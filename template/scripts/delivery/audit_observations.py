"""Delete expired observations (9.2); git history is the record."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from delivery.observe import OBS_FILE


def prune(text: str, today: str) -> tuple[str, list[str]]:
    """Return (new text, deleted ids)."""
    blocks = re.split(r"(?m)^(?=- O-\d+:)", text)
    head, entries = blocks[0], blocks[1:]
    kept: list[str] = []
    deleted: list[str] = []
    for e in entries:
        m = re.search(r"^\s*expires:\s*(\d{4}-\d{2}-\d{2})", e, re.M)
        oid = re.match(r"- (O-\d+):", e)
        if m and m.group(1) < today:
            deleted.append(oid.group(1) if oid else "?")
        else:
            kept.append(e)
    return head + "".join(kept), deleted


def main(argv: list[str]) -> int:
    """Entry point: [repo]."""
    repo = Path(argv[0]) if argv else Path.cwd()
    path = repo / OBS_FILE
    if not path.exists():
        return 0
    new, deleted = prune(path.read_text(), datetime.now(UTC).date().isoformat())
    path.write_text(new)
    for d in deleted:
        print(f"deleted expired observation {d}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
