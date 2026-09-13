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


# ------------------------------------------------------------------- S8 (C09 to C12, C16)

import re as _re

import yaml as _yaml


class TestGithubDir:
    """C09: workflows, setup action, PR template."""

    WORKFLOWS = ["ci.yml", "delivery-checks.yml", "review-agents.yml", "spec-draft.yml", "post-merge.yml", "entropy-audit.yml"]

    def test_workflows_and_action_exist_and_parse(self, delivery_project: Path) -> None:
        for name in self.WORKFLOWS:
            path = delivery_project / ".github/workflows" / name
            assert path.exists(), name
            _yaml.safe_load(path.read_text())
        _yaml.safe_load((delivery_project / ".github/actions/setup/action.yml").read_text())

    def test_workflows_reference_only_existing_targets_and_scripts(self, delivery_project: Path) -> None:
        makefile = (delivery_project / "Makefile").read_text()
        targets = set(_re.findall(r"^([a-zA-Z_-]+):", makefile, _re.M))
        for name in self.WORKFLOWS:
            text = (delivery_project / ".github/workflows" / name).read_text()
            for t in _re.findall(r"\bmake ([a-zA-Z_-]+)", text):
                assert t in targets, f"{name}: make {t}"
            for s in _re.findall(r"scripts/([\w/.-]+\.(?:py|sh))", text):
                assert (delivery_project / "scripts" / s).exists(), f"{name}: scripts/{s}"

    def test_pr_template_has_required_sections(self, delivery_project: Path) -> None:
        text = (delivery_project / ".github/pull_request_template.md").read_text()
        for sec in ("## Intent", "## Risk", "## What changed, by criterion", "## Decisions", "## Promotions", "## Evidence", "Intent-match:"):
            assert sec in text, sec


class TestMakefile:
    """C10: added targets; ci runs the three checks."""

    def test_added_targets_present(self, delivery_project: Path) -> None:
        text = (delivery_project / "Makefile").read_text()
        for t in ("constraints", "budgets", "spec-coverage", "green", "contract", "start", "status", "accept-prepare", "accept",
                  "adopt-branch", "abandon", "amend", "opt-out", "rebuild", "intent", "clarify", "spec", "plan", "red", "implement", "diagnose"):
            assert _re.search(rf"^{t}:", text, _re.M), t

    def test_ci_includes_delivery_checks(self, delivery_project: Path) -> None:
        text = (delivery_project / "Makefile").read_text()
        m = _re.search(r"^ci:\s*(.+)$", text, _re.M)
        assert m and all(t in m.group(1) for t in ("constraints", "budgets", "spec-coverage"))

    def test_stage_stubs_print_slash_command(self, delivery_project: Path) -> None:
        out = subprocess.run(["make", "-s", "intent"], cwd=delivery_project, capture_output=True, text=True, check=False).stdout
        assert "/intent" in out


class TestPreCommit:
    """C11: local hooks, accept type, trailer validator."""

    def test_local_hooks_and_accept_type(self, delivery_project: Path) -> None:
        conf = _yaml.safe_load((delivery_project / ".pre-commit-config.yaml").read_text())
        ids = {h["id"] for r in conf["repos"] for h in r["hooks"]}
        assert {"delivery-constraints", "delivery-budgets", "delivery-accept-trailer"} <= ids
        conv = next(h for r in conf["repos"] for h in r["hooks"] if h["id"] == "conventional-pre-commit")
        assert "accept" in " ".join(conv.get("args", []))

    def test_trailer_validator_behaviour(self, delivery_copy: Path) -> None:
        script = delivery_copy / "scripts/delivery/accept_trailer.py"
        good = delivery_copy / "good.msg"
        good.write_text("accept(work-x): intent\n\nAccepts.\n\nAccept: intent sha256=" + "a" * 64 + "\nWork-Item: x\n")
        bad = delivery_copy / "bad.msg"
        bad.write_text("feat: accept\n\nAccept: intent sha256=" + "a" * 64 + "\n")
        env = {"PYTHONPATH": "scripts"}
        assert subprocess.run(["python3", str(script), str(good)], cwd=delivery_copy, env={**__import__("os").environ, **env}).returncode == 0
        assert subprocess.run(["python3", str(script), str(bad)], cwd=delivery_copy, env={**__import__("os").environ, **env}).returncode == 1


class TestPyproject:
    """C12: ruff additions, import-linter, markers, dev deps."""

    def test_pyproject_additions(self, delivery_project: Path) -> None:
        text = (delivery_project / "pyproject.toml").read_text()
        for needle in ('"C901"', '"PLR0913"', '"TID251"', "[tool.importlinter]", "[tool.ruff.lint.mccabe]",
                       'markers = [', 'spec(anchor)', '"import-linter', '"diff-cover', '"mutmut'):
            assert needle in text, needle

    def test_uv_lock_succeeds(self, delivery_copy: Path) -> None:
        r = subprocess.run(["uv", "lock"], cwd=delivery_copy, capture_output=True, text=True, check=False)
        assert r.returncode == 0, r.stderr[-2000:]


class TestDeployable:
    """C16: .dockerignore and deploy_surface on the generated project."""

    def test_dockerignore_and_surface_check(self, delivery_copy: Path) -> None:
        text = (delivery_copy / ".dockerignore").read_text()
        for entry in (".claude/", ".work/", "working/", "docs/", "scripts/", ".github/", "**/tests/", "*.md"):
            assert entry in text.splitlines(), entry
        env = {**__import__("os").environ, "PYTHONPATH": "scripts"}
        assert subprocess.run(["python3", "-m", "delivery.deploy_surface", "."], cwd=delivery_copy, env=env).returncode == 0
        (delivery_copy / "apps/x").mkdir(parents=True)
        (delivery_copy / "apps/x/Dockerfile").write_text("FROM python\nCOPY . .\n")
        assert subprocess.run(["python3", "-m", "delivery.deploy_surface", "."], cwd=delivery_copy, env=env).returncode == 1
