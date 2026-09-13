"""Validate a work item's criteria.json against the criteria templates.

Required classes per change type come from the table in
working/standards/criteria-templates.md (D20). Also refuses a criterion marked
pass without evidence, or with an empty verify command.
Run: uv run python -m delivery.spec_check --item <id> [repo]. Exit 0/1/2.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from delivery import paths
from delivery.block import fail

_ROW_RE = re.compile(r"^\|\s*(?P<type>[\w-]+)\s*\|\s*(?P<classes>[^|]*)\|\s*$")


def required_classes(repo: Path) -> dict[str, set[str]]:
    """Change type -> required classes, parsed from the templates table."""
    path = repo / paths.TEMPLATES_FILE
    if not path.exists():
        raise FileNotFoundError(path)
    table: dict[str, set[str]] = {}
    for line in path.read_text().splitlines():
        m = _ROW_RE.match(line.strip())
        if not m or m.group("type") in ("change type", "---"):
            continue
        if set(m.group("type")) <= {"-", " "}:
            continue
        classes = {c.strip() for c in m.group("classes").split(",") if c.strip()}
        table[m.group("type")] = classes
    return table


def main(argv: list[str]) -> int:
    """Entry point; see module docstring."""
    if "--item" not in argv:
        return fail(
            "usage",
            "--item <id> is required",
            "see docstring",
            ["uv run python -m delivery.spec_check --item <id> [repo]"],
            "working/README.md#checks",
            env=True,
        )
    item = argv[argv.index("--item") + 1]
    rest = [a for i, a in enumerate(argv) if not a.startswith("--") and argv[i - 1] != "--item"]
    repo = Path(rest[0]) if rest else Path.cwd()
    crit_path = repo / ".work" / item / "criteria.json"
    if not crit_path.exists():
        return fail(
            "spec-check",
            f"{crit_path.relative_to(repo)} not found",
            "the spec stage writes criteria.json",
            ["/spec"],
            "working/README.md#spec",
            env=True,
        )
    try:
        table = required_classes(repo)
    except FileNotFoundError:
        return fail(
            "spec-check",
            "criteria-templates.md not found",
            "required classes are read from the templates, not hard-coded (D20)",
            ["restore working/standards/criteria-templates.md"],
            "working/README.md#spec",
            env=True,
        )
    data = json.loads(crit_path.read_text())
    change_type = str(data.get("change_type", ""))
    if change_type not in table:
        return fail(
            "spec-check",
            f"change type {change_type!r} is not in criteria-templates.md",
            "every change type must have a row in the templates table",
            ["add the row, or set change_type to an existing one"],
            "working/README.md#spec",
            env=True,
        )
    present = {str(c.get("class")) for c in data.get("criteria", [])}
    problems: list[str] = [
        f"missing required class {cls!r} for change type {change_type!r}"
        for cls in sorted(table[change_type] - present)
    ]
    for c in data.get("criteria", []):
        cid = str(c.get("id"))
        if c.get("status") == "pass" and not c.get("evidence"):
            problems.append(f"{cid} is marked pass with no evidence")
        if not str(c.get("verify", "")).strip():
            problems.append(f"{cid} has no verify command")
    if problems:
        return fail(
            "spec-check",
            "; ".join(problems),
            "criteria are computed: each required class present, each pass backed by evidence",
            ["/spec (add the missing criteria)", "/amend (change an accepted one)"],
            "working/README.md#spec",
        )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
