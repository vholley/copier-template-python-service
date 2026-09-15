"""Small CLI over delivery.state for the Makefile: `bound`, `rebuild <id>`, `exits <state>`."""

from __future__ import annotations

import sys
from pathlib import Path

from delivery import block, gitx, state

USAGE = "usage: state_cli bound | rebuild <id> | exits <state>"


def _bound(repo: Path) -> int:
    try:
        item = state.bound_item(repo, gitx.current_branch(repo))
    except state.ConsistencyError:
        return 1
    if item is None:
        return 1
    print(item)
    return 0


@block.guard_unborn
def main(argv: list[str]) -> int:
    """Entry point."""
    repo = Path.cwd()
    cmd = argv[0] if argv else ""
    arg = argv[1] if len(argv) > 1 else ""
    if cmd == "bound":
        return _bound(repo)
    if cmd == "rebuild" and arg:
        st = state.rebuild(repo, arg)
        print(f"rebuilt {arg}: stage {st.stage}")
        return 0
    if cmd == "exits" and arg:
        print("\n".join(state.exits(arg)))
        return 0
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
