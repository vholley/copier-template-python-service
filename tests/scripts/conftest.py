"""Make template/scripts importable so delivery scripts are tested in place."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent.parent / "template" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """An empty git repository with a develop branch and one commit."""
    subprocess.run(["git", "init", "-q", "-b", "develop"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.invalid"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("x\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "chore: init"], cwd=tmp_path, check=True)
    return tmp_path
