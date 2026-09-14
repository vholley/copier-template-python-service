"""Shared output helpers for the task commands.

Colour is emitted only for a TTY that is not on a dumb terminal, so piped and
CI output stays plain. Windows terminals get colour through colorama-free
ANSI, which modern conhost and Windows Terminal both understand.
"""

from __future__ import annotations

import os
import sys

_GREEN = "\033[0;32m"
_YELLOW = "\033[1;33m"
_RED = "\033[0;31m"
_RESET = "\033[0m"


def _colour() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty() and os.environ.get("TERM") != "dumb"


def _paint(code: str, text: str) -> str:
    return f"{code}{text}{_RESET}" if _colour() else text


def info(message: str) -> None:
    """A step that succeeded or is starting."""
    print(f"{_paint(_GREEN, '==>')} {message}")


def warn(message: str) -> None:
    """Something the user should act on, but which does not stop the task."""
    print(f"{_paint(_YELLOW, '!! ')} {message}")


def error(message: str) -> None:
    """A failure. The caller returns a non-zero exit code."""
    print(f"{_paint(_RED, 'xx')} {message}", file=sys.stderr)
