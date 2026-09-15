"""Acceptance commits: the agent prepares, the engineer signs.

prepare(repo, item, stage) validates the artifact for the stage, stages only
the item's files, and writes the commit message to .work/<id>/accept-<stage>.msg.
sign(repo, item, stage) re-checks the staged blobs against the hashes in the
message, then runs `git commit -S -F`. The Bash hook blocks the agent from
running sign; the engineer runs it in their own shell.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from delivery import block, gitx, state
from delivery.block import fail

if TYPE_CHECKING:
    from collections.abc import Callable

STAGE_FILES: dict[str, list[str]] = {
    "intent": ["intent.md"],
    "spec": ["spec.md", "criteria.json"],
    "red": ["tests.json"],
    "diagnosis": ["diagnosis.md"],
    "decisions": ["decisions.md"],
    "opt-out": ["opt-out.md"],
}
NEXT_STAGE = {"intent": "clarify", "spec": "plan", "red": "implement", "diagnosis": "plan"}


class PrepareError(Exception):
    """The artifact is not acceptable as written; the message names what to fix."""


# ---------------------------------------------------------------- validators


def _validate_intent(text: str) -> None:
    m = re.search(r"^## Non-goals\s*$(?P<body>.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m or not re.search(r"^\s*- \S", m.group("body"), re.M):
        raise PrepareError("intent.md: the Non-goals section must list at least one item")
    done = re.search(r"^## Done means\s*$(?P<body>.*?)(?=^## |\Z)", text, re.M | re.S)
    if done and not re.search(r"^\s*- \S", done.group("body"), re.M):
        raise PrepareError("intent.md: the Done means section is present but empty")


def _validate_spec(d: Path) -> None:
    if not (d / "criteria.json").exists():
        raise PrepareError("criteria.json is missing; run /spec")


def _validate_red(d: Path) -> None:
    if not (d / "tests.json").exists():
        raise PrepareError("tests.json is missing; run /red")


def _validate_intent_dir(d: Path) -> None:
    _validate_intent((d / "intent.md").read_text())


VALIDATORS: dict[str, Callable[[Path], None]] = {
    "intent": _validate_intent_dir,
    "spec": _validate_spec,
    "red": _validate_red,
}


# ------------------------------------------------------------------ prepare


def _decision_trailers(d: Path) -> list[str]:
    path = d / "decisions.md"
    if not path.exists():
        return []
    ids = re.findall(r"^## (D\d+)(?: \([^)]*\))?:", path.read_text(), re.M)
    h = state.accept_hash(path)
    return [f"Accept-Decision: {i} sha256={h}" for i in ids]


def _summary(stage: str, d: Path) -> str:
    if stage == "intent":
        text = (d / "intent.md").read_text()
        n = len(
            re.findall(r"^\s*- ", text.split("## Non-goals")[-1].split("## Done means")[0], re.M)
        )
        return f"Accepts intent.md as the definition of what this item will do. Non-goals: {n}."
    if stage == "spec":
        import json

        data = json.loads((d / "criteria.json").read_text())
        classes: dict[str, int] = {}
        for c in data.get("criteria", []):
            classes[str(c.get("class"))] = classes.get(str(c.get("class")), 0) + 1
        return (
            "Accepts spec.md and criteria.json as the definition of done. Criteria: "
            + ", ".join(f"{k} {v}" for k, v in sorted(classes.items()))
            + "."
        )
    if stage == "red":
        return (
            "Accepts the committed failing tests listed in tests.json as the executable criteria."
        )
    if stage == "diagnosis":
        return "Accepts diagnosis.md: reproduction, evidence, and the confirmed cause."
    if stage == "decisions":
        return "Accepts the decisions recorded during implementation."
    return "Acknowledges that this branch does not use the delivery process."


def prepare(repo: Path, item: str | None, stage: str, *, reason: str = "") -> Path:
    """Validate, stage the item's files, and write the message. Returns the message path."""
    if stage not in STAGE_FILES:
        raise PrepareError(f"unknown stage {stage!r}")
    if stage == "opt-out":
        branch = gitx.current_branch(repo)
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", branch)
        d = repo / state.WORK_DIR / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "opt-out.md").write_text(
            f"# Opt-out\nbranch: {branch}\n"
            f"date: {datetime.now(UTC).date().isoformat()}\nreason: {reason}\n"
        )
        subject = f"accept({branch}): opt-out"
        trailers = [f"Opt-Out: sha256={state.accept_hash(d / 'opt-out.md')}"]
    else:
        if item is None:
            raise PrepareError("a work item is required for this stage")
        d = state.item_dir(repo, item)
        validator = VALIDATORS.get(stage)
        if validator:
            validator(d)
        subject = f"accept(work-{item}): {stage}"
        hashes = " ".join(
            f"sha256={state.accept_hash(d / f)}" for f in STAGE_FILES[stage] if (d / f).exists()
        )
        trailers = [f"Accept: {stage} {hashes}"]
        if stage == "spec":
            trailers.extend(_decision_trailers(d))
        trailers.append(f"Work-Item: {item}")
    msg = f"{subject}\n\n{_summary(stage, d)}\n\n" + "\n".join(trailers) + "\n"
    msg_path = d / f"accept-{stage}.msg"
    msg_path.write_text(msg)
    gitx.run(repo, "reset", "-q")
    gitx.run(repo, "add", "--", str(d.relative_to(repo)))
    gitx.run(repo, "reset", "-q", "--", str(msg_path.relative_to(repo)), check=False)
    return msg_path


