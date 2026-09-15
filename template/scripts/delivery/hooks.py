"""Session hooks: one entry point per Claude Code event.

Usage: python -m delivery.hooks <event>   (event JSON on stdin)
Events: session-start, prompt, edit, post-edit, bash, ask, stop, subagent-stop.
Exit 0 allows. Exit 2 blocks with a four-line message on stderr.
scripts/hooks/hook.py is what Claude Code invokes; run(event, payload, repo)
is the testable core.

Rules the hooks enforce apply only where the design says: stage guards on a
branch bound to a work item (spikes exempt); protected paths everywhere;
acceptance commits never from the agent; questions bounded; the turn cannot end
with unverified work. Every block names the exit, including make opt-out.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from delivery import block, gitx, paths, state, status

GREEN_STAMP = Path(".work") / ".green-stamp"
IMPLEMENT_WORDS = re.compile(
    r"\b(implement|build|write the code|code it|add the (function|endpoint|feature)"
    r"|make it work)\b",
    re.I,
)
BEHAVIOR_WORDS = re.compile(
    r"\b(add|change|implement|remove|support|refactor|migrate|new)\b.*\b(flag|option|endpoint|feature|behavior|command|field|api|model)\b",
    re.I,
)
TYPO_WORDS = re.compile(r"\b(typo|docstring|comment|rename|formatting|readme|wording)\b", re.I)
ACCEPT_RE = re.compile(
    r"Accept(-Decision)?:|accept\(work-|accept\([^)]*\): opt-out|\bmake accept\b(?!-prepare)"
)
STAGES_BEFORE_CODE = {"intent", "clarify", "spec", "plan"}
BUILD_STAGES = {"red", "implement", "verify"}
SRC_RE = re.compile(r"^(libs|apps)/[^/]+/src/")
TEST_RE = re.compile(r"^(libs|apps)/[^/]+/tests/")


def _tool_input(payload: dict[str, object]) -> dict[str, object]:
    raw = payload.get("tool_input")
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items()}  # type: ignore[misc]
    return {}


def _str(d: dict[str, object], key: str) -> str:
    v = d.get(key, "")
    return v if isinstance(v, str) else ""


def _read_payload() -> dict[str, object]:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}


def _bound(repo: Path) -> tuple[str | None, state.State | None]:
    branch = gitx.current_branch(repo)
    try:
        item = state.bound_item(repo, branch)
    except state.ConsistencyError:
        return None, None
    if item is None:
        return None, None
    try:
        return item, state.load_unchecked(repo, item)
    except state.IntegrityError:
        return item, None


def _protected(repo: Path, rel: str) -> bool:
    from delivery.compute_tier import matches_any

    patterns = [
        "working/architecture/**",
        "working/standards/**",
        ".claude/**",
        "scripts/**",
        ".github/**",
    ]
    text = (
        (repo / paths.CONSTRAINTS_FILE).read_text()
        if (repo / paths.CONSTRAINTS_FILE).exists()
        else ""
    )
    m = re.search(r"## Protected paths\s*$(?P<body>.*?)(?=^## |\Z)", text, re.M | re.S)
    if m:
        listed = re.findall(r"^- (\S+)", m.group("body"), re.M)
        patterns = listed or patterns
    return matches_any(rel, patterns)


def _cause_confirmed(d: Path) -> bool:
    diag = d / "diagnosis.md"
    return (
        diag.exists()
        and re.search(r"^\s*status:\s*confirmed\s*$", diag.read_text(), re.M) is not None
    )


def _exit(rule: str, what: str, why: str, next_: list[str], anchor: str) -> tuple[int, str, str]:
    return (
        2,
        "",
        block.render(
            rule,
            what,
            why,
            [*next_, "make opt-out  (leave the process for this branch)"],
            f"working/README.md#{anchor}",
        )
        + "\n",
    )


# --------------------------------------------------------------------- events


def session_start(_payload: dict[str, object], repo: Path) -> tuple[int, str, str]:
    """Orientation: status plus a two-level directory map and the last commits."""
    out = [status.report(repo), "Repository map:"]
    for top in ("libs", "apps"):
        base = repo / top
        if base.exists():
            out.extend(f"  {top}/{p.name}" for p in sorted(base.iterdir()) if p.is_dir())
    out.append("Recent commits:")
    out.append(gitx.run(repo, "log", "--oneline", "-10", check=False).rstrip())
    return 0, "\n".join(out) + "\n", ""


def prompt(payload: dict[str, object], repo: Path) -> tuple[int, str, str]:
    """UserPromptSubmit: stage guard on bound branches; nudge on unbound ones."""
    text = str(payload.get("prompt", ""))
    item, st = _bound(repo)
    if st is None:
        if BEHAVIOR_WORDS.search(text) and not TYPO_WORDS.search(text):
            return (
                0,
                "This looks like a behavior change. Run /start before editing source "
                "so the work item exists.\n",
                "",
            )
        return 0, "", ""
    if st.workflow == "spike" or st.stage not in STAGES_BEFORE_CODE:
        return 0, "", ""
    if IMPLEMENT_WORDS.search(text):
        cmd = status.STAGE_COMMANDS.get(st.stage, ["make status"])[0]
        return _exit(
            "stage",
            f"implementation asked for while {item} is at stage {st.stage}",
            "code is written only after the spec (or diagnosis) is accepted",
            [cmd, "make status"],
            "stages",
        )
    return 0, "", ""


def _rel(path: str, repo: Path) -> str:
    """A tool's file_path as a repo-relative posix path.

    Claude Code sends an absolute path, and on Windows str(repo) uses backslashes
    while the rule patterns are all forward-slashed -- a plain string strip left
    the path absolute, so every guard below silently matched nothing.
    """
    if not path:
        return path
    p = Path(path)
    if not p.is_absolute():
        return p.as_posix()
    try:
        return p.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def edit(payload: dict[str, object], repo: Path) -> tuple[int, str, str]:
    """PreToolUse for Edit/Write: protected paths, state.json, and stage guards."""
    path = _str(_tool_input(payload), "file_path")
    rel = _rel(path, repo)
    if rel.endswith("state.json") and rel.startswith(".work/"):
        return _exit(
            "state",
            f"{rel} is written only by stage_state",
            "state.json is a derived cache with a checksum",
            ["make status", "make rebuild ID=<id>"],
            "state",
        )
    if _protected(repo, rel):
        return _exit(
            "protected",
            f"{rel} is a protected path",
            "process-defining files change only through a reviewed pull request",
            ["describe the change to the engineer; they edit it in their own session"],
            "protected",
        )
    item, st = _bound(repo)
    if st is None or st.workflow == "spike" or not SRC_RE.match(rel):
        return 0, "", ""
    if (
        st.workflow == "change-defect"
        and st.stage == "diagnose"
        and not _cause_confirmed(state.item_dir(repo, str(item)))
    ):
        return _exit(
            "diagnose",
            f"source edit while the cause of {item} is not confirmed",
            "a fix is written only after a discriminating test confirms the cause",
            ["/diagnose  (record the evidence; mark the cause confirmed)", "make status"],
            "diagnosis",
        )
    if st.stage in STAGES_BEFORE_CODE:
        cmd = status.STAGE_COMMANDS.get(st.stage, ["make status"])[0]
        return _exit(
            "stage",
            f"source edit while {item} is at stage {st.stage}",
            "code is written only after the spec is accepted",
            [cmd, "make status"],
            "stages",
        )
    return 0, "", ""


def bash(payload: dict[str, object], repo: Path) -> tuple[int, str, str]:
    """PreToolUse for Bash: the agent never makes an acceptance commit."""
    cmd = _str(_tool_input(payload), "command")
    is_commit = re.search(r"\bgit\s+commit\b", cmd) is not None
    if (is_commit and ACCEPT_RE.search(cmd)) or re.search(r"\bmake\s+accept\b(?!-prepare)", cmd):
        return _exit(
            "accept",
            "an acceptance commit from the agent",
            "acceptances are signed by the engineer in their own shell; "
            "the agent only prepares them",
            [
                "make accept-prepare STAGE=<stage>  "
                "(then tell the engineer: make accept STAGE=<stage>)"
            ],
            "signing",
        )
    if is_commit and re.search(r"-F\s+\S*accept-[\w-]+\.msg", cmd):
        return _exit(
            "accept",
            "committing a prepared acceptance message from the agent",
            "the engineer signs it",
            ["tell the engineer: make accept STAGE=<stage>"],
            "signing",
        )
    _ = repo
    return 0, "", ""


def ask(payload: dict[str, object], repo: Path) -> tuple[int, str, str]:
    """PreToolUse for AskUserQuestion: at most three questions, at most one substantial."""
    raw = _tool_input(payload).get("questions", [])
    questions: list[object] = list(raw) if isinstance(raw, list) else []  # type: ignore[arg-type]
    limit = int(paths.read_budgets(repo).get("review.question_max_lines") or 15)
    n = len(questions)
    substantial = 0
    for q in questions:
        if isinstance(q, dict):
            text = q.get("question", "")  # type: ignore[union-attr]
            if isinstance(text, str) and len(text.splitlines()) > limit:
                substantial += 1
    if n > 3:
        return _exit(
            "ask",
            f"{n} questions in one turn",
            "at most three small questions per turn; the engineer's attention is budgeted",
            ["split the ask across turns"],
            "review",
        )
    if substantial > 1:
        return _exit(
            "ask",
            f"{substantial} substantial questions in one turn",
            "at most one substantial question per turn",
            ["ask the first now, the next after the answer"],
            "review",
        )
    return 0, "", ""


def record_green(repo: Path) -> None:
    """Called by make green on success: stamps the time so the stop gate can compare."""
    stamp = repo / GREEN_STAMP
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(str(time.time()))


def _green_is_fresh(repo: Path) -> bool:
    stamp = repo / GREEN_STAMP
    if not stamp.exists():
        return False
    t = float(stamp.read_text() or "0")
    newest = 0.0
    for f in [*paths.source_files(repo), *paths.test_files(repo)]:
        newest = max(newest, f.stat().st_mtime)
    return t >= newest


def _red_stage_problems(repo: Path, d: Path) -> list[str]:
    tests_path = d / "tests.json"
    if not tests_path.exists():
        return []
    import os
    import subprocess

    out: list[str] = []
    tmap: dict[str, list[dict[str, str]]] = json.loads(tests_path.read_text())
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        str(p) for p in [*repo.glob("libs/*/src"), *repo.glob("apps/*/src")]
    )
    for entries in tmap.values():
        for e in entries:
            t = str(e.get("test"))
            r = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "-o",
                    "addopts=",
                    t,
                ],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if r.returncode == 0:
                out.append(f"{t} already passes; a red test must fail")
    return out


def stop(_payload: dict[str, object], repo: Path) -> tuple[int, str, str]:
    """Stop: the turn ends only with committed, green, evidenced work; three blocks escalate."""
    item, st = _bound(repo)
    if st is None or st.stage not in BUILD_STAGES:
        return 0, "", ""
    d = state.item_dir(repo, str(item))
    problems: list[str] = []
    dirty = [
        ln[3:]
        for ln in gitx.run(
            repo, "status", "--porcelain", "--", "libs", "apps", check=False
        ).splitlines()
    ]
    if dirty:
        problems.append(f"uncommitted source: {', '.join(dirty[:3])}")
    if not _green_is_fresh(repo):
        problems.append("make green has not passed since the last edit")
    crit = d / "criteria.json"
    if crit.exists():
        problems.extend(
            f"{c.get('id')} is marked pass with no evidence"
            for c in json.loads(crit.read_text()).get("criteria", [])
            if c.get("status") == "pass" and not c.get("evidence")
        )
    if st.stage == "red":
        problems.extend(_red_stage_problems(repo, d))
    if not problems:
        return 0, "", ""
    cap = int(paths.read_budgets(repo).get("stop_hook.retry_cap") or 3)
    retries = state.bump_retry(repo, str(item))
    if retries >= cap and "escalated" in state.exits(st.stage):
        # The third block is still a block; it also escalates, so the next turn ends freely.
        state.advance(repo, str(item), "escalated")
        progress = d / "progress.md"
        existing = progress.read_text() if progress.exists() else ""
        progress.write_text(
            existing
            + f"\n## escalated after {retries} blocks\n"
            + "".join(f"- {p}\n" for p in problems)
        )
        return (
            2,
            "",
            block.render(
                "stop",
                f"{item} escalated after {retries} blocks: " + "; ".join(problems),
                "a human decides how to continue",
                ["make status  (lists: implement, spec, abandon)"],
                "working/README.md#escalated",
            )
            + "\n",
        )
    return _exit(
        "stop",
        "; ".join(problems),
        "a turn ends only with committed, green, evidenced work",
        [
            "fix the items above, then: make green",
            f"(block {retries} of {cap}; the item escalates at {cap})",
        ],
        "green",
    )


def subagent_stop(payload: dict[str, object], repo: Path) -> tuple[int, str, str]:
    """SubagentStop: the evaluator must have written its report."""
    if str(payload.get("agent_name", "")) != "evaluator":
        return 0, "", ""
    item, _st = _bound(repo)
    if item and not (state.item_dir(repo, item) / "evaluator-report.md").exists():
        return _exit(
            "evaluator",
            "the evaluator ended without writing evaluator-report.md",
            "the evaluator's only output is its report",
            ["write .work/<id>/evaluator-report.md, then stop"],
            "evaluator",
        )
    return 0, "", ""


def post_edit(payload: dict[str, object], repo: Path) -> tuple[int, str, str]:
    """PostToolUse for Edit/Write: run the checks on the touched file and report (feedback only)."""
    path = _str(_tool_input(payload), "file_path")
    if not path.endswith(".py"):
        return 0, "", ""
    import shutil
    import subprocess

    uv = shutil.which("uv") or "uv"
    r = subprocess.run(
        [uv, "run", "ruff", "check", "--output-format", "concise", path],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        return 2, "", r.stdout + "\nFix the lines above (make green runs the same checks).\n"
    return 0, "", ""


EVENTS = {
    "session-start": session_start,
    "prompt": prompt,
    "edit": edit,
    "post-edit": post_edit,
    "bash": bash,
    "ask": ask,
    "stop": stop,
    "subagent-stop": subagent_stop,
}


def run(event: str, payload: dict[str, object], repo: Path) -> tuple[int, str, str]:
    """(exit code, stdout, stderr) for an event. Unknown events allow."""
    handler = EVENTS.get(event)
    if handler is None:
        return 0, "", ""
    return handler(payload, repo)


def main(argv: list[str]) -> int:
    """Entry point: <event> [repo]."""
    if not argv:
        print(
            block.render(
                "usage",
                "an event name is required",
                "see docstring",
                ["python -m delivery.hooks stop"],
                "working/README.md#hooks",
            ),
            file=sys.stderr,
        )
        return 2
    repo = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    if argv[0] == "record-green":
        record_green(repo)
        return 0
    code, out, err = run(argv[0], _read_payload(), repo)
    if out:
        print(out, end="")
    if err:
        print(err, end="", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
