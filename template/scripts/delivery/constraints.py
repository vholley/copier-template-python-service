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


class EnvironmentOnlyInConfig(Rule):
    """INV-01: the environment is read only in the allowed modules.

    The allowed modules are the `[allow: a.b, c.d]` parameter on the constraint's
    line in constraints.md (D39). With no parameter, only modules named
    config.py may read it. Flags os.environ[...], os.environ.get(...), and
    os.getenv(...) elsewhere.
    """

    id = "INV-01"
    anchor = ANCHOR + "inv-01"
    message = (
        "environment read outside the allowed modules; read settings from shared.config "
        "or add the module to INV-01's [allow: ...] list in constraints.md. "
        "Example: libs/shared/src/shared/config.py:1"
    )

    def _is_environ(self, node: ast.expr) -> bool:
        return (
            isinstance(node, ast.Attribute)
            and node.attr == "environ"
            and isinstance(node.value, ast.Name)
            and node.value.id == "os"
        )

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Flag os.environ[...]."""
        if self._is_environ(node.value):
            self.report(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Flag os.getenv(...) and os.environ.get(...)."""
        f = node.func
        if isinstance(f, ast.Attribute) and (
            (f.attr == "getenv" and isinstance(f.value, ast.Name) and f.value.id == "os")
            or (f.attr == "get" and self._is_environ(f.value))
        ):
            self.report(node)
        self.generic_visit(node)


RULES: dict[str, type[Rule]] = {EnvironmentOnlyInConfig.id: EnvironmentOnlyInConfig}


def _module_name(repo: Path, f: Path) -> str:
    """Dotted module name of a source file relative to its member's src directory."""
    parts = f.relative_to(repo).with_suffix("").parts
    if "src" in parts:
        parts = parts[parts.index("src") + 1 :]
    return ".".join(p for p in parts if p != "__init__")


def _exempt(repo: Path, f: Path, rule_id: str) -> bool:
    """INV-01 exemption: modules named config.py, or those in the [allow: ...] parameter."""
    if rule_id != "INV-01":
        return False
    if f.name == "config.py":
        return True
    allowed = paths.constraint_params(repo, rule_id).get("allow", ())
    return _module_name(repo, f) in allowed


def scan(repo: Path) -> list[tuple[str, int, str, str]]:
    """(path, line, rule id, message) for every violation in source files."""
    hits: list[tuple[str, int, str, str]] = []
    for f in paths.source_files(repo):
        tree = ast.parse(f.read_text(), filename=str(f))
        for rule_cls in RULES.values():
            if _exempt(repo, f, rule_cls.id):
                continue
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
