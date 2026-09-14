"""Vendored skills match .claude/VENDORED.md (12.5)."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from delivery.block import fail

VENDORED = Path(".claude/VENDORED.md")


def digest(directory: Path) -> str:
    """Stable SHA-256 over every file's relative path and bytes."""
    h = hashlib.sha256()
    for f in sorted(p for p in directory.rglob("*") if p.is_file()):
        h.update(f.relative_to(directory).as_posix().encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def main(argv: list[str]) -> int:
    """Entry point: [repo] | --digest <skill-dir>.

    --digest prints the value to paste into .claude/VENDORED.md after re-vendoring.
    """
    if argv and argv[0] == "--digest":
        if len(argv) < 2:
            return fail(
                "vendored",
                "--digest needs a skill directory",
                "the digest covers one vendored skill",
                ["python -m delivery.vendored_check --digest .claude/skills/<name>"],
                "working/README.md#skills",
            )
        print(digest(Path(argv[1])))
        return 0
    repo = Path(argv[0]) if argv else Path.cwd()
    path = repo / VENDORED
    if not path.exists():
        return fail(
            "vendored",
            ".claude/VENDORED.md is missing",
            "every vendored skill records its provenance",
            ["restore .claude/VENDORED.md from the template"],
            "working/README.md#skills",
        )
    problems: list[str] = []
    for m in re.finditer(
        r"^\|\s*(?P<name>[\w-]+)\s*\|\s*[^|]*\|\s*[^|]*\|\s*(?P<digest>[0-9a-f]{64})\s*\|",
        path.read_text(),
        re.M,
    ):
        skill = repo / ".claude" / "skills" / m.group("name")
        if not skill.exists():
            problems.append(f"vendored skill {m.group('name')} is missing")
        elif digest(skill) != m.group("digest"):
            problems.append(
                f"vendored skill {m.group('name')} differs from VENDORED.md; "
                "re-vendor upstream, do not edit locally"
            )
    for p in problems:
        print(p)
    if problems:
        return fail(
            "vendored",
            f"{len(problems)} vendored skill problem(s)",
            "vendored skills are copied, never edited locally",
            ["re-vendor from the source in VENDORED.md and update the digest"],
            "working/README.md#skills",
        )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
