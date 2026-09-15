"""Project-layout readers shared by the checks.

Reads working/standards/budgets.md (key: value lines plus path lists),
working/architecture/constraints.md (constraint lines), and the workspace
member layout (libs/*, apps/*). Nothing here prints or decides; it only reads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

BUDGETS_FILE = Path("working/standards/budgets.md")
CONSTRAINTS_FILE = Path("working/architecture/constraints.md")
BASELINE_FILE = Path("working/architecture/constraints-baseline.txt")
TEMPLATES_FILE = Path("working/standards/criteria-templates.md")
SPEC_DIR = Path("working/spec")

_KV_RE = re.compile(r"^(?P<key>[a-z_][\w.]*):\s*(?P<value>[-+]?\d+(?:\.\d+)?)\s*(?:#.*)?$")
_LIST_HEAD_RE = re.compile(r"^(?P<key>[a-z_]\w*):\s*$")
_LIST_ITEM_RE = re.compile(r'^\s+-\s*"?(?P<item>[^"]+?)"?\s*$')
_CONSTRAINT_RE = re.compile(
    r"^-\s+(?P<id>[A-Z][A-Z0-9]*-\d+)\s+\(check:\s+(?P<tool>ruff|importlinter|constraints\.py)"
    r"\s+(?P<check>[A-Za-z0-9_.-]+)\)(?P<params>(?:\s*\[[a-z_]+:[^\]]*\])*)\s*:\s*(?P<text>.+)$"
)
_PARAM_RE = re.compile(r"\[(?P<key>[a-z_]+):\s*(?P<values>[^\]]*)\]")


@dataclass(frozen=True)
class Budgets:
    """Numeric budgets and path lists from budgets.md."""

    numbers: dict[str, float]
    lists: dict[str, list[str]]

    def get(self, key: str) -> float | None:
        """Numeric budget by key, or None when not set."""
        return self.numbers.get(key)


def read_budgets(repo: Path) -> Budgets:
    """Parse budgets.md. Unknown lines are ignored; a list continues until a non-item line."""
    numbers: dict[str, float] = {}
    lists: dict[str, list[str]] = {}
    current: str | None = None
    path = repo / BUDGETS_FILE
    if not path.exists():
        return Budgets(numbers, lists)
    for raw in path.read_text().splitlines():
        line = raw.rstrip()
        if current is not None and (m := _LIST_ITEM_RE.match(line)):
            lists[current].append(m.group("item"))
            continue
        current = None
        if m := _KV_RE.match(line):
            numbers[m.group("key")] = float(m.group("value"))
        elif m := _LIST_HEAD_RE.match(line):
            key = m.group("key")
            current = key
            lists[key] = []
    return Budgets(numbers, lists)


@dataclass(frozen=True)
class Constraint:
    """One line of constraints.md."""

    id: str
    tool: str
    check: str
    text: str
    params: dict[str, tuple[str, ...]]


def read_constraints(repo: Path) -> list[Constraint]:
    """Every `- ID (check: tool id): text` line in constraints.md."""
    path = repo / CONSTRAINTS_FILE
    if not path.exists():
        return []
    out: list[Constraint] = []
    commented = False
    for line in path.read_text(encoding="utf-8").splitlines():
        # The template ships INV-01 as a commented example ("enable by
        # uncommenting"), so a rule inside <!-- --> must not run.
        if "<!--" in line:
            commented = True
        if commented:
            if "-->" in line:
                commented = False
            continue
        m = _CONSTRAINT_RE.match(line.strip())
        if m is None:
            continue
        params = {
            pm.group("key"): tuple(v.strip() for v in pm.group("values").split(",") if v.strip())
            for pm in _PARAM_RE.finditer(m.group("params") or "")
        }
        out.append(
            Constraint(m.group("id"), m.group("tool"), m.group("check"), m.group("text"), params)
        )
    return out


def constraint_params(repo: Path, constraint_id: str) -> dict[str, tuple[str, ...]]:
    """Parameters declared on a constraint's line, or an empty dict."""
    for c in read_constraints(repo):
        if c.id == constraint_id:
            return c.params
    return {}


def read_baseline(repo: Path) -> set[str]:
    """Grandfathered `path:RULE-ID` entries."""
    path = repo / BASELINE_FILE
    if not path.exists():
        return set()
    return {
        ln.strip() for ln in path.read_text().splitlines() if ln.strip() and not ln.startswith("#")
    }


def source_files(repo: Path) -> list[Path]:
    """Python files under libs/*/src and apps/*/src, sorted."""
    files: list[Path] = []
    for member in ("libs", "apps"):
        files.extend((repo / member).glob("*/src/**/*.py"))
    return sorted(files)


def test_files(repo: Path) -> list[Path]:
    """Python files under libs/*/tests and apps/*/tests, sorted."""
    files: list[Path] = []
    for member in ("libs", "apps"):
        files.extend((repo / member).glob("*/tests/**/*.py"))
    return sorted(files)


def rel(repo: Path, path: Path) -> str:
    """Repo-relative POSIX path for output lines."""
    return path.relative_to(repo).as_posix()


def ruff_selected(repo: Path) -> set[str]:
    """Rule codes and prefixes listed in [tool.ruff.lint] select of pyproject.toml."""
    py = repo / "pyproject.toml"
    if not py.exists():
        return set()
    m = re.search(
        r"\[tool\.ruff\.lint\][^\[]*?select\s*=\s*\[(?P<body>[^\]]*)\]", py.read_text(), re.S
    )
    if not m:
        return set()
    return set(re.findall(r'"([A-Z][A-Z0-9]*)"', m.group("body")))


def importlinter_contracts(repo: Path) -> set[str]:
    """Contract IDs: the token before the first ':' in each import-linter contract name."""
    py = repo / "pyproject.toml"
    if not py.exists():
        return set()
    names = re.findall(
        r'\[\[tool\.importlinter\.contracts\]\]\s*\n\s*name\s*=\s*"([^"]+)"', py.read_text()
    )
    return {n.split(":", 1)[0].strip() for n in names}
