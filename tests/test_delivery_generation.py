"""Generation tests for the delivery system (spec S1, S2).

Red for plan step S1: C01, C02, C04. Later steps add their own tests here.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from tests.conftest import TEMPLATE, generate

DELIVERY_ONLY_PATHS = [
    "working",
    ".claude/settings.json",
    ".claude/commands",
    ".claude/skills",
    ".claude/agents",
    "scripts/delivery",
    "scripts/hooks",
    ".github/workflows/delivery-checks.yml",
    ".dockerignore",
    "MIGRATION.md",
]


def _tree(root: Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for p in root.rglob("*"):
        if p.is_file() and ".git/" not in str(p.relative_to(root)) + "/":
            out[str(p.relative_to(root))] = p.read_bytes()
    return out


class TestDeliveryOff:
    """C01: enable_delivery=false produces none of the delivery files and nothing else changes."""

    def test_delivery_off_has_no_delivery_paths(self, plain_project: Path) -> None:
        present = [p for p in DELIVERY_ONLY_PATHS if (plain_project / p).exists()]
        assert present == []

    def test_delivery_off_matches_base_template(self, plain_project: Path, delivery_project: Path) -> None:
        plain = _tree(plain_project)
        full = _tree(delivery_project)
        # Every file in the plain project must exist with identical bytes in the
        # delivery project, except files the delivery scaffold deliberately replaces.
        replaced = {
            "Makefile", "AGENTS.md", ".pre-commit-config.yaml", "pyproject.toml",
            ".github/workflows/ci.yml", ".github/pull_request_template.md",
            "README.md", "scripts/new-app.sh", ".copier-answers.yml",
        }
        diffs = [p for p, b in plain.items() if p not in replaced and full.get(p) != b]
        assert diffs == []


class TestDeliveryAnswers:
    """C02: the delivery answers land in CODEOWNERS and budgets.md; defaults render."""

    def test_no_owner_group_means_no_codeowners(self, delivery_project: Path) -> None:
        assert not (delivery_project / ".github/CODEOWNERS").exists()

    def test_owner_group_generates_codeowners(self, tmp_path: Path) -> None:
        project = generate(tmp_path, enable_delivery=True, owner_group="@acme/platform")
        text = (project / ".github/CODEOWNERS").read_text()
        assert "/working/architecture/      @acme/platform" in text
        assert "/.claude/" in text

    def test_paths_render_into_budgets(self, tmp_path: Path) -> None:
        project = generate(
            tmp_path,
            enable_delivery=True,
            high_risk_paths=["**/auth/**", "**/billing/**"],
            trivial_paths=["docs/**", "*.md"],
        )
        text = (project / "working/standards/budgets.md").read_text()
        assert "**/billing/**" in text
        assert "docs/**" in text

    def test_budget_defaults_present(self, delivery_project: Path) -> None:
        text = (delivery_project / "working/standards/budgets.md").read_text()
        for key in [
            "diff.trivial.max_lines: 50",
            "diff.standard.max_lines: 400",
            "coverage.diff.min: 0.90",
            "stop_hook.retry_cap: 3",
            "review.max_lines: 80",
        ]:
            assert key in text, key


class TestTasksAndMessage:
    """C04: _message_after_update names MIGRATION.md; tasks mention hooks and signing only when enabled."""

    def test_message_after_update_names_migration(self) -> None:
        conf = yaml.safe_load(Path(TEMPLATE, "copier.yaml").read_text())
        assert "MIGRATION.md" in conf["_message_after_update"]

    def test_skip_if_exists_lists_project_owned_files(self) -> None:
        conf = yaml.safe_load(Path(TEMPLATE, "copier.yaml").read_text())
        skip = set(conf["_skip_if_exists"])
        for pattern in [
            "working/spec/**",
            "working/architecture/**",
            "working/standards/budgets.md",
            "working/observations.md",
                ]:
            assert pattern in skip, pattern

    def test_tasks_mention_setup_only_when_enabled(self) -> None:
        conf = yaml.safe_load(Path(TEMPLATE, "copier.yaml").read_text())
        joined = "\n".join(str(t) for t in conf["_tasks"])
        assert "enable_delivery" in joined
        assert "make hooks" in joined
        assert "signing" in joined.lower()


class TestGitignore:
    """S2.1: docs/ stays ignored; working/ is not."""

    def test_docs_ignored_working_tracked(self, delivery_project: Path) -> None:
        subprocess.run(["git", "init", "-q"], cwd=delivery_project, check=True)
        docs = subprocess.run(
            ["git", "check-ignore", "-q", "docs/DEVELOPING.md"], cwd=delivery_project
        )
        working = subprocess.run(
            ["git", "check-ignore", "-q", "working/README.md"], cwd=delivery_project
        )
        assert docs.returncode == 0
        assert working.returncode == 1
