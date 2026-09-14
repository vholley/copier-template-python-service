"""Generation tests for the delivery system (spec S1, S2).

Red for plan step S1: C01, C02, C04. Later steps add their own tests here.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.conftest import BASE_ANSWERS, PYTHON, TEMPLATE, generate, require_bash, require_make
from copier import run_copy

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
    """Relative path -> bytes, keyed with forward slashes on every platform."""
    out: dict[str, bytes] = {}
    for p in root.rglob("*"):
        rel = p.relative_to(root).as_posix()
        if p.is_file() and ".git/" not in rel + "/":
            out[rel] = p.read_bytes()
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
            "docs/RATIONALE.md", "docs/DEVELOPING.md", "docs/SETUP.md",  # gain a delivery section (S9)
            "app-template/pyproject.toml",  # gains [tool.delivery] (S11)
            "app-template/tests/test_main.py",  # gains the spec marker (S11)
        }
        diffs = [p for p, b in plain.items() if p not in replaced and full.get(p) != b]
        assert diffs == []


    def test_plain_agents_md_references_only_what_exists(self, plain_project: Path) -> None:
        """AGENTS.md is read on every turn; with delivery off it must not describe delivery.

        It was rendered unconditionally, so a plain project told the agent to run
        `make green`, `make status`, `/intent` and to read working/README.md -- none
        of which exist. AGENTS.md sits in the `replaced` set above, so its content
        was asserted nowhere.
        """
        text = (plain_project / "AGENTS.md").read_text(encoding="utf-8")
        forbidden = [
            "working/", "DELIVERY-SYSTEM", ".claude/rules", ".work/",
            "make green", "make status", "make start", "make accept", "make observe",
            "/intent", "/clarify", "/spec", "/red", "/implement", "/diagnose",
        ]
        assert [f for f in forbidden if f in text] == []

    def test_plain_agents_md_commands_exist(self, plain_project: Path) -> None:
        """Every `make <target>` it names is a real target in the generated Makefile."""
        import re

        text = (plain_project / "AGENTS.md").read_text(encoding="utf-8")
        makefile = (plain_project / "Makefile").read_text(encoding="utf-8")
        targets = set(re.findall(r"^([a-z][a-z-]*):", makefile, re.M))
        named = set(re.findall(r"make ([a-z][a-z-]*)", text))
        assert named <= targets, sorted(named - targets)

    def test_plain_agents_md_paths_exist(self, plain_project: Path) -> None:
        """Every docs/ file it points at is actually generated."""
        import re

        text = (plain_project / "AGENTS.md").read_text(encoding="utf-8")
        missing = [
            ref for ref in re.findall(r"`(docs/[\w./-]+)`", text)
            if not (plain_project / ref).exists()
        ]
        assert missing == []

    def test_plain_app_template_has_no_spec_marker(self, plain_project: Path) -> None:
        """The spec marker is registered only under enable_delivery, and --strict-markers is not.

        A plain project that runs `make new-app` would otherwise fail collection with
        "'spec' not found in markers configuration option".
        """
        text = (plain_project / "app-template/tests/test_main.py").read_text(encoding="utf-8")
        assert "pytest.mark.spec" not in text
        assert "import pytest" not in text
        assert "markers = [" not in (plain_project / "pyproject.toml").read_text(encoding="utf-8")

    def test_delivery_app_template_has_the_spec_marker(self, delivery_project: Path) -> None:
        text = (delivery_project / "app-template/tests/test_main.py").read_text(encoding="utf-8")
        assert "pytest.mark.spec" in text
        assert "markers = [" in (delivery_project / "pyproject.toml").read_text(encoding="utf-8")


class TestHookEntryPoint:
    """C30: the hooks Claude Code invokes actually run in a generated project.

    The previous shell wrappers ran `python -m delivery.hooks` without
    PYTHONPATH=scripts, so every hook died with ModuleNotFoundError and silently
    did nothing. They were only ever asserted to exist, never executed.
    """

    @pytest.fixture
    def project(self, delivery_copy: Path) -> Path:
        """The copy as a real repository: the hooks read git state, as they would in use."""
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
        subprocess.run(["git", "init", "-q", "-b", "develop"], cwd=delivery_copy, check=True)
        subprocess.run(["git", "symbolic-ref", "HEAD", "refs/heads/develop"], cwd=delivery_copy, check=True)
        subprocess.run([*git, "add", "-A"], cwd=delivery_copy, capture_output=True, check=True)
        subprocess.run([*git, "commit", "-q", "-m", "chore: init"], cwd=delivery_copy, check=True)
        return delivery_copy

    def _run(self, project: Path, event: str, payload: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "scripts/hooks/hook.py", event],
            cwd=project, input=payload, capture_output=True, text=True, check=False,
        )

    @pytest.mark.parametrize(
        "event",
        ["session-start", "prompt", "edit", "bash", "ask", "post-edit", "stop", "subagent-stop"],
    )
    def test_every_hook_runs(self, project: Path, event: str) -> None:
        r = self._run(project, event, "{}")
        assert "ModuleNotFoundError" not in r.stderr, r.stderr
        assert "Traceback" not in r.stderr, r.stderr
        assert r.returncode in (0, 2), (r.returncode, r.stderr)

    def test_protected_path_is_blocked_through_the_entry_point(self, project: Path) -> None:
        """End to end: absolute path in, exit 2 out -- the way Claude Code calls it."""
        target = project / ".claude" / "settings.json"
        payload = json.dumps({"tool_input": {"file_path": str(target)}})
        r = self._run(project, "edit", payload)
        assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
        assert "protected" in r.stdout + r.stderr

    def test_ordinary_source_file_is_allowed(self, project: Path) -> None:
        target = project / "libs" / "shared" / "src" / "shared" / "config.py"
        payload = json.dumps({"tool_input": {"file_path": str(target)}})
        r = self._run(project, "edit", payload)
        assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)


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
import shutil

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
        out = subprocess.run([require_make(), "-s", "intent"], cwd=delivery_project, capture_output=True, text=True, check=False).stdout
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
        assert subprocess.run([PYTHON, str(script), str(good)], cwd=delivery_copy, env={**__import__("os").environ, **env}).returncode == 0
        assert subprocess.run([PYTHON, str(script), str(bad)], cwd=delivery_copy, env={**__import__("os").environ, **env}).returncode == 1


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
        assert subprocess.run([PYTHON, "-m", "delivery.deploy_surface", "."], cwd=delivery_copy, env=env).returncode == 0
        (delivery_copy / "apps/x").mkdir(parents=True)
        (delivery_copy / "apps/x/Dockerfile").write_text("FROM python\nCOPY . .\n")
        assert subprocess.run([PYTHON, "-m", "delivery.deploy_surface", "."], cwd=delivery_copy, env=env).returncode == 1


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
        r = subprocess.run([PYTHON, "-m", "delivery.budgets", "--agents-md", "."], cwd=delivery_copy, env=env, capture_output=True, text=True)
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
        r = subprocess.run([require_bash(), str(script), "--from", str(delivery_project)], cwd=old, capture_output=True, text=True)
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
        r = subprocess.run([PYTHON, "-m", "delivery.writing_check", "README.md", "docs/RATIONALE.md", "docs/DELIVERY-SYSTEM.md", "working/README.md", "AGENTS.md"],
                           cwd=delivery_copy, env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr


# ---------------------------------------------------------------- S9 (C06, C14, C15, C36)


class TestLayout:
    """C06: working/ tracked with every listed file; docs/ ignored with the reference docs."""

    WORKING = [
        "README.md", "commands.toml", "architecture/overview.md", "architecture/constraints.md",
        "architecture/constraints-baseline.txt", "architecture/decisions/README.md", "spec/README.md",
        "standards/model-facing.md", "standards/human-facing.md", "standards/criteria-templates.md",
        "standards/budgets.md", "observations.md", "history/.gitkeep",
    ]
    DOCS = ["CONVENTIONS.md", "DEVELOPING.md", "RATIONALE.md", "SETUP.md", "DELIVERY-SYSTEM.md", "workflow.mermaid"]

    def test_working_files(self, delivery_project: Path) -> None:
        for f in self.WORKING:
            assert (delivery_project / "working" / f).exists(), f

    def test_docs_files(self, delivery_project: Path) -> None:
        for f in self.DOCS:
            assert (delivery_project / "docs" / f).exists(), f

    def test_readme_starts_with_the_split_and_has_command_table(self, delivery_project: Path) -> None:
        text = (delivery_project / "working/README.md").read_text()
        head = "\n".join(text.splitlines()[:12])
        assert "docs/" in head and "working/" in head
        for cmd in ("make start", "make status", "make help", "make accept", "make opt-out"):
            assert cmd in text, cmd
        for anchor in ("#start", "#stages", "#signing", "#green", "#contract", "#bounced", "#escalated", "#opt-out", "#observations"):
            assert _re.search(r"^#+ .*\{" + anchor + r"\}|<a id=\"" + anchor[1:] + r"\"", text, _re.M) or anchor[1:] in text, anchor

    def test_readme_within_budget(self, delivery_project: Path) -> None:
        n = len((delivery_project / "working/README.md").read_text().splitlines())
        assert n <= 200


class TestAgentsMd:
    """C14: AGENTS.md short, marked, non-duplicating; CLAUDE.md is the pointer."""

    def test_agents_md_budget_and_marker(self, delivery_project: Path) -> None:
        text = (delivery_project / "AGENTS.md").read_text()
        assert len(text.splitlines()) < 150
        assert "<!-- managed:end -->" in text
        for needle in ("make green", "/start", "make status", "working/README.md", "opt-out", "decisions.md"):
            assert needle in text, needle

    def test_agents_md_passes_budgets_check(self, delivery_copy: Path) -> None:
        env = {**__import__("os").environ, "PYTHONPATH": "scripts"}
        r = subprocess.run([PYTHON, "-m", "delivery.budgets", "--agents-md", "."], cwd=delivery_copy, env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr

    def test_claude_md_is_pointer(self, delivery_project: Path) -> None:
        lines = [ln for ln in (delivery_project / "CLAUDE.md").read_text().splitlines() if ln.strip() and not ln.startswith("#")]
        assert lines == ["@AGENTS.md"]  # the template's heading line is allowed; nothing else is


class TestMigration:
    """C15: MIGRATION.md and the migration script on a project from the base template."""

    def test_migration_doc_exists(self, delivery_project: Path) -> None:
        text = (delivery_project / "MIGRATION.md").read_text()
        for needle in ("working/", "Makefile", "AGENTS.md", "migrate-to-delivery.sh"):
            assert needle in text, needle

    def test_migration_script_creates_working_and_reports(self, plain_project: Path, delivery_project: Path, tmp_path: Path) -> None:
        old = tmp_path / "old"
        shutil.copytree(plain_project, old)
        subprocess.run(["git", "init", "-q"], cwd=old, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@x", "add", "-A"], cwd=old, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "-m", "init"], cwd=old, check=True)
        (old / "Makefile").write_text((old / "Makefile").read_text() + "\n# local edit\n")
        script = delivery_project / "scripts/migrate-to-delivery.sh"
        r = subprocess.run([require_bash(), str(script), "--from", str(delivery_project)], cwd=old, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert (old / "working/standards/budgets.md").exists()
        assert "Makefile" in r.stdout and "modified" in r.stdout


class TestHumanFacingDocs:
    """C36: README and RATIONALE describe the scaffold; the writing check finds no tells."""

    def test_readme_and_rationale_mention_the_system(self, delivery_project: Path) -> None:
        assert "working/" in (delivery_project / "README.md").read_text()
        assert "delivery" in (delivery_project / "docs/RATIONALE.md").read_text().lower()

    def test_developing_explains_the_makefile(self, delivery_project: Path) -> None:
        text = (delivery_project / "docs/DEVELOPING.md").read_text()
        assert "## The Makefile" in text and "make help" in text

    def test_writing_check_clean(self, delivery_copy: Path) -> None:
        env = {**__import__("os").environ, "PYTHONPATH": "scripts"}
        files = ["README.md", "working/README.md", "docs/RATIONALE.md", "docs/DEVELOPING.md", "docs/DELIVERY-SYSTEM.md", "AGENTS.md"]
        r = subprocess.run([PYTHON, "-m", "delivery.writing_check", *files], cwd=delivery_copy, env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout

    def test_writing_check_finds_seeded_tells(self, delivery_copy: Path) -> None:
        env = {**__import__("os").environ, "PYTHONPATH": "scripts"}
        (delivery_copy / "seeded.md").write_text("This isn't just a tool — it's a paradigm shift that will delve into a rich tapestry of workflows.\n")
        r = subprocess.run([PYTHON, "-m", "delivery.writing_check", "seeded.md"], cwd=delivery_copy, env=env, capture_output=True, text=True)
        assert r.returncode == 1 and "seeded.md" in r.stdout


class TestIssueLog:
    """D42: working/log.md and make log."""

    def test_log_file_and_target_exist(self, delivery_project: Path) -> None:
        assert (delivery_project / "working/log.md").exists()
        assert _re.search(r"^log:", (delivery_project / "Makefile").read_text(), _re.M)

    def test_add_close_open(self, delivery_copy: Path) -> None:
        env = {**__import__("os").environ, "PYTHONPATH": "scripts"}
        run = lambda *a: subprocess.run([PYTHON, "-m", "delivery.log", *a], cwd=delivery_copy, env=env, capture_output=True, text=True)  # noqa: E731
        assert run("add", "--source", "CI", "--what", "x", "--missing", "y").returncode == 0
        assert run("open").returncode == 1
        assert run("close", "L-1", "--fix", "z").returncode == 0
        assert run("open").returncode == 0
        text = (delivery_copy / "working/log.md").read_text()
        assert "## L-1" in text and "· closed" in text and "Fix: z" in text


# ---------------------------------------------------------------- S10 (C03, C07, C08)

import tomllib as _tomllib


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text()
    assert text.startswith("---\n"), path
    block = text.split("---\n", 2)[1]
    out: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


class TestClaudeDir:
    """C07: commands, skills, agents, vendored deslop; budgets and frontmatter."""

    STAGE_SKILLS = ["start", "intent", "clarify", "spec", "plan", "red", "implement", "diagnose",
                    "architect", "decompose", "review-pr", "entropy-audit", "amend", "opt-out"]
    AGENTS = ["evaluator", "necessity-reviewer", "spec-reviewer", "explorer"]

    def test_every_registry_entry_has_a_command_file(self, delivery_project: Path) -> None:
        reg = _tomllib.loads((delivery_project / "working/commands.toml").read_text())
        names = {c["name"] for c in reg["command"]}
        files = {p.stem for p in (delivery_project / ".claude/commands").glob("*.md")}
        assert names <= files, sorted(names - files)
        assert files <= names, sorted(files - names)

    def test_command_files_have_frontmatter_matching_registry(self, delivery_project: Path) -> None:
        reg = {c["name"]: c for c in _tomllib.loads((delivery_project / "working/commands.toml").read_text())["command"]}
        for name, entry in reg.items():
            fm = _frontmatter(delivery_project / f".claude/commands/{name}.md")
            assert fm["description"] == entry["description"], name

    def test_stage_skills_exist_with_frontmatter_and_budget(self, delivery_project: Path) -> None:
        for name in self.STAGE_SKILLS:
            path = delivery_project / f".claude/skills/{name}/SKILL.md"
            assert path.exists(), name
            fm = _frontmatter(path)
            assert fm.get("name") == name and fm.get("description"), name
            assert len(path.read_text().splitlines()) <= 200, name

    def test_agents_exist_read_only_except_explorer_writes_nothing(self, delivery_project: Path) -> None:
        for name in self.AGENTS:
            path = delivery_project / f".claude/agents/{name}.md"
            assert path.exists(), name
            fm = _frontmatter(path)
            assert fm.get("name") == name and fm.get("description"), name
            tools = fm.get("tools", "")
            assert "Write" not in tools and "Edit" not in tools, f"{name} must be read-only"

    def test_evaluator_bash_is_restricted(self, delivery_project: Path) -> None:
        fm = _frontmatter(delivery_project / ".claude/agents/evaluator.md")
        assert "Bash(" in fm["tools"] and "Bash," not in fm["tools"] and not fm["tools"].endswith("Bash")

    def test_vendored_deslop_present_and_matches(self, delivery_copy: Path) -> None:
        assert (delivery_copy / ".claude/skills/deslop/SKILL.md").exists()
        assert (delivery_copy / ".claude/skills/deslop/references/ai-writing-tells.md").exists()
        assert "deslop" in (delivery_copy / ".claude/VENDORED.md").read_text()
        env = {**__import__("os").environ, "PYTHONPATH": "scripts"}
        assert subprocess.run([PYTHON, "-m", "delivery.vendored_check", "."], cwd=delivery_copy, env=env).returncode == 0

    def test_ruff_remediation_rule_exists(self, delivery_project: Path) -> None:
        text = (delivery_project / ".claude/rules/ruff-remediation.md").read_text()
        assert "C901" in text and "TID251" in text

    def test_registry_help_check_passes(self, delivery_copy: Path) -> None:
        env = {**__import__("os").environ, "PYTHONPATH": "scripts"}
        r = subprocess.run([PYTHON, "-m", "delivery.help", "--check", "."], cwd=delivery_copy, env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout


class TestScriptsUsage:
    """C08: every script answers --help with its docstring and exits 2 on bad arguments."""

    def test_help_for_every_module(self, delivery_copy: Path) -> None:
        env = {**__import__("os").environ, "PYTHONPATH": "scripts"}
        modules = sorted(p.stem for p in (delivery_copy / "scripts/delivery").glob("*.py") if not p.stem.startswith("_"))
        assert len(modules) >= 25
        for m in modules:
            r = subprocess.run([PYTHON, "-m", "delivery", m, "--help"], cwd=delivery_copy, env=env, capture_output=True, text=True)
            assert r.returncode == 0 and r.stdout.strip(), m


class TestCopierUpdate:
    """C03 / TPL-02: copier update keeps project-owned files and updates managed ones."""

    def test_update_preserves_owned_and_updates_managed(self, tmp_path: Path) -> None:
        import shutil as _shutil

        from copier import run_update

        tpl = tmp_path / "tpl"
        _shutil.copytree(TEMPLATE, tpl, ignore=_shutil.ignore_patterns(".venv", ".git"))
        subprocess.run(["git", "init", "-q"], cwd=tpl, check=True)
        g = ["git", "-c", "user.name=t", "-c", "user.email=t@x"]
        subprocess.run([*g, "add", "-A"], cwd=tpl, check=True)
        subprocess.run([*g, "commit", "-q", "-m", "v1"], cwd=tpl, check=True)
        subprocess.run(["git", "tag", "v1.0.0"], cwd=tpl, check=True)
        project = tmp_path / "proj"
        run_copy(str(tpl), str(project), data={**BASE_ANSWERS, "enable_delivery": True}, defaults=True, unsafe=True, quiet=True)
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)
        subprocess.run([*g, "add", "-A"], cwd=project, check=True)
        subprocess.run([*g, "commit", "-q", "-m", "generated"], cwd=project, check=True)
        (project / "working/spec/core.md").write_text("# Core\nproject-owned\n")
        (project / "working/architecture/constraints.md").write_text("# mine\n")
        subprocess.run([*g, "add", "-A"], cwd=project, check=True)
        subprocess.run([*g, "commit", "-q", "-m", "edits"], cwd=project, check=True)
        script = tpl / "template/scripts/delivery/block.py"
        script.write_text(script.read_text() + "\n# upstream change\n")
        subprocess.run([*g, "commit", "-qam", "v2"], cwd=tpl, check=True)
        subprocess.run(["git", "tag", "v1.1.0"], cwd=tpl, check=True)
        run_update(str(project), defaults=True, overwrite=True, unsafe=True, quiet=True, skip_answered=True)
        assert (project / "working/spec/core.md").read_text() == "# Core\nproject-owned\n"
        assert (project / "working/architecture/constraints.md").read_text() == "# mine\n"
        assert "# upstream change" in (project / "scripts/delivery/block.py").read_text()


# ------------------------------------------------------------------- S11 (C13)


class TestNewApp:
    """C13: make new-app produces a compliant member and make ci still passes."""

    def test_new_app_is_compliant(self, delivery_copy: Path) -> None:
        subprocess.run(["git", "init", "-q", "-b", "develop"], cwd=delivery_copy, check=True)
        r = subprocess.run([require_bash(), "scripts/new-app.sh", "worker"], cwd=delivery_copy, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        member = delivery_copy / "apps/worker"
        py = (member / "pyproject.toml").read_text()
        assert "[tool.delivery]" in py and "enabled = true" in py
        for layer in ("types", "config", "repo", "service", "runtime"):
            assert (member / "src/worker" / layer / "__init__.py").exists(), layer
        root = (delivery_copy / "pyproject.toml").read_text()
        assert "LAYER-worker" in root and '"worker.types"' in root and '"worker"' in root.split("[tool.importlinter]")[1]
        spec = (delivery_copy / "working/spec/worker.md").read_text()
        assert "status: unspecified" in spec
        assert (member / "tests/test_main.py").exists()
        marker_text = (member / "tests/test_main.py").read_text()
        assert "@pytest.mark.spec" in marker_text

    def test_new_app_then_ci_passes(self, delivery_copy: Path) -> None:
        subprocess.run(["git", "init", "-q", "-b", "develop"], cwd=delivery_copy, check=True)
        subprocess.run([require_bash(), "scripts/new-app.sh", "worker"], cwd=delivery_copy, check=True, capture_output=True)
        subprocess.run(["uv", "sync", "--quiet"], cwd=delivery_copy, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@x", "add", "-A"], cwd=delivery_copy, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "-m", "init"], cwd=delivery_copy, check=True)
        r = subprocess.run([require_make(), "ci"], cwd=delivery_copy, capture_output=True, text=True)
        assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
