"""Red tests for plan step S3: constraints, budgets, spec_coverage, spec_check, deploy_surface.

Interfaces fixed here:
- every module: main(argv: list[str]) -> int; 0 pass, 1 violations, 2 environment
- check output: one `path:line: RULE-ID message` line per violation on stdout
- constraints.RULES: dict[rule_id, Rule class]; baseline in working/architecture/constraints-baseline.txt
- budgets: reads working/standards/budgets.md; --constraints, --agents-md sub-checks
- spec_coverage: anchors `file.md#heading-slug` in working/spec/**, markers @pytest.mark.spec("...")
- spec_check: --item <id>; required classes per change_type from working/standards/criteria-templates.md
- deploy_surface: static Dockerfile check; --image runs the container check when docker exists
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from delivery import budgets, constraints, deploy_surface, spec_check, spec_coverage

BUDGETS = """# Budgets
file.max_lines: 5
agents_md.max_lines: 3
area_doc.max_lines: 4
spec_domain.max_lines: 4
comment_density.max: 0.5
coverage.diff.min: 0.90
"""

CONSTRAINTS = """# Constraints
## Invariants
- INV-01 (check: constraints.py INV-01) [allow: core.logging_setup]: environment is read only in the allowed modules
- INV-02 (check: ruff T20): no print() in library code
- LAYER-01 (check: importlinter LAYER-01): layers depend forward only
## Protected paths
- working/architecture/**
"""

CRITERIA_TEMPLATES = """# Criteria templates
| change type | required classes |
|---|---|
| new-behavior | positive, negative, failure, boundary |
| changed-behavior | positive, negative, failure, boundary, regression |
| defect | reproduction, regression, location |
| trivial | |
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A minimal project layout the checks can read."""
    (tmp_path / "working/standards").mkdir(parents=True)
    (tmp_path / "working/architecture").mkdir(parents=True)
    (tmp_path / "working/spec").mkdir(parents=True)
    (tmp_path / "libs/core/src/core").mkdir(parents=True)
    (tmp_path / "libs/core/tests").mkdir(parents=True)
    (tmp_path / "working/standards/budgets.md").write_text(BUDGETS)
    (tmp_path / "working/standards/criteria-templates.md").write_text(CRITERIA_TEMPLATES)
    (tmp_path / "working/architecture/constraints.md").write_text(CONSTRAINTS)
    (tmp_path / "AGENTS.md").write_text("a\nb\n")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.ruff.lint]\nselect = ["T20"]\n'
        '[[tool.importlinter.contracts]]\nname = "LAYER-01: layers"\ntype = "layers"\n'
    )
    return tmp_path


# --------------------------------------------------------------- constraints (C19)


class TestConstraints:
    def test_output_format_and_exit(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (project / "libs/core/src/core/x.py").write_text("import os\n\ndef f():\n    return os.getenv('DB_URL')\n")
        code = constraints.main([str(project)])
        out = capsys.readouterr().out.splitlines()
        assert code == 1
        assert out == [
            "libs/core/src/core/x.py:4: INV-01 environment read outside the allowed modules; "
            "read settings from shared.config or add the module to INV-01's [allow: ...] list in "
            "constraints.md. Example: libs/shared/src/shared/config.py:1"
        ]

    def test_clean_tree_passes(self, project: Path) -> None:
        (project / "libs/core/src/core/x.py").write_text("def f() -> int:\n    return 1\n")
        assert constraints.main([str(project)]) == 0

    def test_grandfathered_passes_new_fails(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (project / "libs/core/src/core/old.py").write_text("import os\nX = os.environ['LEGACY']\n")
        (project / "working/architecture/constraints-baseline.txt").write_text(
            "libs/core/src/core/old.py:INV-01\n"
        )
        assert constraints.main([str(project)]) == 0
        (project / "libs/core/src/core/new.py").write_text("import os\nY = os.environ.get('NEW')\n")
        assert constraints.main([str(project)]) == 1
        out = capsys.readouterr().out
        assert "new.py" in out and "old.py" not in out

    def test_baseline_regeneration(self, project: Path) -> None:
        (project / "libs/core/src/core/old.py").write_text("import os\nX = os.environ['LEGACY']\n")
        assert constraints.main(["--write-baseline", str(project)]) == 0
        baseline = (project / "working/architecture/constraints-baseline.txt").read_text()
        assert "libs/core/src/core/old.py:INV-01" in baseline

    def test_allowed_module_may_read_environment(self, project: Path) -> None:
        (project / "libs/core/src/core/logging_setup.py").write_text("import os\nLEVEL = os.getenv('LOG_LEVEL')\n")
        assert constraints.main([str(project)]) == 0

    def test_parameters_are_parsed_from_the_constraint_line(self, project: Path) -> None:
        from delivery import paths as p_

        assert p_.constraint_params(project, "INV-01") == {"allow": ("core.logging_setup",)}

    def test_config_module_may_read_environment(self, project: Path) -> None:
        (project / "libs/core/src/core/config.py").write_text("import os\nDB = os.getenv('DB_URL')\n")
        assert constraints.main([str(project)]) == 0

    def test_unlisted_rule_does_not_run(self, project: Path) -> None:
        (project / "working/architecture/constraints.md").write_text("# Constraints\n")
        (project / "libs/core/src/core/x.py").write_text("import os\nY = os.getenv('X')\n")
        assert constraints.main([str(project)]) == 0

    def test_every_registered_rule_has_id_anchor_and_message(self) -> None:
        for rule_id, rule in constraints.RULES.items():
            assert rule.id == rule_id
            assert rule.anchor.startswith("working/architecture/constraints.md#")
            assert "Example:" in rule.message


# ------------------------------------------------------------------- budgets (C20)


class TestBudgets:
    def test_over_budget_file_fails(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (project / "libs/core/src/core/big.py").write_text("x = 1\n" * 6)
        assert budgets.main([str(project)]) == 1
        assert "big.py:1: BUDGET file.max_lines 6 > 5" in capsys.readouterr().out

    def test_agents_md_over_budget_fails(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (project / "AGENTS.md").write_text("a\nb\nc\nd\n")
        assert budgets.main(["--agents-md", str(project)]) == 1
        assert "AGENTS.md:1: BUDGET agents_md.max_lines 4 > 3" in capsys.readouterr().out

    def test_agents_md_duplicating_ruff_rule_fails(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (project / "AGENTS.md").write_text("Never use print statements.\n")
        assert budgets.main(["--agents-md", str(project)]) == 1
        assert "DUPLICATES-RUFF T20" in capsys.readouterr().out

    def test_orphan_constraint_fails(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (project / "working/architecture/constraints.md").write_text(
            CONSTRAINTS + "- INV-09 (check: constraints.py INV-09): orphan\n"
        )
        assert budgets.main(["--constraints", str(project)]) == 1
        assert "ORPHAN-CONSTRAINT INV-09" in capsys.readouterr().out

    def test_constraints_all_backed_passes(self, project: Path) -> None:
        assert budgets.main(["--constraints", str(project)]) == 0

    def test_spec_domain_budget(self, project: Path) -> None:
        (project / "working/spec/core.md").write_text("# a\n" * 5)
        assert budgets.main([str(project)]) == 1


# ------------------------------------------------------------- spec_coverage (C21)


class TestSpecCoverage:
    def test_anchor_without_test_fails(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (project / "working/spec/core.md").write_text("# Core\n\n## Refund window\nRefunds close after 30 days.\n")
        assert spec_coverage.main([str(project)]) == 1
        assert "core.md#refund-window" in capsys.readouterr().out

    def test_marked_test_covers_anchor(self, project: Path) -> None:
        (project / "working/spec/core.md").write_text("# Core\n\n## Refund window\ntext\n")
        (project / "libs/core/tests/test_refund.py").write_text(
            'import pytest\n\n@pytest.mark.spec("core.md#refund-window")\ndef test_x(): ...\n'
        )
        assert spec_coverage.main([str(project)]) == 0

    def test_unspecified_member_is_reported_not_failed(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (project / "working/spec/core.md").write_text("# Core\nstatus: unspecified\n")
        assert spec_coverage.main([str(project)]) == 0
        assert "unspecified" in capsys.readouterr().out


# ---------------------------------------------------------------- spec_check (C39)


class TestSpecCheck:
    def _criteria(self, project: Path, change_type: str, classes: list[str]) -> None:
        d = project / ".work/t1"
        d.mkdir(parents=True)
        (d / "criteria.json").write_text(json.dumps({
            "id": "t1", "change_type": change_type,
            "criteria": [
                {"id": f"C{i}", "class": c, "statement": "s", "verify": "true",
                 "status": "fail", "evidence": None, "evaluator": None, "plan_steps": []}
                for i, c in enumerate(classes)
            ],
        }))

    def test_missing_class_fails_naming_it(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        self._criteria(project, "new-behavior", ["positive", "failure", "boundary"])
        assert spec_check.main(["--item", "t1", str(project)]) == 1
        err = capsys.readouterr().err
        assert "negative" in err and "new-behavior" in err and "BLOCKED" in err

    def test_complete_passes(self, project: Path) -> None:
        self._criteria(project, "new-behavior", ["positive", "negative", "failure", "boundary"])
        assert spec_check.main(["--item", "t1", str(project)]) == 0

    def test_pass_without_evidence_fails(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        self._criteria(project, "trivial", ["positive"])
        p = project / ".work/t1/criteria.json"
        data = json.loads(p.read_text())
        data["criteria"][0]["status"] = "pass"
        p.write_text(json.dumps(data))
        assert spec_check.main(["--item", "t1", str(project)]) == 1
        assert "C0" in capsys.readouterr().err

    def test_missing_verify_command_fails(self, project: Path) -> None:
        self._criteria(project, "trivial", ["positive"])
        p = project / ".work/t1/criteria.json"
        data = json.loads(p.read_text())
        data["criteria"][0]["verify"] = ""
        p.write_text(json.dumps(data))
        assert spec_check.main(["--item", "t1", str(project)]) == 1


# ----------------------------------------------------------- deploy_surface (C38, TPL-06)


class TestDeploySurface:
    def _dockerfile(self, project: Path, body: str) -> None:
        (project / "apps/svc").mkdir(parents=True)
        (project / "apps/svc/Dockerfile").write_text(body)
        (project / ".dockerignore").write_text(".claude/\n.work/\nworking/\ndocs/\nscripts/\n.github/\n**/tests/\n*.md\n")

    GOOD = "FROM python\nCOPY pyproject.toml uv.lock ./\nCOPY libs/ libs/\nCOPY apps/svc/ apps/svc/\n"

    def test_explicit_copy_list_passes(self, project: Path) -> None:
        self._dockerfile(project, self.GOOD)
        assert deploy_surface.main([str(project)]) == 0

    def test_copy_dot_fails_naming_line(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        self._dockerfile(project, "FROM python\nCOPY . .\n")
        assert deploy_surface.main([str(project)]) == 1
        assert "apps/svc/Dockerfile:2: DEPLOY-01" in capsys.readouterr().out

    STAGE_PREFIX = (
        "FROM python AS builder\n"
        "COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv\n"
    )

    def test_stage_copies_are_not_repository_sources(self, project: Path) -> None:
        """COPY --from=<stage|image> reads from another build stage, not the repo.

        The template's own app-template/Dockerfile copies /uv from the uv image and
        /build from the builder stage; both were reported as DEPLOY-01 violations,
        so every generated project failed `make deploy-surface` on its first CI run.
        """
        body = self.STAGE_PREFIX + self.GOOD.split("\n", 1)[1]
        body += "COPY --from=builder --chown=app:app /build /app\n"
        self._dockerfile(project, body)
        assert deploy_surface.main([str(project)]) == 0

    def test_stage_copy_does_not_mask_a_real_violation(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        body = self.STAGE_PREFIX + "COPY working/ /app/working/\n"
        self._dockerfile(project, body)
        assert deploy_surface.main([str(project)]) == 1
        assert "DEPLOY-01" in capsys.readouterr().out

    def test_missing_dockerignore_entry_fails(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        self._dockerfile(project, self.GOOD)
        (project / ".dockerignore").write_text(".claude/\n")
        assert deploy_surface.main([str(project)]) == 1
        out = capsys.readouterr().out
        assert "DEPLOY-02" in out
        assert "working/" in out

    def test_no_docker_skips_image_check_explicitly(self, project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        self._dockerfile(project, self.GOOD)
        monkeypatch.setattr(deploy_surface, "docker_available", lambda: False)
        assert deploy_surface.main(["--image", "svc:test", str(project)]) == 0
        assert "image check skipped: docker not available" in capsys.readouterr().out

    def test_image_with_excluded_path_fails(self, project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        self._dockerfile(project, self.GOOD)
        monkeypatch.setattr(deploy_surface, "docker_available", lambda: True)
        monkeypatch.setattr(deploy_surface, "image_files", lambda _name: ["app/main.py", "app/.claude/settings.json"])
        assert deploy_surface.main(["--image", "svc:test", str(project)]) == 1
        assert "DEPLOY-03" in capsys.readouterr().out

