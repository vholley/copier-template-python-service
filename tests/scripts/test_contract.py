"""Red tests for plan step S5: signers (C37), pr_contract (C25), compute_tier (C26).

Interfaces fixed here:
- signers.load(source) -> dict[email, [public keys]]; source "file:<path>" or "github:<org>";
  raises signers.FetchError on any failure (the caller fails closed).
- pr_contract.main(["--item", ID | "--no-item", "--base", REF, "--signers", "file:PATH",
                    "--description", FILE, "--labels", "a,b", repo]); prints one
  `CONTRACT-nn ...` line per failed condition; exit 0/1/2.
- compute_tier.main(["--base", REF, repo]) prints `tier: trivial|standard|high` and,
  for a standard change with no item, the bounce block on stderr; exit 0 always
  unless usage.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from delivery import compute_tier, pr_contract, signers, state


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def commit(repo: Path, msg: str, *, sign: bool = True) -> str:
    git(repo, "add", "-A")
    args = ["commit", "-q", "-m", msg] + (["-S"] if sign else [])
    git(repo, *args)
    return git(repo, "rev-parse", "HEAD").strip()


@pytest.fixture
def signed_repo(repo: Path, tmp_path: Path) -> Path:
    """repo with an SSH signing key configured and an allowed-signers file at repo/.signers."""
    key = tmp_path / "key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", "t@example.invalid"], check=True)
    git(repo, "config", "gpg.format", "ssh")
    git(repo, "config", "user.signingkey", str(key) + ".pub")
    (repo / ".signers").write_text(f"t@example.invalid {(key.with_suffix('.pub')).read_text().strip()}\n")
    (repo / "working/standards").mkdir(parents=True)
    (repo / "working/standards/budgets.md").write_text(
        "diff.trivial.max_lines: 50\ndiff.standard.max_lines: 400\ndiff.high.max_lines: 250\n"
        "diff.string_only.max_lines: 10\ncoverage.diff.min: 0.90\n"
        'high_risk_paths:\n  - "**/auth/**"\ntrivial_paths:\n  - "docs/**"\n  - "*.md"\n  - "**/tests/**"\n'
    )
    (repo / "working/standards/criteria-templates.md").write_text(
        "| change type | required classes |\n|---|---|\n| new-behavior | positive, negative |\n| trivial | |\n"
    )
    (repo / "working/spec").mkdir()
    (repo / "working/spec/core.md").write_text("# Core\n\n## Add\nadd returns the sum.\n")
    (repo / "working/architecture").mkdir()
    (repo / "working/architecture/constraints.md").write_text("# Constraints\n## Protected paths\n- working/**\n")
    (repo / "working/architecture/decisions").mkdir()
    (repo / "libs/core/src/core").mkdir(parents=True)
    (repo / "libs/core/tests").mkdir()
    (repo / "libs/core/pyproject.toml").write_text('[project]\nname="core"\n[tool.delivery]\nenabled = true\n')
    (repo / "libs/core/src/core/__init__.py").write_text("")
    (repo / "libs/core/src/core/calc.py").write_text("def add(a: int, b: int) -> int:\n    return a + b\n")
    (repo / ".gitignore").write_text(".signers\n")
    commit(repo, "chore: baseline", sign=False)
    git(repo, "branch", "base")
    return repo


PR_DESC = """## Intent
Adds mul. See intent.md.

## Risk
tier: standard; verified by C1.

## What changed, by criterion
- C1 mul returns the product: libs/core/src/core/calc.py

## Decisions
- D1 no new dependency; accepted by t

## Promotions
- none

