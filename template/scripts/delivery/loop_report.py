"""The improvement-loop report (7.6, 11.3): labeled exits and other signals since base.

Labels are read from `Labels:` trailers that the post-merge job writes into the
merge commit message from the PR's GitHub labels, so the report needs no API.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from delivery import gitx

TRACKED = (
    "tier-override",
    "break-glass",
    "test-change-approved",
    "retroactive-chain",
    "bounced",
    "opted-out",
)


def render(repo: Path, base: str) -> str:
    """Markdown report."""
    by_label: dict[str, list[str]] = defaultdict(list)
    for sha, msg in gitx.commits(repo, f"{base}..HEAD"):
        m = re.search(r"^Labels:\s*(.+)$", msg, re.M)
        if not m:
            continue
        for label in (s.strip() for s in m.group(1).split(",")):
            if label in TRACKED:
                by_label[label].append(f"{sha[:8]} {msg.splitlines()[0]}")
    lines = ["# Improvement loop report", ""]
    for label in TRACKED:
        lines.append(f"## {label} ({len(by_label[label])})")
        lines.extend(f"- {e}" for e in by_label[label])
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    """Entry point: --base REF [repo]."""
    base = argv[argv.index("--base") + 1] if "--base" in argv else "main"
    rest = [a for i, a in enumerate(argv) if not a.startswith("--") and argv[i - 1] != "--base"]
    repo = Path(rest[0]) if rest else Path.cwd()
    print(render(repo, base), end="")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
