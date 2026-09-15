"""Red tests for plan step S4: test_ratchet (C22), ordering (C23), diff_coverage (C24).

Interfaces fixed here:
- test_ratchet.main(["--base", <ref>, "--labels", "a,b", repo]) and ["--quality", repo]
  output `path:line: RATCHET-xx ...` / `path:line: TQ-0x ...`
- ordering.main(["--item", id, "--base", ref, repo]); .work/<id>/tests.json maps
  criterion id -> [{"test": "path::test_name", "commit": sha}]; defects: diagnosis.md `location: file:function`
- diff_coverage.main(["--base", ref, "--coverage-json", path, repo]); budget coverage.diff.min
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from delivery import diff_coverage, ordering, test_ratchet


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def commit_all(repo: Path, msg: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD").strip()


@pytest.fixture
def member(repo: Path) -> Path:
    """repo with an enabled member libs/core containing one module and one test file."""
    (repo / "libs/core/src/core").mkdir(parents=True)
    (repo / "libs/core/tests").mkdir(parents=True)
    (repo / "libs/core/pyproject.toml").write_text('[project]\nname="core"\n[tool.delivery]\nenabled = true\n')
    (repo / "libs/core/src/core/__init__.py").write_text("")
    (repo / "libs/core/src/core/calc.py").write_text("def add(a: int, b: int) -> int:\n    return a + b\n")
    (repo / "libs/core/tests/test_calc.py").write_text(
        "import pytest\nfrom core.calc import add\n\n"
        '@pytest.mark.spec("core.md#add")\ndef test_add():\n    assert add(1, 2) == 3\n    assert add(0, 0) == 0\n'
    )
    (repo / "working/standards").mkdir(parents=True)
    (repo / "working/standards/budgets.md").write_text("coverage.diff.min: 0.90\n")
    commit_all(repo, "feat: baseline")
    git(repo, "branch", "base")
    return repo


# ------------------------------------------------------------ test_ratchet (C22)


class TestRatchet:
    def test_deleted_assertion_fails(self, member: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (member / "libs/core/tests/test_calc.py").write_text(
            "import pytest\nfrom core.calc import add\n\n"
            '@pytest.mark.spec("core.md#add")\ndef test_add():\n    assert add(1, 2) == 3\n'
        )
        commit_all(member, "test: drop one")
        assert test_ratchet.main(["--base", "base", member.as_posix()]) == 1
        assert "RATCHET-01" in capsys.readouterr().out

    def test_weakened_comparison_fails(self, member: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (member / "libs/core/tests/test_calc.py").write_text(
            "import pytest\nfrom core.calc import add\n\n"
            '@pytest.mark.spec("core.md#add")\ndef test_add():\n    assert add(1, 2) in (3, 4)\n    assert add(0, 0) == 0\n'
        )
        commit_all(member, "test: weaken")
        assert test_ratchet.main(["--base", "base", member.as_posix()]) == 1
        assert "RATCHET-02" in capsys.readouterr().out

    def test_deleting_last_test_for_anchor_names_the_anchor(self, member: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (member / "libs/core/tests/test_calc.py").write_text("import pytest\n")
        commit_all(member, "test: delete")
        assert test_ratchet.main(["--base", "base", member.as_posix()]) == 1
        out = capsys.readouterr().out
        assert "RATCHET-03" in out and "core.md#add" in out

    def test_rename_with_marker_passes(self, member: Path) -> None:
        (member / "libs/core/tests/test_calc.py").write_text(
            "import pytest\nfrom core.calc import add\n\n"
            '@pytest.mark.spec("core.md#add")\ndef test_addition_basics():\n    assert add(1, 2) == 3\n    assert add(0, 0) == 0\n'
        )
        commit_all(member, "test: rename")
        assert test_ratchet.main(["--base", "base", member.as_posix()]) == 0

    def test_split_across_two_functions_passes(self, member: Path) -> None:
        (member / "libs/core/tests/test_calc.py").write_text(
            "import pytest\nfrom core.calc import add\n\n"
            '@pytest.mark.spec("core.md#add")\ndef test_add_positive():\n    assert add(1, 2) == 3\n\n'
            '@pytest.mark.spec("core.md#add")\ndef test_add_zero():\n    assert add(0, 0) == 0\n'
        )
        commit_all(member, "test: split")
        assert test_ratchet.main(["--base", "base", member.as_posix()]) == 0

    def test_moving_assertion_between_anchor_tests_passes(self, member: Path) -> None:
        (member / "libs/core/tests/test_calc.py").write_text(
            "import pytest\nfrom core.calc import add\n\n"
            '@pytest.mark.spec("core.md#add")\ndef test_add():\n    assert add(0, 0) == 0\n\n'
            '@pytest.mark.spec("core.md#add")\ndef test_add_more():\n    assert add(1, 2) == 3\n'
        )
        commit_all(member, "test: move")
        assert test_ratchet.main(["--base", "base", member.as_posix()]) == 0

    def test_skip_marker_fails(self, member: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (member / "libs/core/tests/test_calc.py").write_text(
            "import pytest\nfrom core.calc import add\n\n"
            '@pytest.mark.skip\n@pytest.mark.spec("core.md#add")\ndef test_add():\n    assert add(1, 2) == 3\n    assert add(0, 0) == 0\n'
        )
        commit_all(member, "test: skip")
        assert test_ratchet.main(["--base", "base", member.as_posix()]) == 1
        assert "RATCHET-04" in capsys.readouterr().out

    def test_label_allows_change(self, member: Path) -> None:
        (member / "libs/core/tests/test_calc.py").write_text("import pytest\n")
        commit_all(member, "test: delete")
        assert test_ratchet.main(["--base", "base", "--labels", "test-change-approved", member.as_posix()]) == 0

    def test_added_assertion_passes(self, member: Path) -> None:
        (member / "libs/core/tests/test_calc.py").write_text(
            "import pytest\nfrom core.calc import add\n\n"
            '@pytest.mark.spec("core.md#add")\ndef test_add():\n    assert add(1, 2) == 3\n    assert add(0, 0) == 0\n    assert add(-1, 1) == 0\n'
        )
        commit_all(member, "test: strengthen")
        assert test_ratchet.main(["--base", "base", member.as_posix()]) == 0


class TestQuality:
    def _write(self, member: Path, body: str) -> None:
        (member / "libs/core/tests/test_q.py").write_text(body)

    def test_no_assertion(self, member: Path, capsys: pytest.CaptureFixture[str]) -> None:
        self._write(member, 'import pytest\n@pytest.mark.spec("core.md#x")\ndef test_x():\n    x = 1\n')
        assert test_ratchet.main(["--quality", member.as_posix()]) == 1
        assert "TQ-01" in capsys.readouterr().out

    def test_tautology(self, member: Path, capsys: pytest.CaptureFixture[str]) -> None:
        self._write(member, 'import pytest\n@pytest.mark.spec("core.md#x")\ndef test_x():\n    x = 1\n    assert x == x\n')
        assert test_ratchet.main(["--quality", member.as_posix()]) == 1
        assert "TQ-02" in capsys.readouterr().out

    def test_constant_assertion(self, member: Path, capsys: pytest.CaptureFixture[str]) -> None:
        self._write(member, 'import pytest\n@pytest.mark.spec("core.md#x")\ndef test_x():\n    assert True\n')
        assert test_ratchet.main(["--quality", member.as_posix()]) == 1
        assert "TQ-02" in capsys.readouterr().out

    def test_mocking_module_under_test(self, member: Path, capsys: pytest.CaptureFixture[str]) -> None:
        self._write(member, (
            'import pytest\nfrom unittest.mock import patch\n@pytest.mark.spec("core.md#x")\n'
            'def test_x():\n    with patch("core.calc.add", return_value=3):\n        assert 3 == 3\n'
        ))
        assert test_ratchet.main(["--quality", member.as_posix()]) == 1
        assert "TQ-03" in capsys.readouterr().out

    def test_missing_marker_in_enabled_member(self, member: Path, capsys: pytest.CaptureFixture[str]) -> None:
        self._write(member, "def test_x():\n    assert 1 + 1 == 2\n")
        assert test_ratchet.main(["--quality", member.as_posix()]) == 1
        out = capsys.readouterr().out
        assert "TQ-04" in out and "pytest.mark.spec" in out and "criterion" not in out

    def test_compliant_passes(self, member: Path) -> None:
        self._write(member, (
            'import pytest\nfrom core.calc import add\n@pytest.mark.spec("core.md#x")\n'
            "def test_x():\n    assert add(2, 2) == 4\n"
        ))
        assert test_ratchet.main(["--quality", member.as_posix()]) == 0


# ---------------------------------------------------------------- ordering (C23)


def _item(repo: Path, tests: list[str], change_type: str = "new-behavior") -> None:
    (repo / ".work/t1").mkdir(parents=True, exist_ok=True)
    (repo / ".work/t1/criteria.json").write_text(json.dumps({
        "id": "t1", "change_type": change_type,
        "criteria": [{"id": "C1", "class": "positive", "statement": "s", "verify": "x",
                      "status": "fail", "evidence": None, "evaluator": None, "plan_steps": []}],
    }))
    (repo / ".work/t1/tests.json").write_text(json.dumps({"C1": [{"test": t, "commit": ""} for t in tests]}))


class TestOrdering:
    def _red_then_green(self, member: Path) -> None:
        (member / "libs/core/tests/test_mul.py").write_text(
            'import pytest\nfrom core.calc import mul\n@pytest.mark.spec("core.md#x")\ndef test_mul():\n    assert mul(2, 3) == 6\n'
        )
        commit_all(member, "test(t1): red C1")
        (member / "libs/core/src/core/calc.py").write_text(
            "def add(a: int, b: int) -> int:\n    return a + b\n\ndef mul(a: int, b: int) -> int:\n    return a * b\n"
        )
        commit_all(member, "feat(t1): mul")

    def test_red_then_green_passes(self, member: Path) -> None:
        self._red_then_green(member)
        _item(member, ["libs/core/tests/test_mul.py::test_mul"])
        commit_all(member, "chore: item")
        assert ordering.main(["--item", "t1", "--base", "base", member.as_posix()]) == 0

    def test_implementation_before_test_fails(self, member: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (member / "libs/core/src/core/calc.py").write_text(
            "def add(a: int, b: int) -> int:\n    return a + b\n\ndef mul(a: int, b: int) -> int:\n    return a * b\n"
        )
        commit_all(member, "feat(t1): mul first")
        (member / "libs/core/tests/test_mul.py").write_text(
            'import pytest\nfrom core.calc import mul\n@pytest.mark.spec("core.md#x")\ndef test_mul():\n    assert mul(2, 3) == 6\n'
        )
        commit_all(member, "test(t1): after")
        _item(member, ["libs/core/tests/test_mul.py::test_mul"])
        commit_all(member, "chore: item")
        assert ordering.main(["--item", "t1", "--base", "base", member.as_posix()]) == 1
        out = capsys.readouterr().out
        assert "ORDER-01" in out and "C1" in out

    def test_test_passing_at_own_commit_is_not_red(self, member: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (member / "libs/core/tests/test_const.py").write_text(
            'import pytest\n@pytest.mark.spec("core.md#x")\ndef test_const():\n    assert 1 == 1\n'
        )
        commit_all(member, "test(t1): not red")
        _item(member, ["libs/core/tests/test_const.py::test_const"])
        commit_all(member, "chore: item")
        assert ordering.main(["--item", "t1", "--base", "base", member.as_posix()]) == 1
        assert "ORDER-02" in capsys.readouterr().out

    def test_defect_location_check(self, member: Path, capsys: pytest.CaptureFixture[str]) -> None:
        self._red_then_green(member)
        _item(member, ["libs/core/tests/test_mul.py::test_mul"], change_type="defect")
        (member / ".work/t1/diagnosis.md").write_text("location: libs/core/src/core/other.py:render\n")
        commit_all(member, "chore: item")
        assert ordering.main(["--item", "t1", "--base", "base", member.as_posix()]) == 1
        assert "ORDER-03" in capsys.readouterr().out
        (member / ".work/t1/diagnosis.md").write_text("location: libs/core/src/core/calc.py:mul\n")
        commit_all(member, "chore: fix location")
        assert ordering.main(["--item", "t1", "--base", "base", member.as_posix()]) == 0


# ----------------------------------------------------------- diff_coverage (C24)


class TestDiffCoverage:
    def _change_and_coverage(self, member: Path, covered: list[int]) -> Path:
        (member / "libs/core/src/core/calc.py").write_text(
            "def add(a: int, b: int) -> int:\n    return a + b\n\n\n"
            "def mul(a: int, b: int) -> int:\n    if a == 0:\n        return 0\n    return a * b\n"
        )
        commit_all(member, "feat: mul")
        cov = member / "coverage.json"
        cov.write_text(json.dumps({"files": {"libs/core/src/core/calc.py": {"executed_lines": covered, "missing_lines": []}}}))
        return cov

    def test_below_budget_fails_naming_lines(self, member: Path, capsys: pytest.CaptureFixture[str]) -> None:
        cov = self._change_and_coverage(member, covered=[5, 6, 8])  # line 7 uncovered of 4 changed
        assert diff_coverage.main(["--base", "base", "--coverage-json", cov.as_posix(), member.as_posix()]) == 1
        out = capsys.readouterr().out
        assert "calc.py:7" in out and "COVERAGE" in out

    def test_at_budget_passes(self, member: Path) -> None:
        cov = self._change_and_coverage(member, covered=[5, 6, 7, 8])
        assert diff_coverage.main(["--base", "base", "--coverage-json", cov.as_posix(), member.as_posix()]) == 0

    def test_no_changed_lines_passes(self, member: Path) -> None:
        (member / "README.md").write_text("changed\n")
        commit_all(member, "docs")
        cov = member / "coverage.json"
        cov.write_text(json.dumps({"files": {}}))
        assert diff_coverage.main(["--base", "base", "--coverage-json", cov.as_posix(), member.as_posix()]) == 0
