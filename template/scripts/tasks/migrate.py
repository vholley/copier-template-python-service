"""Adopt the delivery system in a project generated from an earlier template version.

Was scripts/migrate-to-delivery.sh. See MIGRATION.md.

Usage: python scripts/task.py migrate --from <a freshly generated project>
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from tasks.console import error, info

# Files copied out of the reference project when this project lacks them.
WORKING_FILES = [
    "README.md",
    "commands.toml",
    "observations.md",
    "log.md",
    "standards/model-facing.md",
    "standards/human-facing.md",
    "standards/criteria-templates.md",
    "standards/budgets.md",
    "architecture/overview.md",
    "architecture/constraints.md",
    "architecture/constraints-baseline.txt",
    "architecture/decisions/README.md",
    "spec/README.md",
    "history/.gitkeep",
]

# Directories copied wholesale; existing files are kept.
TREES = [".claude", "scripts/delivery", "scripts/hooks", "scripts/tasks", ".github/workflows"]

# Files the template replaces; report the ones the project had modified.
REPLACED = [
    "Makefile",
    ".github/workflows/ci.yml",
    "AGENTS.md",
    ".github/pull_request_template.md",
    ".pre-commit-config.yaml",
]


def _modified(repo: Path, rel: str) -> bool:
    """True when rel is tracked and differs from HEAD."""
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    if tracked.returncode != 0:
        return False
    diff = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", rel],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    return diff.returncode != 0


def _copy_working(repo: Path, src: Path) -> None:
    info("creating working/ (existing files are kept)")
    for rel in WORKING_FILES:
        dest = repo / "working" / rel
        source = src / "working" / rel
        if dest.exists() or not source.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        print(f"   added working/{rel}")


def _copy_trees(repo: Path, src: Path) -> None:
    info("copying the delivery scripts, hooks and workflows")
    for tree in TREES:
        source = src / tree
        if not source.is_dir():
            continue
        for f in sorted(source.rglob("*")):
            if not f.is_file():
                continue
            dest = repo / tree / f.relative_to(source)
            if dest.exists():
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            print(f"   added {dest.relative_to(repo).as_posix()}")


def _report_replaced(repo: Path) -> None:
    info("replaced files you had modified (merge by hand):")
    for rel in REPLACED:
        if (repo / rel).exists() and _modified(repo, rel):
            print(f"   {rel}: modified locally")


def main(argv: list[str]) -> int:
    """Entry point: --from <generated-project>."""
    if len(argv) < 2 or argv[0] != "--from" or not argv[1]:
        error("usage: python scripts/task.py migrate --from <a freshly generated project>")
        error("see MIGRATION.md")
        return 2
    src = Path(argv[1]).expanduser().resolve()
    if not (src / "working").is_dir():
        error(f"{src} does not look like a project generated with the delivery system")
        return 2

    repo = Path.cwd()
    _copy_working(repo, src)
    _copy_trees(repo, src)
    _report_replaced(repo)
    print("done. Next: make hooks (Windows: uv run pre-commit install --install-hooks)")
    print("see MIGRATION.md")
    return 0
