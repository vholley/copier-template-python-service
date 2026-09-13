"""Shared fixtures for template tests.

Generation is slow (copier renders the whole tree), so projects are generated
once per session for each answer set and reused by every test that only reads
the result. Tests that modify a generated project copy it first.
"""

from __future__ import annotations

import shutil
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