## Evidence
- Evaluator report: link
- Traces: run-1
"""


def build_standard_item(repo: Path, *, item: str = "PROJ-1", code_first: bool = False) -> dict[str, str]:
    """A complete, correct Standard change on branch <item>. Returns acceptance shas.

    code_first=True commits the implementation before the red tests (an ordering violation).
    """
    git(repo, "checkout", "-q", "-b", item)
    state.create(repo, item, "change", item)
    d = repo / ".work" / item
    (d / "intent.md").write_text("# Intent\n## Non-goals\n- none\n")
    (d / "clarify.md").write_text("# Clarify\n## Assumptions\n- A1: x\n  risk: low\n  provenance: inferred\n  reviewed [human]: yes\n  tag: local\n")
    (d / "decisions.md").write_text(
        "# Decisions\n## D1: no new dependency\nalternative-rejected: numpy\nramification-if-wrong: slower\n"
        "scope: local\naccepted-by [human]: t\n"
    )
    shas: dict[str, str] = {}
    h = state.file_hash(d / "intent.md")
    shas["intent"] = commit(repo, f"accept(work-{item}): intent\n\nAccepts intent.\n\nAccept: intent sha256={h}\nWork-Item: {item}\n")
    (d / "spec.md").write_text("# Spec\n- S1 mul returns the product (working/spec/core.md#mul)\n")
    (d / "criteria.json").write_text(json.dumps({
        "id": item, "change_type": "new-behavior",
        "criteria": [
            {"id": "C1", "class": "positive", "statement": "mul returns the product", "verify": "pytest",
             "status": "fail", "evidence": None, "evaluator": None, "plan_steps": ["S1"],
             "tests": ["libs/core/tests/test_mul.py::test_mul"]},
            {"id": "C2", "class": "negative", "statement": "mul rejects non-int", "verify": "pytest",
             "status": "fail", "evidence": None, "evaluator": None, "plan_steps": ["S1"],
             "tests": ["libs/core/tests/test_mul.py::test_mul_rejects"]},
        ],
    }, indent=2))
    hs = state.file_hash(d / "spec.md"); hc = state.file_hash(d / "criteria.json"); hd = state.file_hash(d / "decisions.md")
    shas["spec"] = commit(repo, f"accept(work-{item}): spec\n\nAccepts spec.\n\nAccept: spec sha256={hs} sha256={hc}\nAccept-Decision: D1 sha256={hd}\nWork-Item: {item}\n")

    impl = (
        "def add(a: int, b: int) -> int:\n    return a + b\n\n\n"
        "def mul(a: int, b: int) -> int:\n    if not isinstance(a, int) or not isinstance(b, int):\n"
        "        raise TypeError('ints only')\n    return a * b\n"
    )
    if code_first:
        (repo / "libs/core/src/core/calc.py").write_text(impl)
        commit(repo, f"feat({item}): mul before tests", sign=False)
    (repo / "libs/core/tests/test_mul.py").write_text(
        "import pytest\nfrom core.calc import mul\n\n"
        '@pytest.mark.spec("core.md#mul")\ndef test_mul():\n    assert mul(2, 3) == 6\n\n'
        '@pytest.mark.spec("core.md#mul")\ndef test_mul_rejects():\n    with pytest.raises(TypeError):\n        mul("a", 1)\n'
    )
    commit(repo, f"test({item}): red C1 C2", sign=False)
    ht = state.file_hash(repo / "libs/core/tests/test_mul.py")
    shas["red"] = commit(repo, f"accept(work-{item}): red\n\nAccepts red tests.\n\nAccept: red sha256={ht}\nWork-Item: {item}\n")
    if not code_first:
        (repo / "libs/core/src/core/calc.py").write_text(impl)
    (repo / "working/spec/core.md").write_text("# Core\n\n## Add\nadd returns the sum.\n\n## Mul\nmul returns the product; non-ints raise TypeError.\n")
    data = json.loads((d / "criteria.json").read_text())
    for c in data["criteria"]:
        c["status"] = "pass"; c["evidence"] = "run-1"; c["evaluator"] = "confirmed"
    (d / "criteria.json").write_text(json.dumps(data, indent=2))
    for nxt in ["clarify", "spec", "plan", "red", "implement", "verify", "review"]:
        state.advance(repo, item, nxt, force=True)
    commit(repo, f"feat({item}): mul", sign=False)
    (repo / "pr.md").write_text(PR_DESC)
    return shas


def run_contract(repo: Path, item: str | None = "PROJ-1", labels: str = "", extra: list[str] | None = None) -> int:
    args = ["--base", "base", "--signers", f"file:{repo / '.signers'}", "--description", str(repo / "pr.md")]
    args += ["--item", item] if item else ["--no-item"]
    if labels:
        args += ["--labels", labels]
    args += extra or []
    return pr_contract.main([*args, repo.as_posix()])


# ---------------------------------------------------------------- signers (C37)


class TestSigners:
    def test_file_source_loads(self, signed_repo: Path) -> None:
        keys = signers.load(f"file:{signed_repo / '.signers'}")
        assert "t@example.invalid" in keys and keys["t@example.invalid"][0].startswith("ssh-ed25519")

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(signers.FetchError):
            signers.load(f"file:{tmp_path / 'nope'}")

    def test_github_fetch_failure_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(signers, "_github_signing_keys", lambda _org: (_ for _ in ()).throw(OSError("network")))
        with pytest.raises(signers.FetchError):
            signers.load("github:acme")

    def test_contract_fails_closed_on_fetch_failure(self, signed_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        build_standard_item(signed_repo)
        monkeypatch.setattr(signers, "_github_signing_keys", lambda _org: (_ for _ in ()).throw(OSError("network")))
        code = pr_contract.main(["--item", "PROJ-1", "--base", "base", "--signers", "github:acme",
                                 "--description", str(signed_repo / "pr.md"), signed_repo.as_posix()])
        assert code == 2
        assert "signer" in capsys.readouterr().err.lower()


# ------------------------------------------------------------- pr_contract (C25)


class TestContractPasses:
    def test_complete_standard_pr_passes(self, signed_repo: Path) -> None:
        build_standard_item(signed_repo)
        assert run_contract(signed_repo) == 0

    def test_complete_trivial_pr_passes(self, signed_repo: Path) -> None:
        git(signed_repo, "checkout", "-q", "-b", "fix-typo")
        (signed_repo / "README.md").write_text("fixed\n")
        commit(signed_repo, "docs: typo", sign=False)
        (signed_repo / "pr.md").write_text("Fix a typo in the README.\n")
        assert run_contract(signed_repo, item=None) == 0


class TestContractFails:
    def _out(self, capsys: pytest.CaptureFixture[str]) -> str:
        cap = capsys.readouterr()
        return cap.out + cap.err

    def test_missing_work_item(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        git(signed_repo, "checkout", "-q", "-b", "feature")
        (signed_repo / "libs/core/src/core/calc.py").write_text("def add(a, b):\n    return a + b + 0\n")
        commit(signed_repo, "feat: change", sign=False)
        (signed_repo / "pr.md").write_text("A change.\n")
        assert run_contract(signed_repo, item=None) == 1
        assert "CONTRACT-01" in self._out(capsys)

    def test_unsigned_acceptance(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        build_standard_item(signed_repo)
        git(signed_repo, "config", "--unset", "user.signingkey")
        d = signed_repo / ".work/PROJ-1"
        (d / "intent.md").write_text("# Intent\n## Non-goals\n- none\n- more\n")
        h = state.file_hash(d / "intent.md")
        commit(signed_repo, f"accept(work-PROJ-1): intent\n\nAccept: intent sha256={h}\nWork-Item: PROJ-1\n", sign=False)
        assert run_contract(signed_repo) == 1
        assert "CONTRACT-02" in self._out(capsys)

    def test_hash_mismatch(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        build_standard_item(signed_repo)
        (signed_repo / ".work/PROJ-1/spec.md").write_text("# Spec edited after acceptance\n")
        commit(signed_repo, "chore: edit spec", sign=False)
        assert run_contract(signed_repo) == 1
        assert "CONTRACT-03" in self._out(capsys) and "/amend" in self._out(capsys)

    def test_ordering_violation(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        build_standard_item(signed_repo, code_first=True)
        assert run_contract(signed_repo) == 1
        assert "CONTRACT-04" in self._out(capsys)

    def test_empty_ramification(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        build_standard_item(signed_repo)
        d = signed_repo / ".work/PROJ-1/decisions.md"
        d.write_text(d.read_text() + "## D2: another\nalternative-rejected: x\nramification-if-wrong:\nscope: local\naccepted-by [human]: t\n")
        commit(signed_repo, "chore: decision", sign=False)
        assert run_contract(signed_repo) == 1
        assert "CONTRACT-05" in self._out(capsys) and "D2" in self._out(capsys)

    def test_empty_assumption_risk(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        build_standard_item(signed_repo)
        (signed_repo / ".work/PROJ-1/clarify.md").write_text("# Clarify\n## Assumptions\n- A1: x\n  risk:\n  provenance: inferred\n  reviewed [human]: yes\n  tag: local\n")
        commit(signed_repo, "chore: clarify", sign=False)
        assert run_contract(signed_repo) == 1
        assert "CONTRACT-06" in self._out(capsys)

    def test_missing_promotion(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        build_standard_item(signed_repo)
        d = signed_repo / ".work/PROJ-1/decisions.md"
        d.write_text(d.read_text() + "## D2: durable choice\nalternative-rejected: x\nramification-if-wrong: y\nscope: durable\npromote-to: adr\naccepted-by [human]: t\n")
        commit(signed_repo, "chore: decision", sign=False)
        assert run_contract(signed_repo) == 1
        assert "CONTRACT-07" in self._out(capsys)
        (signed_repo / "working/architecture/decisions/ADR-0001-durable-choice.md").write_text("# ADR-0001\n")
        commit(signed_repo, "docs: adr", sign=False)
        assert run_contract(signed_repo) == 0

    def test_untouched_living_spec(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        build_standard_item(signed_repo)
        git(signed_repo, "checkout", "-q", "base", "--", "working/spec/core.md")
        commit(signed_repo, "chore: revert spec", sign=False)
        assert run_contract(signed_repo) == 1
        assert "CONTRACT-08" in self._out(capsys) and "working/spec/core.md" in self._out(capsys)

    def test_diff_over_budget(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        build_standard_item(signed_repo)
        (signed_repo / "libs/core/src/core/big.py").write_text("x = 1\n" * 401)
        commit(signed_repo, "feat: big", sign=False)
        assert run_contract(signed_repo) == 1
        assert "CONTRACT-09" in self._out(capsys)

    def test_missing_pr_section(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        build_standard_item(signed_repo)
        (signed_repo / "pr.md").write_text(PR_DESC.replace("## Risk\ntier: standard; verified by C1.\n\n", ""))
        assert run_contract(signed_repo) == 1
        assert "CONTRACT-10" in self._out(capsys) and "Risk" in self._out(capsys)

    def test_llm_coauthor_trailer(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        build_standard_item(signed_repo)
        (signed_repo / "libs/core/src/core/calc.py").write_text((signed_repo / "libs/core/src/core/calc.py").read_text() + "\n# note\n")
        commit(signed_repo, "feat: touch\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n", sign=False)
        assert run_contract(signed_repo) == 1
        assert "CONTRACT-11" in self._out(capsys)

    def test_spike_item_cannot_merge(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        git(signed_repo, "checkout", "-q", "-b", "SPIKE-1")
        state.create(signed_repo, "SPIKE-1", "spike", "SPIKE-1")
        commit(signed_repo, "chore: spike", sign=False)
        (signed_repo / "pr.md").write_text("spike\n")
        assert run_contract(signed_repo, item="SPIKE-1") == 1
        assert "CONTRACT-12" in self._out(capsys) and "make start" in self._out(capsys)

    def test_state_disagrees_with_rebuild(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        build_standard_item(signed_repo)
        state.advance(signed_repo, "PROJ-1", "implement", force=True)
        commit(signed_repo, "chore: stage back", sign=False)
        assert run_contract(signed_repo) == 1
        assert "CONTRACT-13" in self._out(capsys)

    def test_retroactive_label_waives_ordering(self, signed_repo: Path) -> None:
        build_standard_item(signed_repo, code_first=True)
        assert run_contract(signed_repo, labels="retroactive-chain") == 0


# ------------------------------------------------------------- compute_tier (C26)


class TestComputeTier:
    def _out(self, capsys: pytest.CaptureFixture[str]) -> tuple[str, str]:
        cap = capsys.readouterr()
        return cap.out, cap.err

    def test_docstring_typo_is_trivial(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        git(signed_repo, "checkout", "-q", "-b", "fix")
        (signed_repo / "libs/core/src/core/calc.py").write_text('def add(a: int, b: int) -> int:\n    """Add two ints."""\n    return a + b\n')
        commit(signed_repo, "docs: docstring", sign=False)
        assert compute_tier.main(["--base", "base", signed_repo.as_posix()]) == 0
        assert "tier: trivial" in self._out(capsys)[0]

    def test_unquoted_string_change_is_trivial(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        git(signed_repo, "checkout", "-q", "-b", "fix")
        (signed_repo / "libs/core/src/core/msg.py").write_text("MSG = 'hello'\n")
        commit(signed_repo, "feat: msg", sign=False)
        git(signed_repo, "branch", "-f", "base")
        (signed_repo / "libs/core/src/core/msg.py").write_text("MSG = 'hello world'\n")
        commit(signed_repo, "fix: msg", sign=False)
        assert compute_tier.main(["--base", "base", signed_repo.as_posix()]) == 0
        assert "tier: trivial" in self._out(capsys)[0]

    def test_spec_quoted_string_change_is_standard(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        git(signed_repo, "checkout", "-q", "-b", "fix")
        (signed_repo / "libs/core/src/core/msg.py").write_text("MSG = 'hello'\n")
        (signed_repo / "working/spec/core.md").write_text("# Core\n\n## Greeting\nThe greeting is 'hello'.\n")
        commit(signed_repo, "feat: msg", sign=False)
        git(signed_repo, "branch", "-f", "base")
        (signed_repo / "libs/core/src/core/msg.py").write_text("MSG = 'hi'\n")
        commit(signed_repo, "fix: msg", sign=False)
        compute_tier.main(["--base", "base", signed_repo.as_posix()])
        assert "tier: standard" in self._out(capsys)[0]

    def test_logic_change_is_standard_with_bounce(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        git(signed_repo, "checkout", "-q", "-b", "fix")
        (signed_repo / "libs/core/src/core/calc.py").write_text("def add(a: int, b: int) -> int:\n    return a + b + 1\n")
        commit(signed_repo, "fix: off by one", sign=False)
        compute_tier.main(["--base", "base", signed_repo.as_posix()])
        out, err = self._out(capsys)
        assert "tier: standard" in out
        assert "BLOCKED" in err and "make start" in err and "make adopt-branch" in err

    def test_high_risk_path(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        git(signed_repo, "checkout", "-q", "-b", "fix")
        (signed_repo / "libs/core/src/core/auth").mkdir()
        (signed_repo / "libs/core/src/core/auth/x.py").write_text("SECRET = 1\n")
        commit(signed_repo, "feat: auth", sign=False)
        compute_tier.main(["--base", "base", signed_repo.as_posix()])
        assert "tier: high" in self._out(capsys)[0]

    def test_trivial_over_budget_is_standard(self, signed_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        git(signed_repo, "checkout", "-q", "-b", "docs")
        (signed_repo / "README.md").write_text("line\n" * 60)
        commit(signed_repo, "docs: big", sign=False)
        compute_tier.main(["--base", "base", signed_repo.as_posix()])
        assert "tier: standard" in self._out(capsys)[0]
