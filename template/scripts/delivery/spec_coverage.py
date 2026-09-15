"""Every living-spec statement has a test.

Anchors are `<file>.md#<heading-slug>` for every `##` heading under working/spec/.
A test claims one with `@pytest.mark.spec("core.md#refund-window")`. A spec file
containing `status: unspecified` is reported and skipped (adoption).
Output: `working/spec/<file>:<line>: SPEC-UNCOVERED <anchor>`. Exit 0/1/2.
"""

from __future__ import annotations

import re
from pathlib import Path

from delivery import paths
from delivery.block import fail

_HEADING_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$")
_MARK_RE = re.compile(r"@pytest\.mark\.spec\(\s*[\"'](?P<anchor>[^\"']+)[\"']\s*\)")


def slug(title: str) -> str:
    """GitHub-style heading slug."""
    s = re.sub(r"[^\w\s-]", "", title.lower()).strip()
    return re.sub(r"[\s_]+", "-", s)


def anchors(repo: Path) -> tuple[list[tuple[str, int, str]], list[str]]:
    """(file, line, anchor) for every heading, plus the list of unspecified files."""
    out: list[tuple[str, int, str]] = []
    unspecified: list[str] = []
    for f in sorted((repo / paths.SPEC_DIR).glob("**/*.md")):
        text = f.read_text()
        relname = f.relative_to(repo / paths.SPEC_DIR).as_posix()
        if re.search(r"^status:\s*unspecified\s*$", text, re.M):
            unspecified.append(relname)
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if m := _HEADING_RE.match(line):
                out.append((paths.rel(repo, f), i, f"{relname}#{slug(m.group('title'))}"))
    return out, unspecified


def claimed(repo: Path) -> set[str]:
    """Anchors claimed by spec markers anywhere in the test trees."""
    found: set[str] = set()
    for f in paths.test_files(repo):
        found.update(_MARK_RE.findall(f.read_text()))
    return found


def main(argv: list[str]) -> int:
    """Entry point; see module docstring."""
    if len(argv) > 1:
        return fail(
            "usage",
            "at most one repo path",
            "see docstring",
            ["uv run python -m delivery.spec_coverage [repo]"],
            "working/README.md#checks",
            env=True,
        )
    repo = Path(argv[0]) if argv else Path.cwd()
    heads, unspecified = anchors(repo)
    for u in unspecified:
        print(
            f"working/spec/{u}:1: SPEC-UNSPECIFIED this member is unspecified: "
            "no living spec yet (allowed during adoption)"
        )
    have = claimed(repo)
    missing = [(f, ln, a) for f, ln, a in heads if a not in have]
    for f, ln, a in missing:
        print(
            f"{f}:{ln}: SPEC-UNCOVERED {a} has no test; "
            f'add @pytest.mark.spec("{a}") to the test that proves it'
        )
    if missing:
        return fail(
            "spec-coverage",
            f"{len(missing)} spec statement(s) without a test",
            "a living-spec statement is true only if a test shows it",
            ["add the marker to an existing test, or write the test (red first)"],
            "working/README.md#living-spec",
        )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
