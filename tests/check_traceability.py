"""Fail if scenario directories and the traceability table disagree.

Reads tests/scenarios/expected_ids.txt (one scenario ID per line) and the
scenario test modules; every ID must have a test and every test must be listed.
Run: uv run python tests/check_traceability.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCENARIOS = HERE / "scenarios"


def main() -> int:
    expected = {
        line.strip()
        for line in (SCENARIOS / "expected_ids.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }
    found: set[str] = set()
    for f in SCENARIOS.glob("test_*.py"):
        found.update(m.replace("_", "-") for m in re.findall(r"def test_([A-Z]+_\d+)", f.read_text()))
    missing = sorted(expected - found)
    extra = sorted(found - expected)
    if missing or extra:
        print("traceability mismatch")
        for m in missing:
            print(f"  listed but no test: {m}")
        for e in extra:
            print(f"  test but not listed: {e}")
        return 1
    print(f"traceability ok: {len(expected)} scenarios")
    return 0


if __name__ == "__main__":
    sys.exit(main())
