"""Thin git wrappers.

Every script reaches git through here so tests can point it at a temporary
repository by passing the repo path.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

GIT = shutil.which("git") or "/usr/bin/git"


def run(repo: Path, *args: str, check: bool = True) -> str:
    """Run a git command in repo and return stdout; raise on failure when check is set."""
    result = subprocess.run(
        [GIT, "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


class UnbornBranchError(RuntimeError):
    """The repository has no commits, so HEAD names a branch that does not exist yet.

    Generation makes the scaffold commit, so this is reachable only when that was
    skipped -- git had no author identity -- or when someone re-initialised the
    repository. Callers catch it and say what to do next.
    """


def current_branch(repo: Path) -> str:
    """Name of the checked-out branch. Raises UnbornBranchError before the first commit."""
    if run(repo, "rev-parse", "--verify", "--quiet", "HEAD", check=False).strip() == "":
        raise UnbornBranchError(str(repo))
    return run(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()


def branch_exists(repo: Path, name: str) -> bool:
    """True when a local branch with this name exists."""
    return run(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}", check=False) != ""


def commits(repo: Path, ref: str = "HEAD") -> list[tuple[str, str]]:
    """(sha, full message) for every commit reachable from ref, newest first."""
    out = run(repo, "log", "--format=%H%x1e%B%x1f", ref, check=False)
    entries: list[tuple[str, str]] = []
    for chunk in out.split("\x1f"):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        sha, _, body = chunk.partition("\x1e")
        entries.append((sha.strip(), body))
    return entries


def is_clean(repo: Path, path: str) -> bool:
    """True when path has no uncommitted changes (tracked and modified, or untracked)."""
    return run(repo, "status", "--porcelain", "--", path, check=False).strip() == ""
