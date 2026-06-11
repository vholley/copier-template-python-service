"""Tests for copier template generation.

Each test generates a project into pytest's tmp_path and asserts on the
resulting file tree. Tests are grouped by what they verify:
- Exclusions: files/dirs that must be absent for a given flag combination
- Inclusions: files/dirs that must be present for a given flag combination
- Rendering: template variables correctly substituted in generated content
"""

from pathlib import Path
from typing import Any

from copier import run_copy

TEMPLATE = str(Path(__file__).parent.parent)

_GCP_EXTRAS: dict[str, Any] = {
    "use_gcp": True,
    "include_docker": True,
    "gcp_project_dev": "my-project-dev",
    "gcp_project_prod": "my-project-prod",
}


def _generate(dest: Path, **overrides: Any) -> Path:
    data: dict[str, Any] = {
        "project_name": "test-project",
        "python_version": "3.14",
        "app_framework": "minimal",
        "use_gcp": False,
        "include_docker": False,
    }
    data.update(overrides)
    run_copy(
        TEMPLATE,
        str(dest),
        data=data,
        defaults=True,
        overwrite=True,
        unsafe=True,
        quiet=True,
        # Test the working tree's HEAD, not the latest release tag (which
        # is what copier uses by default for a git template).
        vcs_ref="HEAD",
    )
    return dest


class TestExclusions:
    def test_no_gcp_excludes_gcp_module(self, tmp_path: Path) -> None:
        project = _generate(tmp_path)
        assert not (project / "libs/shared/src/shared/gcp.py").exists()

    def test_no_gcp_excludes_deploy_workflow(self, tmp_path: Path) -> None:
        project = _generate(tmp_path)
        assert not (project / ".github/workflows/deploy.yml").exists()

    def test_no_gcp_excludes_deploy_script(self, tmp_path: Path) -> None:
        project = _generate(tmp_path)
        assert not (project / "scripts/deploy.sh").exists()

    def test_no_gcp_excludes_infra(self, tmp_path: Path) -> None:
        project = _generate(tmp_path)
        assert not (project / "infra").exists()

    def test_no_docker_excludes_dockerfile(self, tmp_path: Path) -> None:
        project = _generate(tmp_path)
        assert not any(project.rglob("Dockerfile"))

    def test_no_terraform_excludes_terraform_dir(self, tmp_path: Path) -> None:
        project = _generate(tmp_path, **_GCP_EXTRAS, include_terraform=False)
        assert not (project / "infra/terraform").exists()

    def test_no_terraform_excludes_terraform_workflows(self, tmp_path: Path) -> None:
        project = _generate(tmp_path, **_GCP_EXTRAS, include_terraform=False)
        assert not (project / ".github/workflows/terraform-plan.yml").exists()
        assert not (project / ".github/workflows/terraform-apply.yml").exists()

    def test_no_gcp_with_terraform_excludes_terraform_workflows(self, tmp_path: Path) -> None:
        project = _generate(tmp_path, include_terraform=True)
        assert not (project / ".github/workflows/terraform-plan.yml").exists()
        assert not (project / ".github/workflows/terraform-apply.yml").exists()


class TestInclusions:
    def test_ci_workflow_always_present(self, tmp_path: Path) -> None:
        project = _generate(tmp_path)
        assert (project / ".github/workflows/ci.yml").exists()

    def test_gcp_includes_gcp_module(self, tmp_path: Path) -> None:
        project = _generate(tmp_path, **_GCP_EXTRAS)
        assert (project / "libs/shared/src/shared/gcp.py").exists()

    def test_gcp_includes_deploy_workflow(self, tmp_path: Path) -> None:
        project = _generate(tmp_path, **_GCP_EXTRAS)
        assert (project / ".github/workflows/deploy.yml").exists()

    def test_gcp_includes_deploy_script(self, tmp_path: Path) -> None:
        project = _generate(tmp_path, **_GCP_EXTRAS)
        assert (project / "scripts/deploy.sh").exists()

    def test_docker_includes_dockerfile(self, tmp_path: Path) -> None:
        project = _generate(tmp_path, include_docker=True)
        assert any(project.rglob("Dockerfile"))

    def test_terraform_includes_infra_dir(self, tmp_path: Path) -> None:
        project = _generate(tmp_path, **_GCP_EXTRAS, include_terraform=True)
        assert (project / "infra/terraform").exists()

    def test_terraform_includes_workflows(self, tmp_path: Path) -> None:
        project = _generate(tmp_path, **_GCP_EXTRAS, include_terraform=True)
        assert (project / ".github/workflows/terraform-plan.yml").exists()
        assert (project / ".github/workflows/terraform-apply.yml").exists()

    def test_no_gcp_with_terraform_includes_infra_dir(self, tmp_path: Path) -> None:
        project = _generate(tmp_path, include_terraform=True)
        assert (project / "infra/terraform").exists()


class TestRendering:
    def test_project_name_in_readme(self, tmp_path: Path) -> None:
        project = _generate(tmp_path)
        assert "test-project" in (project / "README.md").read_text()

    def test_python_version_in_dotfile(self, tmp_path: Path) -> None:
        project = _generate(tmp_path, python_version="3.13")
        assert "3.13" in (project / ".python-version").read_text()

    def test_gcp_project_ids_rendered(self, tmp_path: Path) -> None:
        project = _generate(tmp_path, **_GCP_EXTRAS)
        readme = (project / "README.md").read_text()
        assert "my-project-dev" in readme
