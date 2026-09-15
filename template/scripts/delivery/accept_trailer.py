"""commit-msg hook: an acceptance trailer requires the `accept` commit type and vice versa.

Usage: accept_trailer.py <message-file>. Exit 0 ok, 1 malformed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def check(msg: str) -> str | None:
    """Return a problem description, or None."""
    subject = msg.splitlines()[0] if msg.strip() else ""
    has_trailer = re.search(r"^(Accept|Accept-Decision|Opt-Out):", msg, re.M) is not None
    is_accept = subject.startswith("accept(")
    if has_trailer and not is_accept:
        return (
            "a commit with an Accept:/Opt-Out: trailer must use the subject form "
            "accept(<scope>): <stage>"
        )
    if is_accept and not has_trailer:
        return "an accept(...) commit must carry an Accept: or Opt-Out: trailer"
    if is_accept and not re.match(r"^accept\(([\w-]+)\): [\w-]+$", subject):
        return "subject must be accept(<scope>): <stage>"
    return None


def main(argv: list[str]) -> int:
    """Entry point."""
    if not argv:
        return 1
    msg = Path(argv[0]).read_text()
    problem = check(msg)
    if problem:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
