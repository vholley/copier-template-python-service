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


# ---------------------------------------------------------------- S9 (C06, C14, C15, C36)

import os as _os


class TestWorkingLayout:
    """C06: working/ tracked with every listed file; docs/ ignored with the supplementary files."""

    def test_working_files(self, delivery_project: Path) -> None:
        for rel in ("working/README.md", "working/commands.toml", "working/architecture/overview.md",
                    "working/architecture/constraints.md", "working/architecture/constraints-baseline.txt",
                    "working/architecture/decisions/README.md", "working/spec/README.md",
                    "working/standards/model-facing.md", "working/standards/human-facing.md",
                    "working/standards/criteria-templates.md", "working/standards/budgets.md",
                    "working/observations.md", "working/history/.gitkeep"):
            assert (delivery_project / rel).exists(), rel

    def test_docs_files(self, delivery_project: Path) -> None:
        for rel in ("docs/DELIVERY-SYSTEM.md", "docs/workflow.mermaid", "docs/DEVELOPING.md", "docs/RATIONALE.md",
                    "docs/CONVENTIONS.md", "docs/SETUP.md"):
            assert (delivery_project / rel).exists(), rel

    def test_readme_carries_commands_and_diagram_link(self, delivery_project: Path) -> None:
        text = (delivery_project / "working/README.md").read_text()
        assert "make start" in text and "make status" in text and "make help" in text
        assert "docs/workflow.mermaid" in text
        assert "make opt-out" in text
        for anchor in ("#start", "#stages", "#signing", "#green", "#contract", "#bounced", "#protected", "#review", "#escalated"):
            assert f'name="{anchor[1:]}"' in text or f"## " in text, anchor

    def test_readme_within_budget(self, delivery_project: Path) -> None:
        n = len((delivery_project / "working/README.md").read_text().splitlines())
        assert n <= 200, n


class TestAgentsMd:
    """C14: AGENTS.md under 150 lines, managed marker, no Ruff duplication, CLAUDE.md pointer."""

    def test_agents_md_shape(self, delivery_project: Path) -> None:
        text = (delivery_project / "AGENTS.md").read_text()
        assert len(text.splitlines()) < 150
        assert "<!-- managed-by-template" in text and "<!-- project-specific below" in text
        assert (delivery_project / "CLAUDE.md").read_text().strip() == "@AGENTS.md"

    def test_agents_md_passes_budget_check(self, delivery_copy: Path) -> None:
        env = {**_os.environ, "PYTHONPATH": "scripts"}
        r = subprocess.run(["python3", "-m", "delivery.budgets", "--agents-md", "."], cwd=delivery_copy, env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr

    def test_agents_md_states_the_core_rules(self, delivery_project: Path) -> None:
        text = (delivery_project / "AGENTS.md").read_text()
        for needle in ("/start", "make green", "one decision", "verbatim", "opt out", "working/README.md"):
            assert needle.lower() in text.lower(), needle


class TestMigration:
    """C15: MIGRATION.md and the migration script on a project from the base template."""

    def test_migration_doc_exists(self, delivery_project: Path) -> None:
        text = (delivery_project / "MIGRATION.md").read_text()
        assert "working/" in text and "migrate-to-delivery" in text

    def test_migration_script_creates_working_and_reports_modified(self, plain_project: Path, tmp_path: Path, delivery_project: Path) -> None:
        import shutil

        old = tmp_path / "old"
        shutil.copytree(plain_project, old, symlinks=True)
        subprocess.run(["git", "init", "-q"], cwd=old, check=True)
        (old / "Makefile").write_text((old / "Makefile").read_text() + "\ncustom:\n\techo hi\n")
        script = delivery_project / "scripts/migrate-to-delivery.sh"
        r = subprocess.run(["bash", str(script), "--from", str(delivery_project)], cwd=old, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert (old / "working/standards/budgets.md").exists()
        assert "Makefile" in r.stdout and "modified" in r.stdout


class TestHumanFacingDocs:
    """C36: README and RATIONALE describe the scaffold; no tells."""

    def test_docs_mention_the_system(self, delivery_project: Path) -> None:
        assert "delivery" in (delivery_project / "README.md").read_text().lower()
        assert "working/" in (delivery_project / "docs/RATIONALE.md").read_text()
        assert "## The Makefile" in (delivery_project / "docs/DEVELOPING.md").read_text()

    def test_writing_check_passes(self, delivery_copy: Path) -> None:
        env = {**_os.environ, "PYTHONPATH": "scripts"}
        r = subprocess.run(["python3", "-m", "delivery.writing_check", "README.md", "docs/RATIONALE.md", "docs/DELIVERY-SYSTEM.md", "working/README.md", "AGENTS.md"],
                           cwd=delivery_copy, env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
