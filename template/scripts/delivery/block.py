"""The four-line block message every refusal in the system uses.

    BLOCKED  <rule-id>: <what was refused>
    WHY      <the rule in plain language>
    NEXT     <a command that moves forward>
             <optional second option>
    MORE     working/README.md#<anchor>

This module is the only place that prints "BLOCKED". Scripts and hooks call
fail() and return its result as their exit code. MORE must point into
working/README.md because docs/ is untracked and absent on a fresh clone.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

MORE_PREFIX = "working/README.md#"
_LABEL_WIDTH = 9  # "BLOCKED  " / "WHY      " / "NEXT     " / "MORE     "


@dataclass(frozen=True)
class Block:
    """A parsed block message."""

    rule_id: str
    what: str
    why: str
    next_: list[str] = field(default_factory=lambda: [])
    more: str = ""


def _label(name: str) -> str:
    return name.ljust(_LABEL_WIDTH)


def render(rule_id: str, what: str, why: str, next_: list[str], more: str) -> str:
    """Return the block as text. Raises ValueError for a message with no exit."""
    if not next_ or not all(n.strip() for n in next_):
        raise ValueError("NEXT must name at least one command")
    if not more.startswith(MORE_PREFIX):
        raise ValueError(f"MORE must point into {MORE_PREFIX}<anchor>, got {more!r}")
    lines = [
        f"{_label('BLOCKED')}{rule_id}: {what}",
        f"{_label('WHY')}{why}",
        f"{_label('NEXT')}{next_[0]}",
    ]
    lines.extend(f"{' ' * _LABEL_WIDTH}{n}" for n in next_[1:])
    lines.append(f"{_label('MORE')}{more}")
    return "\n".join(lines)


def fail(
    rule_id: str, what: str, why: str, next_: list[str], more: str, *, env: bool = False
) -> int:
    """Print the block to stderr and return the exit code (1, or 2 for environment errors)."""
    print(render(rule_id, what, why, next_, more), file=sys.stderr)
    return 2 if env else 1


def parse(text: str) -> Block:
    """Inverse of render(), used by tests and by the suite's EXP-01 collector."""
    lines = text.splitlines()
    head = lines[0][_LABEL_WIDTH:]
    rule_id, _, what = head.partition(": ")
    why = lines[1][_LABEL_WIDTH:]
    next_ = [lines[2][_LABEL_WIDTH:]]
    idx = 3
    while idx < len(lines) and not lines[idx].startswith("MORE"):
        next_.append(lines[idx][_LABEL_WIDTH:])
        idx += 1
    more = lines[idx][_LABEL_WIDTH:] if idx < len(lines) else ""
    return Block(rule_id, what, why, next_, more)
