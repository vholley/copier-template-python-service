"""Red tests for plan step S2: the shared layer (C17 block, C18 state).

These fix the interfaces in plan.md. Every later script imports these modules,
so their shape is decided here, before any of them exists.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from delivery import block, state

# ---------------------------------------------------------------- block (C17)


class TestBlockRender:
    def test_render_has_exactly_four_labeled_lines(self) -> None:
        text = block.render(
            "tier",
            "this PR changes behavior in libs/core/service.py",
            "behavior changes need an accepted spec before merge",
            ["make start", "make adopt-branch 0042"],
            "working/README.md#bounced",
        )
        lines = text.splitlines()
        assert lines[0].startswith("BLOCKED  tier: ")
        assert lines[1].startswith("WHY      ")
        assert lines[2].startswith("NEXT     make start")
        assert lines[3].startswith("         make adopt-branch 0042")
        assert lines[4].startswith("MORE     working/README.md#bounced")
        assert len(lines) == 5

    def test_single_next_renders_four_lines(self) -> None:
        text = block.render("r", "w", "y", ["make status"], "working/README.md#x")
        assert len(text.splitlines()) == 4

    def test_next_is_required_and_nonempty(self) -> None:
        with pytest.raises(ValueError, match="NEXT"):
            block.render("r", "w", "y", [], "working/README.md#x")

    def test_more_must_point_into_working_readme(self) -> None:
        with pytest.raises(ValueError, match="MORE"):
            block.render("r", "w", "y", ["make status"], "docs/DEVELOPING.md#x")

    def test_fail_prints_to_stderr_and_returns_code(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = block.fail("r", "what", "why", ["make status"], "working/README.md#x")
        captured = capsys.readouterr()
        assert code == 1
        assert captured.out == ""
        assert captured.err.startswith("BLOCKED  r: what")

    def test_fail_env_returns_two(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = block.fail("r", "what", "why", ["make status"], "working/README.md#x", env=True)
        assert code == 2
        assert "BLOCKED" in capsys.readouterr().err

    def test_parse_roundtrips(self) -> None:
        text = block.render("r", "w", "y", ["a", "b"], "working/README.md#x")
        parsed = block.parse(text)
        assert parsed == block.Block("r", "w", "y", ["a", "b"], "working/README.md#x")


# ---------------------------------------------------------------- state (C18)


@pytest.fixture
def item(repo: Path) -> Path:
    subprocess.run(["git", "checkout", "-q", "-b", "PROJ-1"], cwd=repo, check=True)
    state.create(repo, "PROJ-1", "change", "PROJ-1")
    return repo


class TestStateCreate:
    def test_create_writes_state_with_checksum(self, item: Path) -> None:
        data = json.loads((item / ".work/PROJ-1/state.json").read_text())
        assert data["id"] == "PROJ-1"
        assert data["workflow"] == "change"
        assert data["branch"] == "PROJ-1"
        assert data["stage"] == "intent"
        assert data["accepted"] == {}
        assert data["retries"] == 0
        assert len(data["checksum"]) == 64

    def test_read_verifies_checksum(self, item: Path) -> None:
        assert state.read(item, "PROJ-1").stage == "intent"

    def test_hand_edit_is_detected(self, item: Path) -> None:
        path = item / ".work/PROJ-1/state.json"
        data = json.loads(path.read_text())
        data["stage"] = "review"
        path.write_text(json.dumps(data))
        with pytest.raises(state.IntegrityError, match="checksum"):
            state.read(item, "PROJ-1")

    def test_create_twice_fails(self, item: Path) -> None:
        with pytest.raises(state.StateError, match="exists"):
            state.create(item, "PROJ-1", "change", "PROJ-1")

    def test_defect_workflow_starts_at_intent(self, repo: Path) -> None:
        state.create(repo, "BUG-7", "change-defect", "BUG-7")
        assert state.read(repo, "BUG-7").stage == "intent"


class TestStateTransitions:
    def test_every_state_has_an_exit(self) -> None:
        for s in state.STATES:
            if s in state.TERMINAL:
                continue
            assert state.exits(s), f"{s} has no exit"

    def test_terminal_states_have_no_exit(self) -> None:
        for s in state.TERMINAL:
            assert state.exits(s) == []

    def test_abandon_is_legal_from_every_non_terminal_state(self) -> None:
        for s in state.STATES:
            if s not in state.TERMINAL:
                assert "abandoned" in state.exits(s), s

    def test_advance_along_change_path(self, item: Path) -> None:
        for nxt in ["clarify", "spec", "plan", "red", "implement", "verify", "review", "merged"]:
            state.advance(item, "PROJ-1", nxt, force=True)
            assert state.read(item, "PROJ-1").stage == nxt

    def test_illegal_transition_is_refused(self, item: Path) -> None:
        with pytest.raises(state.TransitionError, match="intent -> review"):
            state.advance(item, "PROJ-1", "review", force=True)

    def test_defect_path_skips_spec_and_red(self, repo: Path) -> None:
        state.create(repo, "BUG-7", "change-defect", "BUG-7")
        for nxt in ["diagnose", "plan", "implement"]:
            state.advance(repo, "BUG-7", nxt, force=True)
        assert state.read(repo, "BUG-7").stage == "implement"

    def test_abandon_archives_and_marks(self, item: Path) -> None:
        state.abandon(item, "PROJ-1")
        assert not (item / ".work/PROJ-1").exists()
        archived = json.loads((item / "working/history/PROJ-1/state.json").read_text())
        assert archived["stage"] == "abandoned"


class TestStateGuards:
    """advance() without force checks the gate for the transition."""

    def test_intent_to_clarify_requires_acceptance(self, item: Path) -> None:
        with pytest.raises(state.GateError, match="Accept: intent"):
            state.advance(item, "PROJ-1", "clarify")

    def test_acceptance_recorded_unlocks(self, item: Path) -> None:
        state.record_acceptance(item, "PROJ-1", "intent", "deadbeef")
        state.advance(item, "PROJ-1", "clarify")
        assert state.read(item, "PROJ-1").accepted["intent"] == "deadbeef"

    def test_retry_counter_and_escalation(self, item: Path) -> None:
        for nxt in ["clarify", "spec", "plan", "red", "implement"]:
            state.advance(item, "PROJ-1", nxt, force=True)
        for _ in range(3):
            state.bump_retry(item, "PROJ-1")
        assert state.read(item, "PROJ-1").retries == 3
        state.advance(item, "PROJ-1", "escalated")
        assert state.read(item, "PROJ-1").stage == "escalated"
        assert "implement" in state.exits("escalated")


class TestStateBinding:
    def test_bound_item_for_branch(self, item: Path) -> None:
        assert state.bound_item(item, "PROJ-1") == "PROJ-1"

    def test_unbound_branch_returns_none(self, item: Path) -> None:
        assert state.bound_item(item, "feature/x") is None
