"""A small, deterministic check for AI-writing tells in human-facing text.

The full pass is the vendored deslop skill; this catches the handful of patterns that
can be matched mechanically. Usage: writing_check.py FILE... Exit 0/1.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("em-dash", re.compile(r"—")),
    ("negative parallelism", re.compile(r"\b(?:it'?s|this is|that is) not (?:just |only )?[^.]{1,60}[,;] (?:it'?s|it is|but)\b", re.I)),
    ("self-answered question", re.compile(r"\?\s+(?:Because|The answer|Yes|No)\b")),
    ("pompous copula", re.compile(r"\b(?:serves as|stands as|represents a)\b", re.I)),
    ("throat-clearing", re.compile(r"\b(?:Here'?s the thing|It'?s worth noting|At its core|When you think about it)\b", re.I)),
    ("marker vocabulary", re.compile(r"\b(?:delve|leverage|robust|seamless|tapestry|landscape|paradigm|unlock|empower|elevate|multifaceted|utilize)\b", re.I)),
]


def check(text: str) -> list[tuple[int, str]]:
    """(line, tell) for every hit; fenced code blocks are skipped."""
    hits: list[tuple[int, str]] = []
    in_code = False
    for i, line in enumerate(text.splitlines(), start=1):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        hits.extend((i, name) for name, pat in PATTERNS if pat.search(line))
    return hits


def main(argv: list[str]) -> int:
    """Entry point."""
    code = 0
    for arg in argv:
        path = Path(arg)
        if not path.exists():
            print(f"{arg}: missing")
            code = 1
            continue
        for line, tell in check(path.read_text()):
            print(f"{arg}:{line}: WRITING {tell}")
            code = 1
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
