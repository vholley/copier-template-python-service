"""The pull-request contract (design 8.1): what must be true for a change to merge.

Run: uv run python -m delivery.pr_contract (--item ID | --no-item) --base REF
       --signers SOURCE --description FILE [--labels a,b] [repo]
Each failed condition prints one `CONTRACT-nn ...` line on stdout; a single block on
stderr summarizes. Exit 0 pass, 1 failed conditions, 2 environment (signer fetch).

  01 behavior change with no work item (bounce)      08 living spec untouched for a changed member
  02 acceptance commit missing or unsigned           09 diff over the tier budget
  03 accepted file edited after acceptance           10 PR description missing a section
  04 red-first ordering (ordering.py)                11 an LLM co-author trailer
  05 decision without ramification or acceptance     12 spike item
  06 clarify assumption without a risk               13 state.json disagrees with rebuild
  07 durable decision without its promotion edit     14 criteria not all confirmed / spec check

One function per condition; check_item runs them in order.
"""

from __future__ import annotations

import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from delivery import compute_tier, gitx, ordering, paths, signers, spec_check, state
from delivery.block import fail

REQUIRED_SECTIONS = (
    "## Intent",
    "## Risk",
    "## What changed, by criterion",
    "## Decisions",
    "## Promotions",
    "## Evidence",
)
LLM_RE = re.compile(
    r"^Co-Authored-By:.*\b(claude|anthropic|gpt|openai|copilot|gemini|llm)\b", re.I | re.M
)
REQUIRED_ACCEPTANCES = {
    "change": ("intent", "spec", "red"),
    "change-defect": ("intent", "diagnosis"),
    "project": ("intent",),
}
PROMOTION_TARGETS = {
    "adr": "working/architecture/decisions/",
    "spec": "working/spec/",
    "area-doc": "working/architecture/",
    "claude-md": "AGENTS.md",
}


@dataclass
class Ctx:
    """Everything a condition needs, computed once."""

    repo: Path
    item: str
    base: str
    labels: set[str]
    description: str
    allowed: Path
    st: state.State
    changed: list[str] = field(default_factory=lambda: [])

    @property
    def item_dir(self) -> Path:
        """The item's record directory."""
        return state.item_dir(self.repo, self.item)


@dataclass
class Args:
    """Parsed command line."""

    item: str | None = None
    no_item: bool = False
    base: str = "develop"
    signers: str = ""
    description: Path | None = None
    labels: set[str] = field(default_factory=lambda: set())
    repo: Path = field(default_factory=Path.cwd)


def parse_args(argv: list[str]) -> Args:
    """Parse the command line; unknown flags are ignored, the last bare argument is the repo."""
    a = Args()
    i = 0
    rest: list[str] = []
    while i < len(argv):
        tok = argv[i]
        nxt = argv[i + 1] if i + 1 < len(argv) else ""
        if tok == "--item":
            a.item, i = nxt, i + 2
        elif tok == "--no-item":
            a.no_item, i = True, i + 1
        elif tok == "--base":
            a.base, i = nxt, i + 2
        elif tok == "--signers":
            a.signers, i = nxt, i + 2
        elif tok == "--description":
            a.description, i = Path(nxt), i + 2
        elif tok == "--labels":
            a.labels, i = {s.strip() for s in nxt.split(",") if s.strip()}, i + 2
        else:
            rest.append(tok)
            i += 1
    if rest:
        a.repo = Path(rest[-1])
    return a


# ----------------------------------------------------------------- parsers


def _entries(text: str) -> list[dict[str, str]]:
    """Parse `## Dn: title` blocks with `key: value` lines into dicts."""
    out: list[dict[str, str]] = []
    cur: dict[str, str] | None = None
    for line in text.splitlines():
        if m := re.match(r"^## (?P<id>[A-Z]+\d+)(?: \((?P<note>[^)]*)\))?:\s*(?P<title>.*)$", line):
            cur = {"id": m.group("id"), "title": m.group("title"), "note": m.group("note") or ""}
            out.append(cur)
        elif cur is not None and (
            m := re.match(r"^(?P<k>[a-z-]+(?: \[human\])?):\s*(?P<v>.*)$", line)
        ):
            cur[m.group("k").replace(" [human]", "")] = m.group("v").strip()
    return out


