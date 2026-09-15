"""Shared fixtures for template tests.

Generation is slow (copier renders the whole tree), so projects are generated
once per session for each answer set and reused by every test that only reads
the result. Tests that modify a generated project copy it first.
"""

from __future__ import annotations

import functools
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from copier import run_copy

TEMPLATE = str(Path(__file__).parent.parent)

BASE_ANSWERS: dict[str, Any] = {
    "project_name": "test-project",
    "python_version": "3.14",
    "app_framework": "minimal",
    "use_gcp": False,
    "include_docker": False,
    "include_terraform": False,
}


def generate(dest: Path, **overrides: Any) -> Path:
    """Render the template into dest with BASE_ANSWERS plus overrides."""
    data = {**BASE_ANSWERS, **overrides}
    run_copy(
        TEMPLATE,
        str(dest),
        data=data,
        defaults=True,
        overwrite=True,
        unsafe=True,
        quiet=True,
        vcs_ref="HEAD",
    )
    return dest


# The delivery scripts are invoked as `python3` by the Makefile and the CI
# workflows, which is fine on the Linux runners but is not a command on Windows
# and not guaranteed on macOS. Tests run the interpreter that is running them.
PYTHON = sys.executable


@functools.cache
def usable_bash() -> str | None:
    """A bash that actually runs, or None.

    On Windows `bash` often resolves to the WSL stub, which exists on PATH but
    fails with execvpe(/bin/bash) when no distribution is installed.
    """
    exe = shutil.which("bash")
    if exe is None:
        return None
    try:
        r = subprocess.run([exe, "-c", "echo ok"], capture_output=True, text=True, timeout=60)
    except OSError:
        return None
    return exe if r.returncode == 0 and r.stdout.strip() == "ok" else None


@functools.cache
def usable_make() -> str | None:
    """A make that actually runs, or None."""
    exe = shutil.which("make")
    if exe is None:
        return None
    try:
        r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=60)
    except OSError:
        return None
    return exe if r.returncode == 0 else None


def require_bash() -> str:
    """The template's shell scripts need a POSIX shell; README recommends WSL 2 on Windows."""
    exe = usable_bash()
    if exe is None:
        pytest.skip("no usable bash: the delivery shell scripts need a POSIX shell (WSL 2 on Windows)")
    return exe


def require_make() -> str:
    exe = usable_make()
    if exe is None:
        pytest.skip("no usable make: the Makefile needs GNU make and a POSIX shell")
    return exe


@pytest.fixture(scope="session")
def delivery_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A project generated with the delivery system enabled (read-only)."""
    return generate(tmp_path_factory.mktemp("delivery"), enable_delivery=True)


@pytest.fixture(scope="session")
def plain_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A project generated with the delivery system disabled (read-only)."""
    return generate(tmp_path_factory.mktemp("plain"), enable_delivery=False)


@pytest.fixture
def delivery_copy(delivery_project: Path, tmp_path: Path) -> Path:
    """A writable copy of the delivery project for tests that modify it."""
    dest = tmp_path / "project"
    shutil.copytree(delivery_project, dest, symlinks=True)
    return dest
