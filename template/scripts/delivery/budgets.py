"""Budget checks.

Numeric limits from working/standards/budgets.md, plus two structural checks on
the definitions themselves.

  (default)      file, area-doc, and spec-domain line budgets
  --agents-md    AGENTS.md line budget and no duplication of a selected Ruff rule
  --constraints  every constraint names a check that exists (no orphans)

Output: `path:line: BUDGET key actual > limit`, `AGENTS.md:line: DUPLICATES-RUFF CODE`,
`constraints.md:1: ORPHAN-CONSTRAINT ID`. Exit 0 clean, 1 violations, 2 usage.
"""

from __future__ import annotations

import re
from pathlib import Path

from delivery import paths
from delivery.block import fail

# Prose in AGENTS.md that restates a Ruff rule. (pattern, ruff code) — extend as rules are selected.
RUFF_SUBJECTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bprint\b.*\b(statement|call)s?\b", re.I), "T20"),
    (re.compile(r"\b(sort|order)\w*\s+imports\b", re.I), "I"),
    (re.compile(r"\bline\s+length\b|\blines?\s+(over|longer than)\s+\d+", re.I), "E501"),
    (re.compile(r"\bdocstrings?\s+(on|for)\s+(every|all)\b", re.I), "D"),
]


def _count_lines(path: Path) -> int:
    return len(path.read_text().splitlines())


def _check_numeric(repo: Path, b: paths.Budgets) -> list[str]:
    out: list[str] = []
    checks: list[tuple[str, list[Path]]] = [
        ("file.max_lines", paths.source_files(repo)),
        ("spec_domain.max_lines", sorted((repo / paths.SPEC_DIR).glob("**/*.md"))),
        ("area_doc.max_lines", sorted((repo / "working" / "architecture").glob("*.md"))),
    ]
    for key, files in checks:
        limit = b.get(key)
        if limit is None:
            continue
        for f in files:
            n = _count_lines(f)
            if n > limit:
                out.append(f"{paths.rel(repo, f)}:1: BUDGET {key} {n} > {int(limit)}")
    return out


def _check_agents_md(repo: Path, b: paths.Budgets) -> list[str]:
    out: list[str] = []
    agents = repo / "AGENTS.md"
    if not agents.exists():
        return ["AGENTS.md:1: MISSING AGENTS.md is required"]
    limit = b.get("agents_md.max_lines")
    n = _count_lines(agents)
    if limit is not None and n > limit:
        out.append(f"AGENTS.md:1: BUDGET agents_md.max_lines {n} > {int(limit)}")
    selected = paths.ruff_selected(repo)
    for i, line in enumerate(agents.read_text().splitlines(), start=1):
        for pattern, code in RUFF_SUBJECTS:
            if pattern.search(line) and (code in selected or code[0] in selected):
                out.append(
                    f"AGENTS.md:{i}: DUPLICATES-RUFF {code} "
                    "this rule is enforced by ruff; delete the line"
                )
    return out


def _check_constraints(repo: Path) -> list[str]:
    from delivery import constraints as cmod  # local import: avoids a cycle at module load

    out: list[str] = []
    ruff = paths.ruff_selected(repo)
    contracts = paths.importlinter_contracts(repo)
    for c in paths.read_constraints(repo):
        ok = (
            (c.tool == "ruff" and (c.check in ruff or c.check[0] in ruff))
            or (c.tool == "importlinter" and c.check in contracts)
            or (c.tool == "constraints.py" and c.check in cmod.RULES)
        )
        if not ok:
            out.append(
                f"{paths.CONSTRAINTS_FILE.as_posix()}:1: ORPHAN-CONSTRAINT {c.id} names {c.tool} "
                f"{c.check}, which does not exist; add the check or remove the constraint"
            )
    return out


def main(argv: list[str]) -> int:
    """Entry point; see module docstring."""
    flags = {a for a in argv if a.startswith("--")}
    rest = [a for a in argv if not a.startswith("--")]
    if len(rest) > 1 or flags - {"--agents-md", "--constraints"}:
        return fail(
            "usage",
            "unrecognized arguments",
            "see the module docstring",
            ["uv run python -m delivery.budgets [--agents-md|--constraints] [repo]"],
            "working/README.md#checks",
            env=True,
        )
    repo = Path(rest[0]) if rest else Path.cwd()
    b = paths.read_budgets(repo)
    if "--agents-md" in flags:
        lines = _check_agents_md(repo, b)
    elif "--constraints" in flags:
        lines = _check_constraints(repo)
    else:
        lines = _check_numeric(repo, b)
    for ln in lines:
        print(ln)
    if lines:
        return fail(
            "budgets",
            f"{len(lines)} budget violation(s) listed above",
            "budgets in working/standards/budgets.md are limits, not targets",
            ["shorten or split the file; a limit you disagree with is a decision: /amend"],
            "working/README.md#budgets",
        )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
