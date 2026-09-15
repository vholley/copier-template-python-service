"""Entry point for the Claude Code hooks: all logic is in scripts/delivery/hooks.py.

Claude Code runs hook commands with the project root as the working directory, so
delivery.hooks resolves the repository itself. This file exists to put scripts/ on
sys.path -- the delivery package is not installed -- and to turn any failure into a
block, because a hook that raises tells Claude Code nothing.

It is invoked as `uv run --no-project --quiet python scripts/hooks/hook.py <event>`.
A plain `uv run` resolves the whole workspace first, so one member with a missing or
unparseable pyproject.toml makes every hook exit on a uv error -- and Claude Code
reads that exit as a refusal, which jams the session at exactly the moment the
repository is in a state worth guarding. --no-project skips the resolution: nothing
under scripts/delivery imports outside the standard library, so there is no
environment to build. uv is named rather than python3 because it carries its own
interpreter, and a machine that runs this template need not have a system Python.

Usage: uv run --no-project --quiet python scripts/hooks/hook.py <event>
"""

from __future__ import annotations

import sys
from pathlib import Path

# scripts/ must be on the path before the delivery package can be imported, so the
# imports below live inside the functions that need them.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MAX_REASON = 160


def _one_line(exc: BaseException) -> str:
    """The exception as a single short line, so the block stays four lines."""
    text = " ".join(str(exc).split()) or exc.__class__.__name__
    return text if len(text) <= MAX_REASON else text[: MAX_REASON - 1] + "…"


def main(argv: list[str]) -> int:
    """Dispatch to delivery.hooks, rendering any failure as a block."""
    from delivery import block, hooks

    event = argv[0] if argv else "?"
    try:
        return hooks.main(argv)
    # Deliberately broad: a hook may not raise past this point. Claude Code reads a
    # block at exit 2 and nothing at all from a stack trace.
    except Exception as exc:
        return block.fail(
            "hook",
            f"{event} failed: {_one_line(exc)}",
            "a hook that cannot finish cannot say whether the work is allowed",
            ["make ci"],
            "working/README.md#hooks",
            env=True,
        )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
