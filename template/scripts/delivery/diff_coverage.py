"""Lines added or changed by the branch must be executed by tests.

Reads a Coverage.py JSON report (--coverage-json) and the diff against --base.
Budget: coverage.diff.min in working/standards/budgets.md.
Output: `path:line: COVERAGE line not executed by tests`. Exit 0/1/2.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from delivery import gitx, paths
from delivery.block import fail

_SRC_RE = re.compile(r"^(libs|apps)/[^/]+/src/.*\.py$")


def changed_lines(repo: Path, base: str) -> dict[str, set[int]]:
    """Added or modified line numbers at HEAD, per source file."""
    out: dict[str, set[int]] = {}
    files = [
        f
        for f in gitx.run(repo, "diff", "--name-only", base, "HEAD", check=False).split()
        if _SRC_RE.match(f)
    ]
    for rel in files:
        diff = gitx.run(repo, "diff", "-U0", base, "HEAD", "--", rel, check=False)
        lines: set[int] = set()
        for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", diff, re.M):
            start, count = int(m.group(1)), int(m.group(2) or 1)
            lines.update(range(start, start + count))
        # Blank and comment-only lines are not executable; Coverage.py never reports them.
        src = (repo / rel).read_text().splitlines() if (repo / rel).exists() else []
        lines = {
            ln
            for ln in lines
            if ln <= len(src) and src[ln - 1].strip() and not src[ln - 1].lstrip().startswith("#")
        }
        if lines:
            out[rel] = lines
    return out


def executed_lines(report: Path) -> dict[str, set[int]]:
    """Executed line numbers per file from a Coverage.py JSON report (repo-relative keys)."""
    data = json.loads(report.read_text())
    out: dict[str, set[int]] = {}
    for name, entry in data.get("files", {}).items():
        key = name.replace("\\", "/")
        out[key] = set(entry.get("executed_lines", []))
    return out


def compute(
    changed: dict[str, set[int]], executed: dict[str, set[int]]
) -> tuple[float, list[tuple[str, int]]]:
    """(covered fraction, uncovered (path, line) list). Empty diff counts as fully covered."""
    total = 0
    covered = 0
    missing: list[tuple[str, int]] = []
    for rel, lines in changed.items():
        exe: set[int] = next(
            (v for k, v in executed.items() if k == rel or k.endswith("/" + rel)), set[int]()
        )
        for ln in sorted(lines):
            total += 1
            if ln in exe:
                covered += 1
            else:
                missing.append((rel, ln))
    return (1.0 if total == 0 else covered / total), missing


def main(argv: list[str]) -> int:
    """Entry point; see module docstring."""
    if "--base" not in argv or "--coverage-json" not in argv:
        return fail(
            "usage",
            "--base REF and --coverage-json FILE are required",
            "see docstring",
            [
                "uv run python -m delivery.diff_coverage --base develop "
                "--coverage-json coverage.json [repo]"
            ],
            "working/README.md#checks",
            env=True,
        )
    base = argv[argv.index("--base") + 1]
    report = Path(argv[argv.index("--coverage-json") + 1])
    rest = [
        a
        for i, a in enumerate(argv)
        if not a.startswith("--") and argv[i - 1] not in ("--base", "--coverage-json")
    ]
    repo = Path(rest[0]) if rest else Path.cwd()
    if not report.exists():
        return fail(
            "diff-coverage",
            f"{report} not found",
            "the coverage report is produced by the test job",
            ["make test  (writes coverage.json)"],
            "working/README.md#tests",
            env=True,
        )
    budget = paths.read_budgets(repo).get("coverage.diff.min") or 0.0
    ratio, missing = compute(changed_lines(repo, base), executed_lines(report))
    for rel, ln in missing:
        print(f"{rel}:{ln}: COVERAGE line not executed by tests")
    print(f"diff coverage {ratio:.0%} (budget {budget:.0%})")
    if ratio < budget:
        return fail(
            "diff-coverage",
            f"changed lines covered {ratio:.0%} < {budget:.0%}",
            "new or changed code is covered by the tests that justify it",
            ["add tests for the lines listed above (red first)"],
            "working/README.md#tests",
        )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
