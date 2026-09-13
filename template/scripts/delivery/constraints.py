"""Invariant checks that Ruff and import-linter cannot express.

Each rule has an ID, an anchor into working/architecture/constraints.md, and a
remediation message written to the model-facing standard. Output is one
`path:line: RULE-ID message` per violation. Grandfathered violations are listed
in working/architecture/constraints-baseline.txt (`path:RULE-ID`) and the file
may only shrink: a listed violation that no longer exists is itself reported.

Run: uv run python -m delivery.constraints [--write-baseline] [repo]
Exit: 0 clean, 1 violations, 2 usage.
"""

from __future__ import annotations

import ast
from pathlib import Path

from delivery import paths
from delivery.block import fail

ANCHOR = "working/architecture/constraints.md#"


class Rule(ast.NodeVisitor):
    """Base class: subclasses set id, anchor, message and override visit_* methods."""

    id = ""
    anchor = ""
    message = ""

    def __init__(self, path: str) -> None:
        """Bind the rule to the repo-relative path being scanned."""
        self.path = path
        self.hits: list[tuple[str, int]] = []

    def report(self, node: ast.AST) -> None:
        """Record a violation at the node's line."""
        self.hits.append((self.path, getattr(node, "lineno", 1)))


class NoPrintInLibraryCode(Rule):
    """INV-01: library code logs through logging_setup; print() is for CLIs only."""

    id = "INV-01"
    anchor = ANCHOR + "inv-01"
    message = (
        "print() in library code; use the logger from core.logging_setup. "
        "Example: libs/shared/src/shared/logging_setup.py:1"
    )

    def visit_Call(self, node: ast.Call) -> None:
        """Flag calls to the print builtin."""
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            self.report(node)
        self.generic_visit(node)


RULES: dict[str, type[Rule]] = {NoPrintInLibraryCode.id: NoPrintInLibraryCode}


def scan(repo: Path) -> list[tuple[str, int, str, str]]:
    """(path, line, rule id, message) for every violation in source files."""
    hits: list[tuple[str, int, str, str]] = []
    for f in paths.source_files(repo):
        if f.name == "main.py":  # CLI entry points may print (Ruff per-file-ignores mirror this)
            continue
        tree = ast.parse(f.read_text(), filename=str(f))
        for rule_cls in RULES.values():
            rule = rule_cls(paths.rel(repo, f))
            rule.visit(tree)
            hits.extend((p, ln, rule.id, rule.message) for p, ln in rule.hits)
    return hits


def main(argv: list[str]) -> int:
    """Entry point; see module docstring."""
    write = "--write-baseline" in argv
    rest = [a for a in argv if not a.startswith("--")]
    if len(rest) > 1:
        return fail(
            "usage",
            "constraints takes at most one repo path",
            "see --help",
            ["uv run python -m delivery.constraints [--write-baseline] [repo]"],
            "working/README.md#checks",
            env=True,
        )
    repo = Path(rest[0]) if rest else Path.cwd()
    hits = scan(repo)
    if write:
        entries = sorted({f"{p}:{rid}" for p, _ln, rid, _m in hits})
        target = repo / paths.BASELINE_FILE
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "# Grandfathered violations; this file may only shrink.\n"
            + "".join(e + "\n" for e in entries)
        )
        return 0
    baseline = paths.read_baseline(repo)
    seen: set[str] = set()
    violations = 0
    for p, ln, rid, msg in hits:
        key = f"{p}:{rid}"
        seen.add(key)
        if key in baseline:
            continue
        print(f"{p}:{ln}: {rid} {msg}")
        violations += 1
    for stale in sorted(baseline - seen):
        print(
            f"{stale.split(':')[0]}:1: BASELINE-STALE {stale} no longer occurs; "
            "remove it from constraints-baseline.txt"
        )
        violations += 1
    if violations:
        return fail(
            "constraints",
            f"{violations} violation(s) listed above",
            "every constraint in constraints.md is enforced mechanically",
            ["fix each line as its message says, then: make green"],
            "working/README.md#constraints",
        )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