def _assumptions(text: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    cur: dict[str, str] | None = None
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section, cur = "Assumptions" in line, None
            continue
        if not in_section:
            continue
        if m := re.match(r"^- (?P<id>A\d+):", line):
            cur = {"id": m.group("id")}
            out.append(cur)
        elif cur is not None and (
            m := re.match(r"^\s+(?P<k>[a-z-]+(?: \[human\])?):\s*(?P<v>.*)$", line)
        ):
            cur[m.group("k").replace(" [human]", "")] = m.group("v").strip()
    return out


def _diff_lines(repo: Path, base: str, files: list[str]) -> int:
    if not files:
        return 0
    out = gitx.run(repo, "diff", "--numstat", base, "HEAD", "--", *files, check=False)
    total = 0
    for ln in out.splitlines():
        parts = ln.split("\t")
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            total += int(parts[0]) + int(parts[1])
    return total


# -------------------------------------------------------------- conditions


def c02_acceptances_signed(c: Ctx) -> list[str]:
    """Every required acceptance exists and is signed by a registered key."""
    out: list[str] = []
    acc = state.acceptances(c.repo, c.item)
    for stage in REQUIRED_ACCEPTANCES.get(c.st.workflow, ()):
        if stage not in acc:
            out.append(
                f"CONTRACT-02 no Accept: {stage} commit for {c.item}. "
                f"NEXT: make accept STAGE={stage}"
            )
            continue
        sha, _h = acc[stage]
        if not signers.verify_commit(c.repo, sha, c.allowed):
            out.append(
                f"CONTRACT-02 Accept: {stage} commit {sha[:8]} is not signed by a registered key. "
                f"NEXT: make accept STAGE={stage}"
            )
    return out


def c03_accepted_files_unchanged(c: Ctx) -> list[str]:
    """No accepted artifact was edited after its acceptance."""
    return [
        "CONTRACT-03 " + p.replace("NEXT: make accept", "NEXT: /amend, then make accept")
        for p in state.accepted_file_problems(c.repo, c.item)
    ]


def c04_ordering(c: Ctx) -> list[str]:
    """Red before green for every criterion, unless a labeled exit waives it."""
    if c.labels & {"retroactive-chain", "bounced"}:
        return []
    return [f"CONTRACT-04 {ln}" for ln in ordering.check(c.repo, c.base, c.item)]


def c05_decisions(c: Ctx) -> list[str]:
    """Every decision has a ramification and an acceptance."""
    path = c.item_dir / "decisions.md"
    if not path.exists():
        return []
    out: list[str] = []
    for e in _entries(path.read_text()):
        if "withdrawn" in e.get("note", "").lower():
            continue
        if not e.get("ramification-if-wrong"):
            out.append(f"CONTRACT-05 decision {e['id']} has no ramification-if-wrong")
        if not e.get("accepted-by"):
            out.append(
                f"CONTRACT-05 decision {e['id']} is not accepted. NEXT: make accept STAGE=decisions"
            )
    return out


def c06_assumptions(c: Ctx) -> list[str]:
    """Every clarify assumption states a risk."""
    path = c.item_dir / "clarify.md"
    if not path.exists():
        return []
    return [
        f"CONTRACT-06 assumption {a['id']} has no risk"
        for a in _assumptions(path.read_text())
        if not a.get("risk")
    ]


def c07_promotions(c: Ctx) -> list[str]:
    """Every durable decision has its promotion edit in the diff."""
    path = c.item_dir / "decisions.md"
    if not path.exists():
        return []
    out: list[str] = []
    for e in _entries(path.read_text()):
        if e.get("scope") != "durable" or "withdrawn" in e.get("note", "").lower():
            continue
        target = e.get("promote-to", "")
        where = PROMOTION_TARGETS.get(target, "")
        if not where or not any(f.startswith(where) for f in c.changed):
            out.append(
                f"CONTRACT-07 durable decision {e['id']} promotes to {target or '?'} "
                f"but the diff has no edit under {where or 'a known target'}"
            )
    return out


def c08_living_spec(c: Ctx) -> list[str]:
    """A member whose src changed has its living-spec file in the diff (D27)."""
    members = {m.group(1) for f in c.changed if (m := re.match(r"^(?:libs|apps)/([^/]+)/src/", f))}
    return [
        f"CONTRACT-08 {name} source changed but working/spec/{name}.md was not updated in this PR"
        for name in sorted(members)
        if f"working/spec/{name}.md" not in c.changed
    ]


def c09_diff_budget(c: Ctx) -> list[str]:
    """The diff is within the budget for its tier."""
    tier = compute_tier.classify(c.repo, c.base).tier
    key = {"trivial": "diff.trivial.max_lines", "high": "diff.high.max_lines"}.get(
        tier, "diff.standard.max_lines"
    )
    budget = paths.read_budgets(c.repo).get(key)
    counted = [f for f in c.changed if not f.startswith((".work/", "working/history/"))]
    n = _diff_lines(c.repo, c.base, counted)
    if budget is not None and n > budget:
        return [
            f"CONTRACT-09 diff is {n} lines, over the {tier} budget of {int(budget)}. "
            "NEXT: split the item"
        ]
    return []


def c10_description(c: Ctx) -> list[str]:
    """The PR description has every required section."""
    return [
        f"CONTRACT-10 PR description is missing section {sec!r}"
        for sec in REQUIRED_SECTIONS
        if sec not in c.description
    ]


def c11_no_llm_coauthor(c: Ctx) -> list[str]:
    """No commit names an LLM as co-author (1.7)."""
    return [
        f"CONTRACT-11 commit {sha[:8]} carries an LLM co-author trailer; "
        "every change has one engineer (1.7)"
        for sha, msg in gitx.commits(c.repo, f"{c.base}..HEAD")
        if LLM_RE.search(msg)
    ]


def c13_state_agrees(c: Ctx) -> list[str]:
    """The committed state.json agrees with what git and the artifacts imply."""
    derived = state.derive_stage(c.repo, c.item)
    if c.st.stage not in ("escalated", "bounced") and derived != c.st.stage:
        return [
            f"CONTRACT-13 state.json says {c.st.stage} but the artifacts imply {derived}. "
            f"NEXT: make rebuild ID={c.item}"
        ]
    return []


def c14_criteria_complete(c: Ctx) -> list[str]:
    """Every criterion is confirmed and the spec check passes."""
    out: list[str] = []
    derived = state.derive_stage(c.repo, c.item)
    if derived != "review":
        out.append(f"CONTRACT-14 criteria are not all confirmed (derived stage {derived})")
    if spec_check.main(["--item", c.item, c.repo.as_posix()]) != 0:
        out.append("CONTRACT-14 spec check failed (see above)")
    return out


CONDITIONS: list[Callable[[Ctx], list[str]]] = [
    c02_acceptances_signed,
    c03_accepted_files_unchanged,
    c04_ordering,
    c05_decisions,
    c06_assumptions,
    c07_promotions,
    c08_living_spec,
    c09_diff_budget,
    c10_description,
    c11_no_llm_coauthor,
    c13_state_agrees,
    c14_criteria_complete,
]


def check_item(a: Args, allowed: Path) -> list[str]:
    """All CONTRACT-nn lines for a work-item PR."""
    repo, item = a.repo, str(a.item)
    if not (state.item_dir(repo, item) / "state.json").exists():
        return [
            f"CONTRACT-01 work item {item} has no state.json. "
            "NEXT: make start; make adopt-branch <id>"
        ]
    try:
        st = state.load_unchecked(repo, item)
    except state.IntegrityError as exc:
        return [f"CONTRACT-13 {exc}"]
    if st.workflow == "spike":
        return [
            f"CONTRACT-12 {item} is a spike; nothing merges from a spike. "
            "NEXT: make start (turn it into a change or bug fix)"
        ]
    desc = a.description.read_text() if a.description and a.description.exists() else ""
    c = Ctx(repo, item, a.base, a.labels, desc, allowed, st)
    c.changed = gitx.run(repo, "diff", "--name-only", a.base, "HEAD", check=False).split()
    lines: list[str] = []
    for cond in CONDITIONS:
        lines.extend(cond(c))
    return lines


def check_no_item(a: Args) -> list[str]:
    """Quick-change PRs: trivial tier, a description, no LLM trailer."""
    t = compute_tier.classify(a.repo, a.base)
    if t.tier != "trivial":
        return [
            f"CONTRACT-01 this PR changes behavior ({t.reasons[0]}) but has no work item. "
            "NEXT: make start; make adopt-branch <id>"
        ]
    lines: list[str] = []
    desc = a.description.read_text().strip() if a.description and a.description.exists() else ""
    if not desc:
        lines.append("CONTRACT-10 a quick change needs a one-line description")
    lines.extend(
        f"CONTRACT-11 commit {sha[:8]} carries an LLM co-author trailer"
        for sha, msg in gitx.commits(a.repo, f"{a.base}..HEAD")
        if LLM_RE.search(msg)
    )
    return lines


def main(argv: list[str]) -> int:
    """Entry point; see module docstring."""
    a = parse_args(argv)
    if a.item is None and not a.no_item:
        return fail(
            "usage",
            "--item ID or --no-item is required",
            "see docstring",
            [
                "uv run python -m delivery.pr_contract --item ID --base develop "
                "--signers file:.signers --description pr.md"
            ],
            "working/README.md#contract",
            env=True,
        )
    if a.item is not None:
        try:
            keys = signers.load(a.signers)
        except signers.FetchError as exc:
            return fail(
                "signers",
                str(exc),
                "the contract cannot verify acceptances without the signer list; it fails closed",
                [
                    "retry when the signer source is reachable",
                    "or pass --signers file:<allowed_signers> for a local run",
                ],
                "working/README.md#signing",
                env=True,
            )
        with tempfile.TemporaryDirectory() as tmp:
            allowed = signers.write_allowed_signers(keys, Path(tmp) / "allowed_signers")
            lines = check_item(a, allowed)
    else:
        lines = check_no_item(a)
    for ln in lines:
        print(ln)
    if lines:
        return fail(
            "pr-contract",
            f"{len(lines)} condition(s) failed; see the CONTRACT lines above",
            "nothing merges to develop without the chain the design requires",
            ["fix each condition as its line says", "make contract  (re-run locally)"],
            "working/README.md#contract",
        )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
