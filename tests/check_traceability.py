"""Fail if the scenario index and expected_ids.txt disagree, or a listed test node is missing.

Run: uv run python tests/check_traceability.py
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).parent
SCENARIOS = HERE / "scenarios"


def main() -> int:
    """Entry point."""
    expected = {
        line.strip()
        for line in (SCENARIOS / "expected_ids.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }
    index = tomllib.loads((SCENARIOS / "index.toml").read_text())["scenarios"]
    problems: list[str] = []
    problems.extend(f"listed but not in index: {i}" for i in sorted(expected - set(index)))
    problems.extend(f"in index but not listed: {i}" for i in sorted(set(index) - expected))
    collected = subprocess.run(
        ["uv", "run", "pytest", "--collect-only", "-q", "tests/scripts", "tests/test_delivery_generation.py"],
        cwd=HERE.parent, capture_output=True, text=True, check=False,
    ).stdout.splitlines()
    nodes = {ln.strip() for ln in collected if "::" in ln}
    for sid, tests in index.items():
        for t in tests:
            base = t.split("[")[0]
            if base not in nodes:
                problems.append(f"{sid}: test node not found: {t}")
    for p in problems:
        print(p)
    if problems:
        return 1
    print(f"traceability ok: {len(expected)} scenarios, {sum(len(v) for v in index.values())} test nodes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
