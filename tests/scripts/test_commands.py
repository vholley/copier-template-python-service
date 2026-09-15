"""Red tests for plan step S6: engineer commands (C27) and housekeeping (C28).

Interfaces fixed here:
- start.offers(repo) -> list[str] of answer keys for the current context (19.1)
  start.main(["--answer", KEY, "--ticket", ID, repo])
- status.report(repo) -> str (19.3 fields; ends with "commands available now")
- accept.prepare(repo, item, stage) -> Path of the message file; accept.sign(repo, item, stage)
  runs `git commit -S -F`; the message follows 5.5 exactly
- registry: working/commands.toml; help.render(repo) -> str grouped by `when`
- post_merge.main([--item ID, repo]); observe.main([...]); audit_observations.main([repo])
- vendored_check.main([repo]); loop_report.main([--base REF, repo])
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from delivery import accept, audit_observations, compute_tier, gitx, help as help_cmd, hooks, loop_report, observe, post_merge, start, state, state_cli, status, vendored_check


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


REGISTRY = '''[[command]]
name = "start"
description = "Begin work: asks what you are here to do"
when = "anywhere"
runner = "both"

[[command]]
name = "status"
description = "Where am I and what is next"
when = "anywhere"
runner = "both"

[[command]]
name = "accept"
description = "Sign a prepared acceptance (engineer only)"
when = "front-stage"
runner = "human"

[[command]]
name = "intent"
description = "Write intent.md"
when = "front-stage"
runner = "agent"
'''


@pytest.fixture
def project(repo: Path, tmp_path: Path) -> Path:
    (repo / "working/standards").mkdir(parents=True)
    (repo / "working/standards/budgets.md").write_text("stop_hook.retry_cap: 3\n")
    (repo / "working/commands.toml").write_text(REGISTRY)
    (repo / "working/history").mkdir()
    (repo / "working/observations.md").write_text("# Observations\n")
    (repo / "libs/core/src/core").mkdir(parents=True)
    key = tmp_path / "key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", "t@example.invalid"], check=True)
    git(repo, "config", "gpg.format", "ssh")
    git(repo, "config", "user.signingkey", str(key) + ".pub")
    allowed = tmp_path / "allowed_signers"
    allowed.write_text(f"t@example.invalid {(key.with_suffix('.pub')).read_text().strip()}\n")
    git(repo, "config", "gpg.ssh.allowedSignersFile", str(allowed))  # %G? reports N without it
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "chore: scaffold")
    return repo


# ---------------------------------------------------------------- start (19.1)


class TestStart:
    def test_offers_on_clean_develop(self, project: Path) -> None:
        assert start.offers(project) == ["quick-change", "change", "bug-fix", "explore", "opt-out"]

    def test_offers_on_bound_branch(self, project: Path) -> None:
        start.main(["--answer", "change", "--ticket", "PROJ-1", project.as_posix()])
        assert start.offers(project) == ["continue", "abandon"]

    def test_offers_on_spike(self, project: Path) -> None:
        start.main(["--answer", "explore", "--ticket", "SPIKE-1", project.as_posix()])
        assert start.offers(project) == ["to-change", "to-bug-fix", "keep-exploring"]

    def test_offers_on_unbound_branch_with_changes(self, project: Path) -> None:
        git(project, "checkout", "-q", "-b", "feature-x")
        (project / "libs/core/src/core/x.py").write_text("x = 1\n")
        assert start.offers(project) == ["quick-change", "attach"]

    def test_change_creates_bound_item(self, project: Path) -> None:
        assert start.main(["--answer", "change", "--ticket", "PROJ-1", project.as_posix()]) == 0
        st = state.read(project, "PROJ-1")
        assert st.workflow == "change" and st.branch == "PROJ-1" and st.stage == "intent"
        assert git(project, "rev-parse", "--abbrev-ref", "HEAD").strip() == "PROJ-1"
        assert (project / ".work/PROJ-1/intent.md").exists()

    def test_bug_fix_creates_defect_item(self, project: Path) -> None:
        start.main(["--answer", "bug-fix", "--ticket", "BUG-2", project.as_posix()])
        assert state.read(project, "BUG-2").workflow == "change-defect"

    def test_quick_change_creates_branch_only(self, project: Path) -> None:
        start.main(["--answer", "quick-change", "--ticket", "typo", project.as_posix()])
        assert git(project, "rev-parse", "--abbrev-ref", "HEAD").strip() == "typo"
        assert not (project / ".work").exists()

    def test_attach_binds_existing_branch(self, project: Path) -> None:
        git(project, "checkout", "-q", "-b", "feature-x")
        (project / "libs/core/src/core/x.py").write_text("x = 1\n")
        assert start.main(["--answer", "attach", "--ticket", "PROJ-9", project.as_posix()]) == 0
        assert state.read(project, "PROJ-9").branch == "feature-x"

    def test_spike_to_change_rebinds(self, project: Path) -> None:
        start.main(["--answer", "explore", "--ticket", "SPIKE-1", project.as_posix()])
        (project / ".work/SPIKE-1/notes.md").write_text("found the thing\n")
        assert start.main(["--answer", "to-change", project.as_posix()]) == 0
        st = state.read(project, "SPIKE-1")
        assert st.workflow == "change" and st.stage == "intent"
        assert "found the thing" in (project / ".work/SPIKE-1/intent.md").read_text()

    def test_unoffered_answer_is_refused(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert start.main(["--answer", "continue", project.as_posix()]) == 1
        assert "BLOCKED" in capsys.readouterr().err

    def test_new_project_answer_never_offered(self, project: Path) -> None:
        assert "new-project" not in start.offers(project)


# --------------------------------------------------------------- status (19.3)


class TestStatus:
    def test_report_fields_on_item(self, project: Path) -> None:
        start.main(["--answer", "change", "--ticket", "PROJ-1", project.as_posix()])
        text = status.report(project)
        for label in ("Branch", "Kind of work", "Stage", "Accepted", "Blocking", "Next", "commands available now"):
            assert label in text, label
        assert "PROJ-1" in text and "intent" in text
        assert "make accept STAGE=intent" in text or "/intent" in text

    def test_report_on_unbound_branch(self, project: Path) -> None:
        text = status.report(project)
        assert "no work item" in text and "make start" in text

    def test_available_commands_are_legal_transitions(self, project: Path) -> None:
        start.main(["--answer", "change", "--ticket", "PROJ-1", project.as_posix()])
        text = status.report(project)
        tail = text.split("commands available now")[1]
        assert "/intent" in tail and "make abandon" in tail
        assert "/implement" not in tail

    def test_escalated_lists_exits(self, project: Path) -> None:
        start.main(["--answer", "change", "--ticket", "PROJ-1", project.as_posix()])
        for nxt in ["clarify", "spec", "plan", "red", "implement"]:
            state.advance(project, "PROJ-1", nxt, force=True)
        for _ in range(3):
            state.bump_retry(project, "PROJ-1")
        state.advance(project, "PROJ-1", "escalated")
        tail = status.report(project).split("commands available now")[1]
        assert "implement" in tail and "spec" in tail and "abandon" in tail

    def test_blocking_shows_consistency_problem(self, project: Path) -> None:
        start.main(["--answer", "change", "--ticket", "PROJ-1", project.as_posix()])
        (project / ".work/PROJ-1/state.json").write_text("{broken")
        text = status.report(project)
        assert "Blocking" in text and "make rebuild" in text


# ------------------------------------------------------------- accept (5.5, D6)


class TestAccept:
    def test_prepare_writes_message_with_hashes(self, project: Path) -> None:
        start.main(["--answer", "change", "--ticket", "PROJ-1", project.as_posix()])
        (project / ".work/PROJ-1/intent.md").write_text("# Intent\n## Non-goals\n- none\n")
        msg_path = accept.prepare(project, "PROJ-1", "intent")
        msg = msg_path.read_text()
        assert msg.startswith("accept(work-PROJ-1): intent\n")
        assert re.search(r"^Accept: intent sha256=[0-9a-f]{64}$", msg, re.M)
        assert "Work-Item: PROJ-1" in msg
        staged = git(project, "diff", "--cached", "--name-only").split()
        assert staged and all(p.startswith(".work/PROJ-1/") for p in staged)

    def test_prepare_refuses_empty_non_goals(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        start.main(["--answer", "change", "--ticket", "PROJ-1", project.as_posix()])
        (project / ".work/PROJ-1/intent.md").write_text("# Intent\n## Non-goals\n")
        with pytest.raises(accept.PrepareError, match="Non-goals"):
            accept.prepare(project, "PROJ-1", "intent")

    def test_sign_creates_signed_commit_and_records_acceptance(self, project: Path) -> None:
        start.main(["--answer", "change", "--ticket", "PROJ-1", project.as_posix()])
        (project / ".work/PROJ-1/intent.md").write_text("# Intent\n## Non-goals\n- none\n")
        accept.prepare(project, "PROJ-1", "intent")
        assert accept.sign(project, "PROJ-1", "intent") == 0
        assert git(project, "log", "-1", "--format=%G?").strip() == "G"
        assert state.read(project, "PROJ-1").accepted["intent"] == git(project, "rev-parse", "HEAD").strip()
        assert state.read(project, "PROJ-1").stage == "clarify"

    def test_sign_refuses_when_staged_content_changed(self, project: Path) -> None:
        start.main(["--answer", "change", "--ticket", "PROJ-1", project.as_posix()])
        (project / ".work/PROJ-1/intent.md").write_text("# Intent\n## Non-goals\n- none\n")
        accept.prepare(project, "PROJ-1", "intent")
        (project / ".work/PROJ-1/intent.md").write_text("# Intent edited\n## Non-goals\n- none\n")
        git(project, "add", ".work/PROJ-1/intent.md")
        assert accept.sign(project, "PROJ-1", "intent") == 1

    def test_spec_acceptance_batches_decisions(self, project: Path) -> None:
        start.main(["--answer", "change", "--ticket", "PROJ-1", project.as_posix()])
        d = project / ".work/PROJ-1"
        (d / "spec.md").write_text("# Spec\n")
        (d / "criteria.json").write_text(json.dumps({"id": "PROJ-1", "change_type": "trivial", "criteria": []}))
        (d / "decisions.md").write_text("# Decisions\n## D1: x\nalternative-rejected: y\nramification-if-wrong: z\nscope: local\naccepted-by [human]: t\n")
        msg = accept.prepare(project, "PROJ-1", "spec").read_text()
        assert "Accept-Decision: D1 sha256=" in msg

    def test_opt_out_acceptance(self, project: Path) -> None:
        git(project, "checkout", "-q", "-b", "feature-x")
        msg = accept.prepare(project, None, "opt-out", reason="prototype").read_text()
        assert msg.startswith("accept(feature-x): opt-out")
        assert "Opt-Out: sha256=" in msg
        assert (project / ".work/feature-x/opt-out.md").read_text().count("prototype") == 1
        assert accept.sign(project, None, "opt-out") == 0
        assert accept.opted_out(project, "feature-x")


# --------------------------------------------------------- registry and help (19.7)


class TestHelp:
    def test_help_groups_by_when_and_marks_runner(self, project: Path) -> None:
        text = help_cmd.render(project)
        assert "anywhere" in text and "front-stage" in text
        assert re.search(r"accept.*engineer", text)

    def test_registry_and_command_files_must_agree(self, project: Path) -> None:
        (project / ".claude/commands").mkdir(parents=True)
        for name in ("start", "status", "accept"):
            (project / f".claude/commands/{name}.md").write_text(f"---\ndescription: x\n---\n/{name}\n")
        problems = help_cmd.check(project)
        assert any("intent" in p and "no .claude/commands" in p for p in problems)


# --------------------------------------------------------- housekeeping (C28)


class TestHousekeeping:
    def test_post_merge_archives_without_progress(self, project: Path) -> None:
        start.main(["--answer", "change", "--ticket", "PROJ-1", project.as_posix()])
        (project / ".work/PROJ-1/progress.md").write_text("notes\n")
        assert post_merge.main(["--item", "PROJ-1", project.as_posix()]) == 0
        assert not (project / ".work/PROJ-1").exists()
        assert (project / "working/history/PROJ-1/state.json").exists()
        assert not (project / "working/history/PROJ-1/progress.md").exists()

    def test_observe_drops_hypothesized(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        code = observe.main(["--file", "libs/core/src/core/x.py", "--line", "3", "--what", "w",
                             "--consequence", "c", "--provenance", "hypothesized", "--source", "PROJ-1", project.as_posix()])
        assert code == 0
        assert "not recorded" in capsys.readouterr().out
        assert "libs/core" not in (project / "working/observations.md").read_text()

    def test_observe_records_inferred_with_expiry(self, project: Path) -> None:
        observe.main(["--file", "libs/core/src/core/x.py", "--line", "3", "--what", "w",
                      "--consequence", "c", "--provenance", "inferred", "--source", "PROJ-1", project.as_posix()])
        text = (project / "working/observations.md").read_text()
        assert "O-1" in text and re.search(r"expires: \d{4}-\d{2}-\d{2}", text)

    def test_observe_routes_observed_to_defect(self, project: Path, capsys: pytest.CaptureFixture[str]) -> None:
        observe.main(["--file", "x.py", "--line", "1", "--what", "w", "--consequence", "c",
                      "--provenance", "observed", "--source", "PROJ-1", project.as_posix()])
        out = capsys.readouterr().out
        assert "defect" in out
        assert "make start" in out

    def test_audit_deletes_expired(self, project: Path) -> None:
        (project / "working/observations.md").write_text(
            "# Observations\n- O-1: x.py:1 old\n  consequence: c\n  provenance: inferred(a)\n  source: PROJ-1\n  expires: 2000-01-01\n"
            "- O-2: y.py:1 new\n  consequence: c\n  provenance: inferred(a)\n  source: PROJ-2\n  expires: 2999-01-01\n"
        )
        assert audit_observations.main([project.as_posix()]) == 0
        text = (project / "working/observations.md").read_text()
        assert "O-1" not in text and "O-2" in text

    def test_vendored_check(self, project: Path) -> None:
        d = project / ".claude/skills/deslop"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("skill\n")
        digest = vendored_check.digest(d)
        (project / ".claude/VENDORED.md").write_text(f"| deslop | /mnt/skills/user/deslop | 2026-09-13 | {digest} |\n")
        assert vendored_check.main([project.as_posix()]) == 0
        (d / "SKILL.md").write_text("skill edited\n")
        assert vendored_check.main([project.as_posix()]) == 1

    def test_loop_report_lists_labeled_exits(self, project: Path) -> None:
        git(project, "checkout", "-q", "-b", "x")
        (project / "a.txt").write_text("a\n")
        git(project, "add", "-A")
        git(project, "commit", "-q", "-m", "feat: a\n\nLabels: tier-override, break-glass\n")
        text = loop_report.render(project, base="develop")
        assert "tier-override" in text and "break-glass" in text


# ------------------------------------------------- unborn branch (a repo with no commits)


SCAFFOLD = 'git add -A && git commit -m "chore: generate from copier-template-python-service"'


@pytest.fixture
def unborn(tmp_path: Path) -> Path:
    """A repository with a branch but no commits, so HEAD does not resolve.

    Generation makes the scaffold commit, but stops short of it when git has no
    author identity. The engineer meets this state next, and every command has to
    say what to do rather than raise.
    """
    subprocess.run(["git", "init", "-q", "-b", "develop"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.invalid"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("x\n", encoding="utf-8")
    return tmp_path


class TestUnbornBranch:
    """No traceback, a four-line block, and the next command is the scaffold commit."""

    def test_gitx_raises_a_named_error(self, unborn: Path) -> None:
        with pytest.raises(gitx.UnbornBranchError):
            gitx.current_branch(unborn)

    def test_start_blocks(self, unborn: Path, capsys: pytest.CaptureFixture[str]) -> None:
        code = start.main([str(unborn)])
        err = capsys.readouterr().err
        assert code == 1, err
        assert "BLOCKED" in err and SCAFFOLD in err and "Traceback" not in err

    def test_status_blocks(self, unborn: Path, capsys: pytest.CaptureFixture[str]) -> None:
        code = status.main([str(unborn)])
        err = capsys.readouterr().err
        assert code == 1, err
        assert "BLOCKED" in err and SCAFFOLD in err and "Traceback" not in err

    def test_compute_tier_blocks(self, unborn: Path, capsys: pytest.CaptureFixture[str]) -> None:
        code = compute_tier.main(["--base", "develop", str(unborn)])
        err = capsys.readouterr().err
        assert code == 1, err
        assert "BLOCKED" in err and SCAFFOLD in err and "Traceback" not in err

    def test_hooks_block_with_exit_two(self, unborn: Path) -> None:
        """Hooks use exit 2: that is what Claude Code reads as a block."""
        code, _out, err = hooks.run("prompt", {}, unborn)
        assert code == 2, err
        assert "BLOCKED" in err and SCAFFOLD in err and "Traceback" not in err

    def test_the_block_is_four_lines(self, unborn: Path, capsys: pytest.CaptureFixture[str]) -> None:
        start.main([str(unborn)])
        lines = [ln for ln in capsys.readouterr().err.splitlines() if ln.strip()]
        assert len(lines) == 4, lines
        assert lines[0].startswith("BLOCKED")
        assert lines[1].startswith("WHY")
        assert lines[2].startswith("NEXT")
        assert lines[3].startswith("MORE")

    def test_state_cli_blocks(self, unborn: Path, capsys: pytest.CaptureFixture[str]) -> None:
        code = state_cli.main(["bound", str(unborn)])
        assert code == 1, capsys.readouterr().err

    def test_accept_blocks(self, unborn: Path, capsys: pytest.CaptureFixture[str]) -> None:
        code = accept.main(["--stage", "opt-out", str(unborn)])
        assert code in (1, 2), capsys.readouterr().err
