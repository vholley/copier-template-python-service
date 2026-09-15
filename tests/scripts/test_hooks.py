"""Red tests for plan step S7: the session hooks (C30 to C33).

Every hook is `python -m delivery.hooks <event>` reading Claude Code's event JSON
on stdin. Exit 0 allows; exit 2 blocks with a four-line message on stderr
scripts/hooks/hook.py calls these; the
tests call hooks.run(event, payload, repo) directly.

  session-start   prints the orientation text (7.1, 19.3) on stdout
  prompt          UserPromptSubmit: refuse implementation prompts on a bound branch
                  before spec acceptance; on unbound branches never block, add a
                  one-line nudge for behavior-change prompts (19.1)
  edit            PreToolUse for Edit/Write: block source edits before spec (or
                  before a confirmed cause on defects); block protected paths always;
                  spikes exempt from stage blocks
  bash            PreToolUse for Bash: block `git commit` with Accept:/Accept-Decision:
                  in the message; block `make accept`
  ask             PreToolUse for AskUserQuestion: at most three questions, at most
                  one substantial (19.6)
  stop            Stop: block until make green passed since the last edit and every
                  pass has evidence; three blocks then escalate (7.3)
  subagent-stop   SubagentStop for the evaluator: block until its report exists
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from delivery import hooks, state, status

MORE = "working/README.md#"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


@pytest.fixture
def project(repo: Path) -> Path:
    (repo / "working/standards").mkdir(parents=True)
    (repo / "working/standards/budgets.md").write_text("stop_hook.retry_cap: 3\nreview.question_max_lines: 2\n")
    (repo / "working/architecture").mkdir()
    (repo / "working/architecture/constraints.md").write_text(
        "# Constraints\n## Protected paths\n- working/architecture/**\n- working/standards/**\n- .claude/**\n- scripts/**\n"
    )
    (repo / "libs/core/src/core").mkdir(parents=True)
    (repo / "libs/core/tests").mkdir()
    (repo / "libs/core/src/core/x.py").write_text("x = 1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "chore: scaffold")
    return repo


def bound(project: Path, stage: str, workflow: str = "change") -> Path:
    git(project, "checkout", "-q", "-b", "PROJ-1")
    state.create(project, "PROJ-1", workflow, "PROJ-1")
    for nxt in state_path(workflow, stage):
        state.advance(project, "PROJ-1", nxt, force=True)
    return project


def state_path(workflow: str, stage: str) -> list[str]:
    change = ["clarify", "spec", "plan", "red", "implement", "verify", "review"]
    defect = ["diagnose", "plan", "implement", "verify", "review"]
    seq = change if workflow == "change" else defect
    return seq[: seq.index(stage) + 1] if stage != "intent" else []


def run(event: str, payload: dict[str, object], repo: Path) -> tuple[int, str, str]:
    return hooks.run(event, payload, repo)


# ------------------------------------------------------------ session-start


class TestSessionStart:
    def test_orientation_contains_status_and_map(self, project: Path) -> None:
        bound(project, "spec")
        code, out, _err = run("session-start", {"source": "startup"}, project)
        assert code == 0
        assert "Branch" in out and "PROJ-1" in out and "libs/core" in out
        assert "Next" in out


# -------------------------------------------------------------- prompt (C30)


class TestPromptGuard:
    def test_implementation_prompt_blocked_before_spec(self, project: Path) -> None:
        bound(project, "clarify")
        code, _out, err = run("prompt", {"prompt": "implement the new endpoint now"}, project)
        assert code == 2
        assert "BLOCKED" in err and "clarify" in err and "/clarify" in err and MORE in err
        assert "make opt-out" in err

    def test_planning_prompt_allowed_before_spec(self, project: Path) -> None:
        bound(project, "clarify")
        code, _out, _err = run("prompt", {"prompt": "what contradictions do you see in the intent?"}, project)
        assert code == 0

    def test_after_red_acceptance_prompts_allowed(self, project: Path) -> None:
        bound(project, "implement")
        code, _out, _err = run("prompt", {"prompt": "implement step 1"}, project)
        assert code == 0

    def test_unbound_branch_never_blocks_but_nudges(self, project: Path) -> None:
        git(project, "checkout", "-q", "-b", "feature-x")
        code, out, _err = run("prompt", {"prompt": "add a --json flag to the list command"}, project)
        assert code == 0
        assert "/start" in out

    def test_unbound_branch_typo_prompt_no_nudge(self, project: Path) -> None:
        git(project, "checkout", "-q", "-b", "feature-x")
        code, out, _err = run("prompt", {"prompt": "fix the typo in the CLI help text"}, project)
        assert code == 0 and out.strip() == ""

    def test_spike_never_blocks(self, project: Path) -> None:
        git(project, "checkout", "-q", "-b", "SPIKE-1")
        state.create(project, "SPIKE-1", "spike", "SPIKE-1")
        code, _out, _err = run("prompt", {"prompt": "implement a quick prototype"}, project)
        assert code == 0


# ---------------------------------------------------------------- edit (C30)


def edit_payload(path: str) -> dict[str, object]:
    return {"tool_name": "Edit", "tool_input": {"file_path": path}}


class TestEditGuard:
    def test_source_edit_blocked_at_spec(self, project: Path) -> None:
        bound(project, "spec")
        code, _o, err = run("edit", edit_payload("libs/core/src/core/x.py"), project)
        assert code == 2 and "spec" in err and "make opt-out" in err

    def test_scratch_edit_allowed_at_spec(self, project: Path) -> None:
        bound(project, "spec")
        code, _o, _e = run("edit", edit_payload(".work/PROJ-1/spec.md"), project)
        assert code == 0

    def test_source_edit_allowed_at_implement(self, project: Path) -> None:
        bound(project, "implement")
        code, _o, _e = run("edit", edit_payload("libs/core/src/core/x.py"), project)
        assert code == 0

    def test_defect_source_edit_blocked_until_cause_confirmed(self, project: Path) -> None:
        bound(project, "diagnose", workflow="change-defect")
        (project / ".work/PROJ-1/diagnosis.md").write_text("## Cause claims\n- K1: x\n  provenance: hypothesized\n  status: open\n")
        code, _o, err = run("edit", edit_payload("libs/core/src/core/x.py"), project)
        assert code == 2 and "confirmed" in err
        code, _o, _e = run("edit", edit_payload("libs/core/tests/test_x.py"), project)
        assert code == 0
        (project / ".work/PROJ-1/diagnosis.md").write_text("## Cause claims\n- K1: x\n  provenance: observed(E1)\n  status: confirmed\n")
        code, _o, _e = run("edit", edit_payload("libs/core/src/core/x.py"), project)
        assert code == 0

    def test_protected_path_blocked_on_an_unbound_branch(self, project: Path) -> None:
        git(project, "checkout", "-q", "-b", "feature-x")
        code, _o, err = run("edit", edit_payload("working/standards/budgets.md"), project)
        assert code == 2 and "protected" in err

    def test_state_json_edit_blocked(self, project: Path) -> None:
        bound(project, "implement")
        code, _o, err = run("edit", edit_payload(".work/PROJ-1/state.json"), project)
        assert code == 2 and "stage_state" in err

    def test_spike_source_edit_allowed(self, project: Path) -> None:
        git(project, "checkout", "-q", "-b", "SPIKE-1")
        state.create(project, "SPIKE-1", "spike", "SPIKE-1")
        code, _o, _e = run("edit", edit_payload("libs/core/src/core/x.py"), project)
        assert code == 0

    def test_unbound_branch_source_edit_allowed(self, project: Path) -> None:
        git(project, "checkout", "-q", "-b", "feature-x")
        code, _o, _e = run("edit", edit_payload("libs/core/src/core/x.py"), project)
        assert code == 0


# ---------------------------------------------------------------- bash (C32)


def bash_payload(cmd: str) -> dict[str, object]:
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


class TestBashGuard:
    @pytest.mark.parametrize("cmd", [
        'git commit -m "accept(work-PROJ-1): intent\n\nAccept: intent sha256=abc"',
        'git commit -S -F .work/PROJ-1/accept-spec.msg',
        'git commit -m "x" -m "Accept-Decision: D1 sha256=abc"',
        "make accept STAGE=intent",
    ])
    def test_acceptance_commits_blocked(self, project: Path, cmd: str) -> None:
        bound(project, "intent")
        code, _o, err = run("bash", bash_payload(cmd), project)
        assert code == 2 and "engineer" in err

    def test_accept_prepare_allowed(self, project: Path) -> None:
        bound(project, "intent")
        code, _o, _e = run("bash", bash_payload("make accept-prepare STAGE=intent"), project)
        assert code == 0

    def test_ordinary_commit_allowed(self, project: Path) -> None:
        bound(project, "implement")
        code, _o, _e = run("bash", bash_payload('git commit -m "feat(PROJ-1): step 1"'), project)
        assert code == 0


# ----------------------------------------------------------------- ask (C31)


def ask_payload(questions: list[str]) -> dict[str, object]:
    return {"tool_name": "AskUserQuestion", "tool_input": {"questions": [{"question": q, "options": []} for q in questions]}}


class TestAskLimiter:
    def test_four_small_questions_blocked(self, project: Path) -> None:
        code, _o, err = run("ask", ask_payload(["a?", "b?", "c?", "d?"]), project)
        assert code == 2 and "three" in err

    def test_two_substantial_blocked(self, project: Path) -> None:
        big = "line\n" * 5
        code, _o, err = run("ask", ask_payload([big, big]), project)
        assert code == 2 and "one substantial" in err

    def test_three_small_allowed(self, project: Path) -> None:
        code, _o, _e = run("ask", ask_payload(["a?", "b?", "c?"]), project)
        assert code == 0

    def test_one_substantial_allowed(self, project: Path) -> None:
        code, _o, _e = run("ask", ask_payload(["line\n" * 5]), project)
        assert code == 0


# ---------------------------------------------------------------- stop (C33)


class TestStopGate:
    def _criteria(self, project: Path, status_: str, evidence: str | None) -> None:
        (project / ".work/PROJ-1/criteria.json").write_text(json.dumps({
            "id": "PROJ-1", "change_type": "trivial",
            "criteria": [{"id": "C1", "class": "positive", "statement": "s", "verify": "true",
                          "status": status_, "evidence": evidence, "evaluator": None, "plan_steps": []}],
        }))

    def test_uncommitted_source_blocks(self, project: Path) -> None:
        bound(project, "implement")
        self._criteria(project, "fail", None)
        (project / "libs/core/src/core/x.py").write_text("x = 2\n")
        hooks.record_green(project)
        code, _o, err = run("stop", {}, project)
        assert code == 2 and "uncommitted" in err and "x.py" in err

    def test_pass_without_evidence_blocks(self, project: Path) -> None:
        bound(project, "implement")
        self._criteria(project, "pass", None)
        hooks.record_green(project)
        code, _o, err = run("stop", {}, project)
        assert code == 2 and "C1" in err and "evidence" in err

    def test_green_not_run_since_edit_blocks(self, project: Path) -> None:
        bound(project, "implement")
        self._criteria(project, "fail", None)
        (project / "libs/core/src/core/x.py").write_text("x = 2\n")
        git(project, "add", "-A")
        git(project, "commit", "-q", "-m", "feat: x")
        code, _o, err = run("stop", {}, project)
        assert code == 2 and "make green" in err

    def test_all_clear_allows(self, project: Path) -> None:
        bound(project, "implement")
        self._criteria(project, "pass", "run-1")
        git(project, "add", "-A")
        git(project, "commit", "-q", "-m", "chore: criteria")
        hooks.record_green(project)
        code, _o, _e = run("stop", {}, project)
        assert code == 0

    def test_three_blocks_then_escalate(self, project: Path) -> None:
        bound(project, "implement")
        self._criteria(project, "pass", None)
        git(project, "add", "-A")
        git(project, "commit", "-q", "-m", "chore: criteria")
        hooks.record_green(project)
        codes = [run("stop", {}, project)[0] for _ in range(4)]
        assert codes == [2, 2, 2, 0]
        assert state.load_unchecked(project, "PROJ-1").stage == "escalated"
        assert "escalat" in (project / ".work/PROJ-1/progress.md").read_text()

    def test_red_stage_requires_failing_tests(self, project: Path) -> None:
        bound(project, "red")
        (project / ".work/PROJ-1/tests.json").write_text(json.dumps({"C1": [{"test": "libs/core/tests/test_x.py::test_x", "commit": ""}]}))
        (project / "libs/core/tests/test_x.py").write_text("def test_x():\n    assert True\n")
        git(project, "add", "-A")
        git(project, "commit", "-q", "-m", "test: passes already")
        hooks.record_green(project)
        code, _o, err = run("stop", {}, project)
        assert code == 2 and "fail" in err and "test_x" in err

    def test_stop_outside_build_stages_allows(self, project: Path) -> None:
        bound(project, "spec")
        code, _o, _e = run("stop", {}, project)
        assert code == 0


# ------------------------------------------------------- subagent-stop (C33)


class TestSubagentStop:
    def test_evaluator_without_report_blocks(self, project: Path) -> None:
        bound(project, "verify")
        code, _o, err = run("subagent-stop", {"agent_name": "evaluator"}, project)
        assert code == 2 and "report" in err

    def test_evaluator_with_report_allows(self, project: Path) -> None:
        bound(project, "verify")
        (project / ".work/PROJ-1/evaluator-report.md").write_text("C1: confirmed\n")
        code, _o, _e = run("subagent-stop", {"agent_name": "evaluator"}, project)
        assert code == 0

    def test_other_subagents_unaffected(self, project: Path) -> None:
        bound(project, "verify")
        code, _o, _e = run("subagent-stop", {"agent_name": "necessity-reviewer"}, project)
        assert code == 0


# ---------------------------------------------------- settings.json (S2.2, A4)


class TestSettings:
    def test_settings_declare_every_hook_and_disable_coauthor(self) -> None:
        settings = json.loads((Path(__file__).parents[2] / "template/.claude/settings.json").read_text())
        assert settings["includeCoAuthoredBy"] is False
        hooks_cfg = settings["hooks"]
        for event in ("SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop", "SubagentStop"):
            assert event in hooks_cfg, event
        matchers = {h.get("matcher", "") for h in hooks_cfg["PreToolUse"]}
        assert any("Edit" in m for m in matchers) and any("Bash" in m for m in matchers) and any("AskUserQuestion" in m for m in matchers)
        for event, entries in hooks_cfg.items():
            for entry in entries:
                for h in entry["hooks"]:
                    assert h["type"] == "command", f"{event}: hooks are deterministic shell (11.1)"
                    assert "scripts/hooks/hook.py" in h["command"], h["command"]
                    assert h["command"].split()[-1] in hooks.EVENTS, h["command"]

    def test_every_declared_hook_script_exists(self) -> None:
        root = Path(__file__).parents[2] / "template"
        settings = json.loads((root / ".claude/settings.json").read_text())
        for entries in settings["hooks"].values():
            for entry in entries:
                for h in entry["hooks"]:
                    rel = next(a for a in h["command"].split() if a.endswith(".py"))
                    script = root / rel
                    assert script.exists(), script

    def test_every_event_is_declared_in_settings(self) -> None:
        """settings.json wires all eight events, including post-edit."""
        settings = json.loads((Path(__file__).parents[2] / "template/.claude/settings.json").read_text())
        declared = {
            h["command"].split()[-1]
            for entries in settings["hooks"].values()
            for entry in entries
            for h in entry["hooks"]
        }
        assert declared == set(hooks.EVENTS)


class TestAbsolutePaths:
    """Claude Code sends file_path as an absolute path (M5)."""

    def test_protected_path_blocks_when_sent_absolute(self, repo: Path) -> None:
        (repo / ".claude").mkdir(parents=True, exist_ok=True)
        (repo / ".claude/settings.json").write_text("{}\n", encoding="utf-8")
        payload = {"tool_input": {"file_path": str(repo / ".claude" / "settings.json")}}
        code, _out, _err = hooks.run("edit", payload, repo)
        assert code == 2

    def test_relative_and_absolute_agree(self, repo: Path) -> None:
        (repo / ".claude").mkdir(parents=True, exist_ok=True)
        (repo / ".claude/settings.json").write_text("{}\n", encoding="utf-8")
        rel = hooks.run("edit", {"tool_input": {"file_path": ".claude/settings.json"}}, repo)
        absolute = hooks.run(
            "edit", {"tool_input": {"file_path": str(repo / ".claude" / "settings.json")}}, repo
        )
        assert rel[0] == absolute[0] == 2

    def test_path_outside_the_repo_is_allowed(self, repo: Path) -> None:
        payload = {"tool_input": {"file_path": str(Path.home() / "notes.txt")}}
        code, _out, _err = hooks.run("edit", payload, repo)
        assert code == 0


PROCESS_FILES = [
    "working/standards/budgets.md",
    "working/architecture/constraints.md",
    "working/architecture/overview.md",
    ".claude/rules/branching.md",
]


class TestProtectedPathsDuringAProjectItem:
    """The files a project item exists to write were the files it could not write.

    /architect's whole output is working/architecture/ and working/standards/, and
    the protected-path guard refused every one of them. The rule it enforces is
    that process-defining files change through a reviewed pull request, and a
    project item is exactly that: its branch opens one. So the guard asks what the
    branch is bound to before it refuses.
    """

    def _project(self, project: Path) -> Path:
        git(project, "checkout", "-q", "-b", "SETUP-1")
        state.create(project, "SETUP-1", "project", "SETUP-1")
        return project

    @pytest.mark.parametrize("rel", PROCESS_FILES)
    def test_allowed_on_a_project_item(self, project: Path, rel: str) -> None:
        code, _o, err = run("edit", edit_payload(rel), self._project(project))
        assert code == 0, (rel, err)

    @pytest.mark.parametrize("rel", PROCESS_FILES)
    def test_blocked_on_a_change_item(self, project: Path, rel: str) -> None:
        bound(project, "implement")
        code, _o, err = run("edit", edit_payload(rel), project)
        assert code == 2, (rel, err)
        assert "protected" in err

    @pytest.mark.parametrize("rel", PROCESS_FILES)
    def test_blocked_on_an_unbound_branch(self, project: Path, rel: str) -> None:
        git(project, "checkout", "-q", "-b", "feature-x")
        code, _o, err = run("edit", edit_payload(rel), project)
        assert code == 2, (rel, err)
        assert "protected" in err

    def test_the_block_names_the_way_through(self, project: Path) -> None:
        """A refusal that does not say how to proceed is the defect, not the block."""
        bound(project, "implement")
        _c, _o, err = run("edit", edit_payload("working/standards/budgets.md"), project)
        assert "process-change" in err, err

    def test_state_json_is_still_refused_on_a_project_item(self, project: Path) -> None:
        """The derived cache is not a process file; nothing unlocks it."""
        proj = self._project(project)
        code, _o, err = run("edit", edit_payload(".work/SETUP-1/state.json"), proj)
        assert code == 2 and "stage_state" in err

    def test_source_edits_are_still_stage_blocked(self, project: Path) -> None:
        """Only the protected-path rule relaxes. A project item at intent is still
        a work item, and code before a signed intent is the thing the stages exist
        to prevent."""
        proj = self._project(project)
        code, _o, err = run("edit", edit_payload("libs/core/src/core/x.py"), proj)
        assert code == 2, err
        assert "stage" in err
