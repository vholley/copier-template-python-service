"""`make status`: where am I and what is next (19.3)."""

from __future__ import annotations

from pathlib import Path

from delivery import block, gitx, registry, state

KIND = {
    "change": "change (add or change behavior)",
    "change-defect": "bug fix",
    "project": "new project",
    "spike": "exploration (spike)",
}
STAGE_COMMANDS: dict[str, list[str]] = {
    "intent": ["/intent", "make accept STAGE=intent"],
    "clarify": ["/clarify"],
    "spec": ["/spec", "make accept STAGE=spec"],
    "diagnose": ["/diagnose", "make accept STAGE=diagnosis"],
    "plan": ["/plan"],
    "red": ["/red", "make accept STAGE=red"],
    "implement": ["/implement", "make green"],
    "verify": ["/implement (evaluator)"],
    "review": ["open the PR", "make contract"],
    "escalated": ["/implement (after fixing the criterion)", "/amend --to spec", "make abandon"],
    "bounced": ["/intent"],
}


def _unbound(repo: Path, branch: str, lines: list[str]) -> str:
    corrupt = repo / state.WORK_DIR / branch / "state.json"
    if corrupt.exists():
        lines += [
            "Kind of work  unknown (state.json unreadable)",
            "Stage         unknown",
            f"Blocking      .work/{branch}/state.json cannot be read. "
            f"NEXT: make rebuild ID={branch}",
            f"Next          make rebuild ID={branch}",
            "",
            "commands available now",
            f"  make rebuild ID={branch}",
            "  make help",
        ]
    else:
        lines += [
            "Kind of work  no work item on this branch",
            "Stage         (none)",
            "Blocking      nothing",
            "Next          make start",
            "",
            "commands available now",
            "  make start",
            "  make help",
        ]
    return "\n".join(lines) + "\n"


def _acceptance_lines(repo: Path, item: str) -> list[str]:
    acc = state.acceptances(repo, item)
    if not acc:
        return ["Accepted      nothing yet"]
    out = ["Accepted"]
    for stage, (sha, _h) in acc.items():
        who = gitx.run(repo, "log", "-1", "--format=%an, %as", sha, check=False).strip()
        out.append(f"  {stage:10} {who}   {sha[:8]}")
    return out


def report(repo: Path) -> str:
    """The status text."""
    branch = gitx.current_branch(repo)
    lines: list[str] = [f"Branch        {branch}"]
    try:
        item = state.bound_item(repo, branch)
    except state.ConsistencyError as exc:
        lines.append(f"Blocking      {exc}")
        item = None
    if item is None:
        return _unbound(repo, branch, lines)
    blocking: list[str] = []
    st: state.State | None
    try:
        st = state.read(repo, item)
    except (state.IntegrityError, state.ConsistencyError) as exc:
        blocking.append(str(exc))
        try:
            st = state.load_unchecked(repo, item)
        except state.IntegrityError:
            st = None
    kind = KIND.get(st.workflow, st.workflow) if st else "unknown (state.json unreadable)"
    lines.append(f"Kind of work  {kind}")
    lines.append(f"Stage         {st.stage if st else 'unknown'}")
    if st:
        lines.extend(_acceptance_lines(repo, item))
        blocking.extend(state.check(repo, item))
    lines.append("Blocking      " + (blocking[0] if blocking else "nothing"))
    lines.extend("              " + extra for extra in blocking[1:])
    stage = st.stage if st else "intent"
    cmds = STAGE_COMMANDS.get(stage, [])
    lines.append(f"Next          {cmds[0] if cmds else 'make status'}")
    lines += ["", "commands available now", *(f"  {c}" for c in cmds)]
    if st and st.stage not in state.TERMINAL:
        lines.append("  make abandon")
    lines += ["  /amend", "  make help"]
    _ = registry  # `make help` reads the registry; status lists only what is legal now
    return "\n".join(lines) + "\n"


@block.guard_unborn
def main(argv: list[str]) -> int:
    """Entry point."""
    repo = Path(argv[0]) if argv else Path.cwd()
    print(report(repo), end="")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
