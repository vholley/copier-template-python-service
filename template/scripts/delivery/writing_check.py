"""Deterministic writing check for human-facing documents.

Flags the lexical and structural tells the deslop skill's reference lists as
detectable by pattern (working/standards/human-facing.md). The deslop skill
rewrites; this only refuses. Output: `path:line: WRITING-nn message`. Exit 0/1.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from delivery.block import fail

_VOCAB = (
    # "harness" is the domain term for an agent harness, not a tell. The tell is
    # the verb ("harness the power of"), and excluding the noun would fire on
    # correct usage in every project built from this template.
    "delve|tapestry|paradigm|synergy|leverage|robust|seamless|holistic|elevate|empower|"
    "unlock|game-changer|cutting-edge"
)
_BRIDGES = (
    "it's worth noting|it is worth noting|here's the thing|the key insight|at its core|"
    "when you really think about it"
)
TELLS: list[tuple[str, re.Pattern[str], str]] = [
    ("WRITING-01", re.compile(r"—"), "em-dash; use a comma, colon, or a new sentence"),
    (
        "WRITING-02",
        re.compile(
            r"\b(isn't|is not|not) (just|merely|only) [^.]{1,80}?\b(it's|it is|but)\b", re.I
        ),
        "negative parallelism (not just X, it's Y); state the claim",
    ),
    ("WRITING-03", re.compile(rf"\b({_VOCAB})\b", re.I), "AI-tell vocabulary; use the plain word"),
    (
        "WRITING-04",
        re.compile(r"\b(serves as|stands as|represents a|marks a)\b", re.I),
        "pompous copula; use 'is'",
    ),
    (
        "WRITING-05",
        re.compile(r"^\s*[^#\n]{0,60}\?\s*$"),
        "a question the text answers itself; state the answer",
    ),
    ("WRITING-06", re.compile(rf"\b({_BRIDGES})\b", re.I), "filler bridge; delete it"),
    (
        "WRITING-07",
        re.compile(r"\b(deeply|genuinely|truly|fundamentally|remarkably|incredibly)\b", re.I),
        "filler intensifier",
    ),
]
SKIP_LINE = re.compile(r"^\s*(```|<!--|\||-{3,})")


def check_file(path: Path) -> list[str]:
    """WRITING-nn lines for one file. Code blocks, tables, and comments are skipped."""
    out: list[str] = []
    in_code = False
    for i, line in enumerate(path.read_text().splitlines(), start=1):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or SKIP_LINE.match(line):
            continue
        out.extend(
            f"{path.as_posix()}:{i}: {rule_id} {msg}"
            for rule_id, pattern, msg in TELLS
            if pattern.search(line)
        )
    return out


def main(argv: list[str]) -> int:
    """Entry point: one or more files."""
    files = [Path(a) for a in argv if not a.startswith("--")]
    if not files:
        return fail(
            "usage",
            "at least one file is required",
            "see docstring",
            ["uv run python -m delivery.writing_check README.md"],
            "working/README.md#skills",
            env=True,
        )
    lines: list[str] = []
    for f in files:
        if f.exists():
            lines.extend(check_file(f))
    for ln in lines:
        print(ln)
    if lines:
        return fail(
            "writing",
            f"{len(lines)} writing tell(s) listed above",
            "human-facing text is written for a reader without context "
            "(working/standards/human-facing.md)",
            ["rewrite the lines, or run the deslop skill on the file"],
            "working/README.md#skills",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
