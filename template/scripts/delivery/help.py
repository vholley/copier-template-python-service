"""`make help` and `/help`: every command, grouped by when it applies (19.7).

help.check(repo) reports registry entries without a command file and command
files without an entry (EXP-11).
"""

from __future__ import annotations

from pathlib import Path

from delivery import registry

RUNNER_NOTE = {"human": "engineer only", "agent": "agent", "both": "either"}


def render(repo: Path) -> str:
    """The help text."""
    cmds = registry.load(repo)
    if not cmds:
        return "No commands registered (working/commands.toml is missing)."
    lines: list[str] = ["Commands (make <name> or /<name>; runner in brackets)", ""]
    for when in registry.WHEN_ORDER:
        group = [c for c in cmds if c.when == when]
        if not group:
            continue
        lines.append(f"{when}:")
        width = max(len(c.name) for c in group)
        lines.extend(
            f"  {c.name.ljust(width)}  {c.description}  [{RUNNER_NOTE.get(c.runner, c.runner)}]"
            for c in group
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def check(repo: Path) -> list[str]:
    """Registry and .claude/commands must agree."""
    problems: list[str] = []
    cmds = {c.name for c in registry.load(repo)}
    cdir = repo / ".claude" / "commands"
    files: set[str] = {p.stem for p in cdir.glob("*.md")} if cdir.exists() else set()
    problems.extend(
        f"registry entry {n} has no .claude/commands/{n}.md" for n in sorted(cmds - files)
    )
    problems.extend(f".claude/commands/{n}.md has no registry entry" for n in sorted(files - cmds))
    return problems


def main(argv: list[str]) -> int:
    """Entry point: print help, or --check to verify consistency."""
    rest = [a for a in argv if not a.startswith("--")]
    repo = Path(rest[0]) if rest else Path.cwd()
    if "--check" in argv:
        problems = check(repo)
        for p in problems:
            print(p)
        return 1 if problems else 0
    print(render(repo), end="")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
