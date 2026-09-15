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

from delivery import accept, audit_observations, compute_tier, gitx, help as help_cmd, hooks, log, loop_report, observe, post_merge, start, state, state_cli, status, vendored_check


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
    def test_offers_on_clean_develop(self, established: Path) -> None:
        assert start.offers(established) == [
            "quick-change", "change", "bug-fix", "explore", "process-change", "opt-out",
        ]

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


@pytest.fixture
def logged(tmp_path: Path) -> Path:
    """A project with an empty issue log."""
    (tmp_path / "working").mkdir()
    (tmp_path / "working" / "log.md").write_text(
        "# Issue log\n\nAppend-only. Status moves from open to closed only.\n", encoding="utf-8"
    )
    return tmp_path


class TestIssueLogClosesExplicitly:
    """Recording a fix and closing an entry are two acts, not one.

    `make log FIX=...` used to write the entry closed, so the log said "resolved"
    at the moment the fix was typed -- before it was reviewed, merged, or shown to
    work. The weekly audit reads open entries, so anything written with a fix was
    invisible to it from birth.
    """

    def _text(self, repo: Path) -> str:
        return (repo / "working" / "log.md").read_text(encoding="utf-8")

    def _status(self, repo: Path, lid: str) -> str:
        return next(e["status"] for e in log.entries(self._text(repo)) if e["id"] == lid)

    def test_an_entry_without_a_fix_is_open(self, logged: Path) -> None:
        lid = log.add(logged, "session", "hook fired wrongly", "no rule for it", "")
        assert self._status(logged, lid) == "open"

    def test_recording_a_fix_leaves_the_entry_open(self, logged: Path) -> None:
        """The point of the item: a written fix is not a landed fix."""
        lid = log.add(logged, "session", "hook fired wrongly", "no rule for it", "widen the glob")
        assert self._status(logged, lid) == "open"
        assert "widen the glob" in self._text(logged)

    def test_closing_marks_it_closed(self, logged: Path) -> None:
        lid = log.add(logged, "session", "w", "m", "widen the glob")
        assert log.close(logged, lid, "") is True
        assert self._status(logged, lid) == "closed"

    def test_closing_keeps_the_fix_already_recorded(self, logged: Path) -> None:
        lid = log.add(logged, "session", "w", "m", "widen the glob")
        log.close(logged, lid, "")
        assert "widen the glob" in self._text(logged)

    def test_closing_an_entry_with_no_fix_takes_one(self, logged: Path) -> None:
        lid = log.add(logged, "session", "w", "m", "")
        log.close(logged, lid, "reverted the rule")
        assert "reverted the rule" in self._text(logged)
        assert self._status(logged, lid) == "closed"

    def test_an_entry_closes_once(self, logged: Path) -> None:
        lid = log.add(logged, "session", "w", "m", "f")
        log.close(logged, lid, "")
        assert log.close(logged, lid, "") is False

    def test_open_lists_a_fixed_but_unclosed_entry(
        self, logged: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        lid = log.add(logged, "session", "w", "m", "widen the glob")
        code = log.main(["open", str(logged)])
        out = capsys.readouterr().out
        assert code == 1, out
        assert lid in out

    def test_open_is_quiet_once_everything_is_closed(
        self, logged: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        lid = log.add(logged, "session", "w", "m", "f")
        log.close(logged, lid, "")
        assert log.main(["open", str(logged)]) == 0
        assert capsys.readouterr().out.strip() == ""

    def test_add_through_main_does_not_close(
        self, logged: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`make log` is this call; it may never be the thing that closes."""
        code = log.main(
            ["add", "--what", "w", "--missing", "m", "--fix", "widen the glob", str(logged)]
        )
        assert code == 0, capsys.readouterr().err
        assert log.entries(self._text(logged))[0]["status"] == "open"

    def test_close_through_main(self, logged: Path, capsys: pytest.CaptureFixture[str]) -> None:
        lid = log.add(logged, "session", "w", "m", "f")
        code = log.main(["close", lid, str(logged)])
        assert code == 0, capsys.readouterr().err
        assert self._status(logged, lid) == "closed"

    def test_closing_an_unknown_id_blocks(
        self, logged: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = log.main(["close", "L-99", str(logged)])
        err = capsys.readouterr().err
        assert code == 1
        assert "BLOCKED" in err and "L-99" in err


@pytest.fixture
def fresh(project: Path) -> Path:
    """A generated project on its first day: libs/ only, apps/ empty, no spec members."""
    (project / "apps").mkdir()
    (project / "working/spec").mkdir(parents=True)
    (project / "working/spec/README.md").write_text("# Living spec\n", encoding="utf-8")
    git(project, "add", "-A")
    git(project, "commit", "-q", "-m", "chore: spec placeholder")
    return project


@pytest.fixture
def established(fresh: Path) -> Path:
    """The same project once it has a member: set-up no longer applies."""
    (fresh / "apps/worker").mkdir(parents=True)
    (fresh / "apps/worker/pyproject.toml").write_text('[project]\nname = "worker"\n', encoding="utf-8")
    git(fresh, "add", "-A")
    git(fresh, "commit", "-q", "-m", "feat: worker")
    return fresh


class TestSetUpAnswer:
    """The first question a generated project cannot answer is what it is.

    Every answer start offered assumed the project already existed: change,
    bug-fix and explore all bind a work item to code that has not been written.
    The architect skill is documented as running after a signed project intent,
    and nothing created one, so the workflow that sets a project up had no door.
    """

    FRESH_OFFERS = [
        "set-up", "quick-change", "change", "bug-fix", "explore", "process-change", "opt-out",
    ]

    def test_set_up_is_offered_first(self, fresh: Path) -> None:
        assert start.offers(fresh)[0] == "set-up"

    def test_the_other_answers_remain(self, fresh: Path) -> None:
        assert start.offers(fresh) == self.FRESH_OFFERS

    def test_it_has_a_description(self, fresh: Path) -> None:
        assert start.ANSWERS["set-up"]

    def test_the_spec_readme_is_not_a_member(self, fresh: Path) -> None:
        """working/spec/README.md ships with the template; it describes no member."""
        assert (fresh / "working/spec/README.md").exists()
        assert "set-up" in start.offers(fresh)

    def test_an_app_retires_the_answer(self, established: Path) -> None:
        assert "set-up" not in start.offers(established)

    def test_a_spec_member_retires_the_answer(self, fresh: Path) -> None:
        (fresh / "working/spec/worker.md").write_text("# worker\n", encoding="utf-8")
        assert "set-up" not in start.offers(fresh)

    def test_it_creates_a_project_item(self, fresh: Path) -> None:
        assert start.main(["--answer", "set-up", "--ticket", "SETUP-1", fresh.as_posix()]) == 0
        st = state.read(fresh, "SETUP-1")
        assert st.workflow == "project"
        assert st.stage == "intent"
        assert st.branch == "SETUP-1"

    def test_it_drafts_an_intent(self, fresh: Path) -> None:
        start.main(["--answer", "set-up", "--ticket", "SETUP-1", fresh.as_posix()])
        text = (fresh / ".work/SETUP-1/intent.md").read_text(encoding="utf-8")
        assert "SETUP-1" in text
        assert "workflow: project" in text

    def test_it_drafts_from_the_shipped_template(self, fresh: Path) -> None:
        """The skill's template is the one source; the script does not carry a second."""
        tpl = fresh / start.PROJECT_INTENT_TEMPLATE
        tpl.parent.mkdir(parents=True)
        tpl.write_text(
            "# Intent: <title>\nid: <work-id>\nworkflow: project\n\n## Members\n",
            encoding="utf-8",
        )
        start.main(["--answer", "set-up", "--ticket", "SETUP-1", fresh.as_posix()])
        text = (fresh / ".work/SETUP-1/intent.md").read_text(encoding="utf-8")
        assert "## Members" in text
        assert "<work-id>" not in text and "<title>" not in text

    def test_it_names_the_next_two_steps(
        self, fresh: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        start.main(["--answer", "set-up", "--ticket", "SETUP-1", fresh.as_posix()])
        out = capsys.readouterr().out
        assert "/intent" in out and "/architect" in out

    def test_it_needs_a_ticket(self, fresh: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert start.main(["--answer", "set-up", fresh.as_posix()]) == 1
        err = capsys.readouterr().err
        assert "BLOCKED" in err and "ticket" in err, err
        assert not (fresh / ".work").exists()

    def test_it_is_not_offered_once_bound(self, fresh: Path) -> None:
        start.main(["--answer", "set-up", "--ticket", "SETUP-1", fresh.as_posix()])
        assert start.offers(fresh) == ["continue", "abandon"]


class TestProcessChangeAnswer:
    """Changing the process is itself work, and it needs an item to be reviewable.

    The protected-path guard tells the agent to hand the edit to the engineer. That
    is the right answer for a stray edit and the wrong one for deliberate work on
    the process, which then had no route at all: no item, no branch, no pull
    request. process-change opens one.
    """

    def test_it_is_offered_on_a_clean_branch(self, established: Path) -> None:
        assert "process-change" in start.offers(established)

    def test_it_is_offered_on_a_fresh_project_too(self, fresh: Path) -> None:
        assert "process-change" in start.offers(fresh)

    def test_it_is_not_offered_while_an_item_is_bound(self, established: Path) -> None:
        start.main(["--answer", "change", "--ticket", "PROJ-1", established.as_posix()])
        assert "process-change" not in start.offers(established)

    def test_it_has_a_description(self, established: Path) -> None:
        assert start.ANSWERS["process-change"]

    def test_it_creates_a_project_item(self, established: Path) -> None:
        code = start.main(
            ["--answer", "process-change", "--ticket", "PROC-1", established.as_posix()]
        )
        assert code == 0
        st = state.read(established, "PROC-1")
        assert st.workflow == "project"
        assert st.stage == "intent"

    def test_it_drafts_from_the_process_template(self, established: Path) -> None:
        tpl = established / start.PROCESS_INTENT_TEMPLATE
        tpl.parent.mkdir(parents=True, exist_ok=True)
        tpl.write_text(
            "# Intent: <title>" + chr(10) + "id: <work-id>" + chr(10)
            + "workflow: project" + chr(10) + chr(10) + "## Which rule" + chr(10),
            encoding="utf-8",
        )
        start.main(["--answer", "process-change", "--ticket", "PROC-1", established.as_posix()])
        text = (established / ".work/PROC-1/intent.md").read_text(encoding="utf-8")
        assert "## Which rule" in text
        assert "<work-id>" not in text

    def test_it_needs_a_ticket(
        self, established: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert start.main(["--answer", "process-change", established.as_posix()]) == 1
        assert "ticket" in capsys.readouterr().err
