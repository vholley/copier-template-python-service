"""Record a residual observation (9.2).

Hypothesized consequences are not recorded; observed consequences are defects
and are routed to make start; inferred ones are recorded with an expiry at the
next audit date.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from delivery.block import fail

OBS_FILE = Path("working/observations.md")
AUDIT_INTERVAL_DAYS = 7


def _arg(argv: list[str], name: str) -> str:
    return argv[argv.index(name) + 1] if name in argv else ""


def next_id(text: str) -> str:
    """O-<n+1>."""
    ids = [int(m) for m in re.findall(r"^- O-(\d+):", text, re.M)]
    return f"O-{(max(ids) if ids else 0) + 1}"


def main(argv: list[str]) -> int:
    """Entry point: --file --line --what --consequence --provenance --source [repo]."""
    keys = ("--file", "--line", "--what", "--consequence", "--provenance", "--source")
    values = {k: _arg(argv, k) for k in keys}
    if not all(values.values()):
        return fail(
            "usage",
            "all of --file --line --what --consequence --provenance --source are required",
            "an observation without a concrete consequence is not recorded",
            ["see working/README.md#observations"],
            "working/README.md#observations",
            env=True,
        )
    rest = [a for i, a in enumerate(argv) if not a.startswith("--") and argv[i - 1] not in keys]
    repo = Path(rest[0]) if rest else Path.cwd()
    prov = values["--provenance"]
    if prov.startswith("hypothesized"):
        print("not recorded: a hypothesized consequence is not an observation (9.2)")
        return 0
    if prov.startswith("observed"):
        print(
            "this is a defect, not an observation: an observed consequence violates a written "
            "statement. NEXT: make start (fix a bug)"
        )
        return 0
    path = repo / OBS_FILE
    text = path.read_text() if path.exists() else "# Observations\n"
    oid = next_id(text)
    expires = (datetime.now(UTC) + timedelta(days=AUDIT_INTERVAL_DAYS)).date().isoformat()
    entry = (
        f"- {oid}: {values['--file']}:{values['--line']} {values['--what']}\n"
        f"  consequence: {values['--consequence']}\n  provenance: {prov}\n"
        f"  source: {values['--source']}\n  expires: {expires}\n"
    )
    path.write_text(text.rstrip("\n") + "\n" + entry)
    print(f"recorded {oid}, expires {expires}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
