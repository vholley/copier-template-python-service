"""The command registry: working/commands.toml.

Every command the process offers is declared here once. `make help`, `/help`,
the README table, and `make status` are generated from it.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

REGISTRY_FILE = Path("working/commands.toml")
WHEN_ORDER = ("anywhere", "front-stage", "build", "defects", "review")


@dataclass(frozen=True)
class Command:
    """One registry entry."""

    name: str
    description: str
    when: str
    runner: str  # agent | human | both

    @property
    def slash(self) -> str:
        """Slash form."""
        return f"/{self.name}"

    @property
    def make(self) -> str:
        """Make form."""
        return f"make {self.name}"


def load(repo: Path) -> list[Command]:
    """Read the registry; missing file means no commands."""
    path = repo / REGISTRY_FILE
    if not path.exists():
        return []
    data = tomllib.loads(path.read_text())
    return [
        Command(
            str(entry["name"]),
            str(entry.get("description", "")),
            str(entry.get("when", "anywhere")),
            str(entry.get("runner", "both")),
        )
        for entry in data.get("command", [])
    ]
