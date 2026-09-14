"""C29: the build followed its own discipline.

For every delivery script, the commit that first added a test for it precedes
the commit that first added the script (red before green, D5). Scripts that are
pure plumbing (the package files) are exempt and listed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "template/scripts/delivery"
EXEMPT = {"__init__", "__main__"}
# module -> the test file that covers it (the first commit adding that file is the red commit)
COVERED_BY = {
    "block": "tests/scripts/test_shared_layer.py",
    "state": "tests/scripts/test_shared_layer.py",
    "gitx": "tests/scripts/test_shared_layer.py",
    "paths": "tests/scripts/test_checks.py",
    "constraints": "tests/scripts/test_checks.py",
    "budgets": "tests/scripts/test_checks.py",
    "spec_coverage": "tests/scripts/test_checks.py",
    "spec_check": "tests/scripts/test_checks.py",
    "deploy_surface": "tests/scripts/test_checks.py",
    "test_ratchet": "tests/scripts/test_tdd_checks.py",
    "ordering": "tests/scripts/test_tdd_checks.py",
    "diff_coverage": "tests/scripts/test_tdd_checks.py",
    "signers": "tests/scripts/test_contract.py",
    "pr_contract": "tests/scripts/test_contract.py",
    "compute_tier": "tests/scripts/test_contract.py",
    "start": "tests/scripts/test_commands.py",
    "status": "tests/scripts/test_commands.py",
    "accept": "tests/scripts/test_commands.py",
    "help": "tests/scripts/test_commands.py",
    "registry": "tests/scripts/test_commands.py",
    "post_merge": "tests/scripts/test_commands.py",
    "observe": "tests/scripts/test_commands.py",
    "audit_observations": "tests/scripts/test_commands.py",
    "vendored_check": "tests/scripts/test_commands.py",
    "loop_report": "tests/scripts/test_commands.py",
    "hooks": "tests/scripts/test_hooks.py",
    "accept_trailer": "tests/test_delivery_generation.py",
    "state_cli": "tests/test_delivery_generation.py",
    "green_runner": "tests/test_delivery_generation.py",
    "writing_check": "tests/test_delivery_generation.py",
    "log": "tests/test_delivery_generation.py",
}


def first_commit_time(path: str) -> int:
    out = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%ct", "--follow", "--", path],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()
    assert out, f"{path} has no add commit"
    return int(out[-1])


def test_every_script_is_listed() -> None:
    modules = {p.stem for p in SCRIPTS.glob("*.py")} - EXEMPT
    assert modules == set(COVERED_BY), sorted(modules ^ set(COVERED_BY))


@pytest.mark.parametrize("module", sorted(COVERED_BY))
def test_red_precedes_green(module: str) -> None:
    red = first_commit_time(COVERED_BY[module])
    green = first_commit_time(f"template/scripts/delivery/{module}.py")
    assert red <= green, f"{module}: test file added after the script"


def test_scripts_pass_generated_lint_and_types(delivery_project: Path) -> None:
    """The delivery scripts pass the ruff rules a generated project enforces on itself.

    Run from inside the generated project, as `make lint` does: ruff resolves
    per-file-ignores globs against the project root, so linting from outside with
    --config reports ignored rules (T20, S603) as errors.
    """
    lint = subprocess.run(
        ["uv", "run", "ruff", "check", "--no-cache", "scripts/delivery"],
        cwd=delivery_project, capture_output=True, text=True,
    )
    assert lint.returncode == 0, lint.stdout + lint.stderr
    types = subprocess.run(["uv", "run", "pyright", "-p", "pyrightconfig.strict.json"], cwd=ROOT, capture_output=True, text=True)
    assert types.returncode == 0, types.stdout[-2000:]