# --------------------------------------------------------------------- sign


def _staged_hashes_match(repo: Path, d: Path, msg: str) -> bool:
    """The staged files are exactly the item's files and their hashes match the message."""
    subject = msg.splitlines()[0]
    m = re.search(r"\): ([\w-]+)$", subject)
    files = STAGE_FILES.get(m.group(1), []) if m else []
    trailer = re.search(
        r"^(?:Accept|Opt-Out):(?: [\w-]+)? ((?:sha256=[0-9a-f]{64} ?)+)$", msg, re.M
    )
    want = re.findall(r"sha256=([0-9a-f]{64})", trailer.group(1)) if trailer else []
    have = [state.accept_hash(d / f) for f in files if (d / f).exists()]
    if want != have:
        return False
    # git reports forward slashes on every platform, and splitlines keeps paths
    # that contain spaces in one piece.
    staged = gitx.run(repo, "diff", "--cached", "--name-only").splitlines()
    prefix = d.relative_to(repo).as_posix() + "/"
    return bool(staged) and all(s.strip().startswith(prefix) for s in staged if s.strip())


def sign(repo: Path, item: str | None, stage: str) -> int:
    """The engineer's step: verify the prepared message still matches, then commit -S."""
    if stage == "opt-out":
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", gitx.current_branch(repo))
        d = repo / state.WORK_DIR / slug
    else:
        if item is None:
            return fail(
                "accept",
                "a work item is required",
                "stage acceptances belong to an item",
                ["make status"],
                "working/README.md#signing",
            )
        d = state.item_dir(repo, item)
    msg_path = d / f"accept-{stage}.msg"
    if not msg_path.exists():
        return fail(
            "accept",
            f"no prepared message for {stage}",
            "the agent prepares, the engineer signs",
            [f"make accept-prepare STAGE={stage}"],
            "working/README.md#signing",
        )
    msg = msg_path.read_text()
    if not _staged_hashes_match(repo, d, msg):
        return fail(
            "accept",
            f"{stage} artifacts changed since they were prepared, or something else is staged",
            "you sign exactly what was prepared",
            [f"make accept-prepare STAGE={stage}", "make status"],
            "working/README.md#signing",
        )
    gitx.run(repo, "commit", "-q", "-S", "-F", str(msg_path))
    sha = gitx.run(repo, "rev-parse", "HEAD").strip()
    msg_path.unlink()
    if stage != "opt-out" and item is not None:
        state.record_acceptance(repo, item, stage, sha)
        nxt = NEXT_STAGE.get(stage)
        st = state.load_unchecked(repo, item)
        if nxt and nxt in state.exits(st.stage):
            state.advance(repo, item, nxt)
    print(f"signed {sha[:8]} ({stage})")
    return 0


def opted_out(repo: Path, branch: str) -> bool:
    """True when a signed opt-out record exists for the branch."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", branch)
    if not (repo / state.WORK_DIR / slug / "opt-out.md").exists():
        return False
    return any(
        "Opt-Out:" in msg and f"accept({branch}): opt-out" in msg
        for _sha, msg in gitx.commits(repo)
    )


@block.guard_unborn
def main(argv: list[str]) -> int:
    """Entry point: --prepare or --sign, --stage, [--item], [--reason]."""
    stage = argv[argv.index("--stage") + 1] if "--stage" in argv else ""
    item = argv[argv.index("--item") + 1] if "--item" in argv else None
    reason = argv[argv.index("--reason") + 1] if "--reason" in argv else ""
    rest = [
        a
        for i, a in enumerate(argv)
        if not a.startswith("--") and argv[i - 1] not in ("--stage", "--item", "--reason")
    ]
    repo = Path(rest[0]) if rest else Path.cwd()
    if not stage:
        return fail(
            "usage",
            "--stage is required",
            "see docstring",
            ["make accept STAGE=intent"],
            "working/README.md#signing",
            env=True,
        )
    if "--prepare" in argv:
        try:
            path = prepare(repo, item, stage, reason=reason)
        except PrepareError as exc:
            return fail(
                "accept-prepare",
                str(exc),
                "an acceptance must be complete before it is signed",
                ["fix the artifact, then: make accept-prepare STAGE=" + stage],
                "working/README.md#signing",
            )
        print(
            f"prepared {path.relative_to(repo)}; now run in your shell: make accept STAGE={stage}"
        )
        return 0
    return sign(repo, item, stage)


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
