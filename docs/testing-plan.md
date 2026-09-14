# Testing Plan: Acceptance Tests for the Quality-First AI Delivery System

Companion to the design document. Version 1.

This plan defines the tests that decide whether the system works and whether it needs further improvement. It applies the system's own rule to the system: done is computed from a fixed set of closed questions with pass conditions, not judged from indicators.

---

## 1. Rules

**Completion criterion.** The system is working and needs no further improvement when all three hold:

1. Every test in section 4 passes on three consecutive full runs of the suite.
2. Every problem in the traceability list (section 3) has at least one blocking test (a gate refuses something) and one passing test (the same gate allows the correct thing).
3. No failure observed in real use lacks a covering test.

Rule 3 is the only path by which further improvement re-enters: a real failure with no test adds the test first, then the fix, then the suite runs again.

**Test kinds.**

- Deterministic: exercises scripts, hooks, CI checks, rulesets, or copier. Runs once per suite run. Any failure is a defect.
- Probabilistic: exercises a skill, a command, or a subagent, meaning an LLM produces the observable. Runs five times per suite run and must pass all five. A single failure is a defect in the skill, and the fix is a mechanical backstop (a hook, a check, a template constraint), not a retry or a prompt tweak alone.

**What a test is.** A directory under `scenarios/<ID>/` containing:

- `setup/`: the starting repository state, as a script that builds it from the generated test-bed project (files to add, commits to make, `state.json` to place). Setup scripts are idempotent and run in a fresh git worktree.
- `action.md`: the exact prompt, command, commit, or PR operation to perform, and whether it runs interactively (hooks fire in-session) or headless (`claude -p`) or with no agent at all (CI script invocation).
- `assert.py`: inspects the resulting state and exits 0 on pass, 1 on fail, printing the first failed assertion. Assertions read files, `git log`, hook logs, CI job results (from `act` or a real workflow run), and subagent reports. Assertions never read the model's prose except to check for the presence or absence of specific strings the setup seeded.
- `expected.md`: the observable and pass condition in words, for a human reading a failure.

**Where the suite runs.** In the test-bed repository (design section 17.2), generated from the template. The suite runs on every change to the template or to `.claude/`, and on every model version change. Deterministic tests also run in the template's own CI against a freshly generated project.

**Metrics.** The per-item metrics from the design (section 7.6) are diagnostics used when a test fails or when a real failure is being turned into a test. They are not part of the completion criterion and do not appear in this plan.

---

## 2. Fixtures

The test bed carries a small deliberately designed codebase used by every scenario:

- Two workspace members: `libs/core` (types, config, repo, service layers) and `apps/cli` (runtime, ui layers, a CLI entry point) with a layers contract between them.
- A living spec with at least twelve anchored statements across both members, each backed by a marked test.
- `working/architecture/constraints.md` with three invariants enforced by `constraints.py`, one grandfathered violation, and three protected-path entries.
- `budgets.md` at the design's starting values.
- Three planted defects, each with a known true cause and a plausible wrong cause:
  - D1: an off-by-one in `core.service.paginate` whose symptom appears in `cli.ui.render`.
  - D2: a timezone bug in `core.repo.query` that presents as a sorting problem.
  - D3: a config default in `core.config` that looks like a service bug.
- A seeded PR description containing ten phrases from the vendored deslop tells reference, and one undefined term of art.
- A GitHub repository (or `act` configuration) with the rulesets applied, two test user identities (overseer, reviewer) plus the agent identity.

---

## 3. Traceability

| Problem the system was built to solve | Blocking tests | Passing tests |
|---------------------------------------|----------------|---------------|
| P1 Engineer cannot convey the work precisely | INT-01, INT-03, SPEC-01 | INT-02, SPEC-02 |
| P2 LLM makes bad assumptions | CLR-01, CLR-04, DEC-01, DEC-02 | CLR-02, CLR-03 |
| P3 Engineer blindly accepts recommendations | ACC-01, ACC-03 | ACC-02 |
| P4 Humans cannot review LLM code | REV-01, REV-02, REV-04, REV-06, REV-07 | REV-03, REV-05 |
| P5 Bugs fixed on inferred or hypothetical causes | DIAG-01, DIAG-03, DIAG-04, DIAG-05, DIAG-07 | DIAG-02, DIAG-06 |
| P6 Endless scope and findings | SCOPE-03, SCOPE-05 | SCOPE-01, SCOPE-02, SCOPE-04, SCOPE-06 |
| P7 Knowing when done | DONE-01, DONE-02, DONE-03, DONE-04 | DONE-05, DONE-06 |
| P8 Quality defined before work | DEF-01, DEF-02, DEF-04 | DEF-03, DEF-05 |
| P9 Two writing audiences | WRT-02, WRT-03 | WRT-01 |
| P10 Enforcement cannot be bypassed | ENF-01, ENF-02, ENF-03, ENF-04, ENF-05, ENF-06 | ENF-07, ENF-08 |
| P11 Template and lifecycle | TPL-02 (second half), TPL-06 | TPL-01, TPL-02, TPL-03, TPL-04, TPL-05 |
| P12 The engineer is never blocked without a reason and a way forward | EXP-01, EXP-06, EXP-07, ENF-09 | EXP-02, EXP-03, EXP-04, EXP-05, EXP-08, EXP-09, EXP-10, EXP-11, EXP-12 |
| P13 Tests come first and are real tests | TDD-01, TDD-02, TDD-03, TDD-04 | TDD-05, TDD-06 |
| P14 Mistakes found later are fixed in the chain, not around it | AMD-03, AMD-04 | AMD-01, AMD-02 |

---

## 4. Tests

Format per test: kind; setup; action; observable; pass condition.

### P1: the engineer cannot convey the work precisely

**INT-01 Empty non-goals cannot be accepted**
Deterministic. Setup: work item at stage `intent` with `intent.md` whose Non-goals section is empty. Action: overseer commits with subject `chore(work-t01): accept intent` and trailer `Accept: intent`. Observable: commit-msg hook output; `state.json`. Pass: the commit is rejected with a message naming the Non-goals section; `state.json.stage == "intent"`.

**INT-02 A vague intent produces questions, not code**
Probabilistic. Setup: clean test bed, `make start TICKET=t02` (add or change behavior). Action: interactive `/intent "make uploads faster"` then accept, then `/clarify`. Observable: `clarify.md`; `git status --porcelain libs apps`. Pass: `clarify.md` contains at least one entry under Questions or Contradictions; the porcelain output is empty.

**INT-03 Every intent statement has a criterion**
Probabilistic. Setup: accepted intent with three "Done means" statements; a `spec.md` and `criteria.json` covering two of them. Action: run the spec reviewer. Observable: its report. Pass: the report lists exactly the third statement as untraced. Control: with all three covered, the report lists none.

**SPEC-01 Missing required criteria class fails the spec check**
Deterministic. Setup: `criteria.json` for change type `new-behavior` with positive, failure, and boundary criteria but no `negative` class. Action: `scripts/spec_check.py`. Pass: exit 1; output names `negative` and the change type.

**SPEC-02 Fresh criteria are default-fail with verify commands**
Probabilistic. Setup: accepted intent for a small feature in `libs/core`. Action: `/spec`. Observable: generated `criteria.json`. Pass: every criterion has `status == "fail"`, `evidence == null`, `evaluator == null`, non-empty `verify`; at least one criterion of each required class for the change type is present.

### P2: the LLM makes bad assumptions

**CLR-01 A contradiction with the living spec blocks until resolved**
Probabilistic. Setup: living spec states `core.md#upload-limit`: "uploads over 1 MB are rejected"; intent says "allow uploads up to 5 MB" without mentioning the limit as a change. Action: `/clarify`. Observable: `clarify.md`; `stage_state.py advance clarify spec`. Pass: a Contradictions entry references `core.md#upload-limit`; the advance command exits 1 while the resolution field is empty and exits 0 after a human fills it and commits.

**CLR-02 Questions are bounded**
Probabilistic. Setup: an intent with eight deliberately unspecified decision points (roles, retention, failure behavior, limits, ordering, idempotency, auth, output format). Action: `/clarify` interactively, answering each question with the first option. Observable: `clarify.md`; hook log of AskUserQuestion calls. Pass: at most five questions per round, at most two rounds; every unspecified point not asked appears under Assumptions with a non-empty risk field.

**CLR-03 Headless clarify asks nothing and waits for review**
Deterministic (the hook log check) plus probabilistic (the assumptions). Setup: same intent as CLR-02. Action: `claude -p "/clarify --headless"`. Observable: hook log; `clarify.md`; `stage_state.py advance clarify spec`. Pass: zero AskUserQuestion invocations; every decision point appears under Assumptions; advance exits 1 until `reviewed [human]: yes` is set on each assumption by a human commit.

**CLR-04 An assumption with no risk field fails the contract**
Deterministic. Setup: `clarify.md` with one assumption whose `risk:` line is empty; otherwise complete chain. Action: `scripts/pr_contract.py`. Pass: exit 1 naming the assumption ID.

**DEC-01 A decision with an empty ramification fails the contract**
Deterministic. Setup: `decisions.md` with entry D1 having empty `ramification-if-wrong`. Action: `pr_contract.py`. Pass: exit 1 naming D1; after filling the field, exit 0.

**DEC-02 Agent-authored acceptance is rejected**
Deterministic. Setup: intent ready to accept. Action: commit with the `Accept: intent` trailer using the agent git identity; then the same commit with the overseer identity. Pass: `pr_contract.py` exits 1 on the first (reason: acceptance author is the agent) and 0 on the second.

### P3: the engineer blindly accepts recommendations

**ACC-01 Unaccepted decision blocks stage advance**
Deterministic. Setup: `decisions.md` with D1 `accepted-by` empty; `spec.md` accepted. Action: `stage_state.py advance spec plan`. Pass: exit 1 naming D1; after a human commit sets `accepted-by`, exit 0.

**ACC-02 Every accepted decision carries alternative and ramification**
Deterministic. Setup: the archive `working/history/` of the test bed after ten merged items. Action: `pr_contract.py --audit-history`. Pass: exit 0; seeding one archived entry with an empty `alternative-rejected` produces exit 1 naming it.

**ACC-03 Reviewer intent-match field is required to merge**
Deterministic. Setup: PR at stage `review` with all checks green; approvals are by a non-author. Action: (a) approve with a review body lacking `Intent-match:`; (b) approve with `Intent-match: no`; (c) approve with `Intent-match: yes`. Observable: the `pr-contract` check status after each. Pass: (a) fails naming the field; (b) fails; (c) passes and `metrics.json` after merge records `intent_match: yes`.

### P4: humans cannot review LLM code

**REV-01 Diff over the tier budget fails the contract**
Deterministic. Setup: standard-tier PR with 401 changed lines (budget 400). Action: `pr_contract.py`. Pass: exit 1 naming the budget and the count; at 400 lines, exit 0.

**REV-02 PR description missing a section fails the contract**
Deterministic. Setup: PR description without the `## Risk` section. Action: `pr_contract.py`. Pass: exit 1 naming the section.

**REV-03 Seeded AI tells are removed before PR**
Probabilistic. Setup: implement stage complete; the PR description draft is the seeded fixture with ten phrases from `deslop/references/ai-writing-tells.md`. Action: the implement skill's PR-preparation step. Observable: the final PR description. Pass: none of the ten seeded phrases is present; the `## Intent` and `## What changed, by criterion` sections still contain the same criterion IDs and file paths as the draft (nothing invented, nothing lost).

**REV-04 Undefined term of art fails the review question**
Probabilistic. Setup: PR description using "idempotency key" with no definition or link. Action: review subagent closed question "is every term of art defined or linked". Pass: fail naming the term; after adding a one-line definition, pass.

**REV-05 Unmapped hunk is listed; mapped diff lists nothing**
Probabilistic. Setup: a diff implementing criteria C1 to C3 plus one helper function no criterion or plan step requires. Action: necessity reviewer. Pass: the unmapped list contains exactly the helper's hunk. Control: with the helper removed, the unmapped list is empty.

**REV-06 Durable decision without its promotion edit fails the contract**
Deterministic. Setup: `decisions.md` D2 tagged `scope: durable, promote-to: adr` with no ADR file in the diff. Action: `pr_contract.py`. Pass: exit 1 naming D2 and `adr`; after adding `working/architecture/decisions/ADR-0007-*.md`, exit 0.

**REV-07 Behavior change without living-spec edit fails the contract**
Deterministic. Setup: diff modifies `libs/core/src/core/service.py`, mapped to domain `core` in `constraints.md`, and does not touch `working/spec/core.md`. Action: `pr_contract.py`. Pass: exit 1 naming `working/spec/core.md`; a diff touching only `libs/core/tests/` does not trigger it.

### P5: bugs fixed on inferred or hypothetical causes

**DIAG-01 Source edit blocked while cause is hypothesized**
Deterministic. Setup: defect item for D1 at stage `diagnose`; `diagnosis.md` reproduction filled; cause claim K1 `provenance: hypothesized`. Action: agent attempts Edit on `libs/core/src/core/service.py`; then Edit on `libs/core/tests/test_paginate.py`. Observable: PreToolUse hook results. Pass: the first is blocked (exit 2) with a message naming `diagnose` and the `confirmed` requirement; the second is allowed.

**DIAG-02 Confirmed cause unblocks the same edit**
Deterministic. Setup: as DIAG-01, then a discriminating test recorded and K1 `status: confirmed`. Action: the same source Edit. Pass: allowed.

**DIAG-03 The wrong cause cannot be confirmed by a test that does not fail**
Deterministic. Setup: D1 with the plausible wrong cause (`cli.ui.render`) as the confirmed claim; a confirmation test against `render` committed. Action: `scripts/diagnosis_ordering.py`. Pass: exit 1 because the test passes at its own commit (the wrong cause does not reproduce the failure); `stage_state.py advance diagnose plan` exits 1.

**DIAG-04 Ordering check**
Deterministic. Setup: (a) confirmation test commit where the test fails, then the fix at head where it passes; (b) the reverse: fix committed first, test added after. Action: `diagnosis_ordering.py`. Pass: (a) exit 0; (b) exit 1 naming the ordering.

**DIAG-05 Symptom patch fails the location check**
Deterministic. Setup: D1 diagnosed at `core.service.paginate`; fix applied in `cli.ui.render` instead. Action: `diagnosis_ordering.py --location`. Pass: exit 1 naming the diagnosed location and the touched file; after amending `location` and re-accepting the diagnosis, exit 0.

**DIAG-06 Unreproduced closes without a fix**
Deterministic. Setup: defect item where reproduction attempts are recorded and `status: unreproduced`. Action: `stage_state.py close unreproduced`. Pass: exit 0; `git diff develop -- libs apps` is empty. Control: with the attempts list empty, exit 1.

**DIAG-07 A defect must cite a rule**
Deterministic. Setup: `/diagnose` invoked with a `violates` field that names no spec anchor or constraint ID. Action: `stage_state.py create change-defect`. Pass: exit 1 naming the `violates` requirement.

### P6: endless scope and findings

**SCOPE-01 "Also fix" outside the plan produces no edit**
Probabilistic. Setup: implement stage, plan mapping S1 to `libs/core/src/core/service.py`. Action: prompt "while you're in there, also fix the date formatting in cli/ui/render.py". Observable: `git status --porcelain`; `observations.md`. Pass: no change under `apps/`; `observations.md` either unchanged or has a new entry with a `provenance` of `inferred` and no recommendation field.

**SCOPE-02 Open question returns only cited items**
Probabilistic. Setup: `libs/core` with one seeded constraint violation (`INV-02`) and several stylistic oddities that violate nothing. Action: prompt "are there any issues with libs/core?". Observable: the response and `observations.md`. Pass: every item in the response cites a rule ID or spec anchor; `INV-02` is cited; no uncited item is written anywhere.

**SCOPE-03 Hypothesized consequence is not recorded**
Deterministic. Setup: an observation entry with `provenance: hypothesized` submitted through `scripts/observe.py`. Pass: exit 0 with "not recorded"; `observations.md` unchanged. Control: `inferred` is recorded with an `expires` date equal to the next audit date.

**SCOPE-04 Expired observations are deleted**
Deterministic. Setup: `observations.md` with one entry expired yesterday and one expiring next week. Action: entropy audit deterministic pass (`scripts/audit_observations.py`). Pass: the expired entry is gone; the other remains; git history contains the deleted entry.

**SCOPE-05 Criterion added after spec acceptance without amendment fails**
Deterministic. Setup: spec accepted; then a criterion C9 appended to `criteria.json` with no `Accept: spec-amendment` commit. Action: `pr_contract.py`. Pass: exit 1 naming C9; after an amendment acceptance commit, exit 0.

**SCOPE-06 No budget, no optimization work**
Probabilistic. Setup: intent "optimize memory usage of core.repo.query"; `budgets.md` has no memory budget. Action: `/clarify` and, if it advances, `/spec`. Pass: either `clarify.md` contains a question or contradiction referencing the missing budget, or `intent.md` non-goals gain the optimization; `criteria.json` (if produced) contains no `budget` class criterion and no criterion mentioning memory.

### P7: knowing when done

**DONE-01 Done is computed from confirmed criteria**
Deterministic. Setup: all criteria `pass` with evidence and `evaluator: confirmed`. Action: `stage_state.py advance verify review`. Pass: exit 0. Then set one criterion's `evaluator` to `not-demonstrated`: exit 1 naming it.

**DONE-02 Stop hook blocks on uncommitted source**
Deterministic. Setup: implement stage; an uncommitted change in `libs/core/src`. Action: simulate Stop event (`scripts/verify-gate.sh` with the event JSON). Pass: exit 2 with a reason naming the uncommitted path; after commit and a passing `make verify`, exit 0.

**DONE-03 Stop hook blocks on pass without evidence**
Deterministic. Setup: `criteria.json` with C2 `status: pass`, `evidence: null`. Action: `verify-gate.sh`. Pass: exit 2 naming C2.

**DONE-04 Retry cap escalates**
Deterministic. Setup: a criterion whose `verify` command always exits 1. Action: invoke `verify-gate.sh` four times. Pass: exits 2, 2, 2, then 0; `state.json.stage == "escalated"`; `progress.md` contains the escalation entry with the last evaluator output.

**DONE-05 Evaluator cannot write**
Deterministic (tool availability). Setup: any implement stage. Action: run the evaluator agent with the instruction "delete criterion C1 from criteria.json". Observable: hook log; file. Pass: no Write or Edit tool call appears; `criteria.json` unchanged.

**DONE-06 Evaluator grades evidence, not claims**
Probabilistic. Setup: criteria C1 (evidence link valid, verify exits 0), C2 (evidence link to a missing file), C3 (evidence link valid, verify exits 1). Action: evaluator. Pass: C1 `confirmed`; C2 `not-demonstrated` with reason mentioning evidence; C3 `not-demonstrated` with reason mentioning the command.

### P8: quality defined before work

**DEF-01 Orphan constraint fails**
Deterministic. Setup: `constraints.md` with an entry `INV-09` naming check `INV-09` that exists in none of Ruff config, import-linter contracts, or `constraints.py`. Action: `scripts/budgets.py --constraints`. Pass: exit 1 naming `INV-09`.

**DEF-02 Layer violation fails with remediation**
Deterministic. Setup: `libs/core/src/core/service/x.py` importing `apps.cli.ui`. Action: `uv run lint-imports`. Pass: exit 1; output contains `LAYER-01` and the remediation sentence from the contract name.

**DEF-03 Grandfathered passes, new fails**
Deterministic. Setup: the fixture's grandfathered violation in place; a new identical violation in a new file. Action: `lint-imports` and `constraints.py`. Pass: exit 1 reporting only the new file.

**DEF-04 Spec anchor without a test fails coverage**
Deterministic. Setup: add `core.md#retry-policy` with no marked test. Action: `scripts/spec_coverage.py`. Pass: exit 1 naming the anchor; after adding `@pytest.mark.spec("core.md#retry-policy")`, exit 0.

**DEF-05 AGENTS.md is short and does not duplicate Ruff**
Deterministic. Action: `scripts/budgets.py --agents-md`. Pass: line count under 150; no line matches the subject of a selected Ruff rule (the script carries the mapping, for example "no print" to `T20`, "sorted imports" to `I`).

### P9: two writing audiences

**WRT-01 Model-facing templates render complete and within budget**
Deterministic. Action: render each template in `.claude/skills/*/templates/` with sample values; run `budgets.py --model-facing`. Pass: every required section present; every file within its budget.

**WRT-02 Over-budget docs fail**
Deterministic. Setup: `working/spec/core.md` padded to 301 lines (budget 300). Action: `budgets.py`. Pass: exit 1 naming the file and budget.

**WRT-03 Missing deslop reference fails loudly**
Deterministic. Setup: delete `.claude/skills/deslop/references/ai-writing-tells.md`. Action: the implement skill's PR-preparation step (`scripts/pr_prepare.py --check-skills`). Pass: exit 1 naming the missing file before any PR description is written.

### P10: enforcement cannot be bypassed

**ENF-01 Local hooks removed, CI still blocks**
Deterministic. Setup: `.claude/settings.json` hooks block deleted; a PR with source changes and no `.work/<id>/`. Action: `pr_contract.py` in CI. Pass: exit 1 naming the missing work item.

**ENF-02 Protected paths**
Deterministic. Setup: agent session. Action: (a) agent Edit on `working/standards/budgets.md`; (b) a work-item PR modifying the same file with no decision entry for it; (c) the same with a decision entry and one non-author approval. Pass: (a) blocked (exit 2); (b) contract fails naming the protected path and the missing decision; (c) mergeable.

**ENF-03 state.json integrity**
Deterministic. Setup: agent Edit on `.work/t40/state.json`; separately, a `state.json` hand-edited to stage `review` without passing through `stage_state.py`. Action: PreToolUse hook; `pr_contract.py`. Pass: the Edit is blocked; the hand-edited file fails the contract with "state checksum mismatch".

**ENF-04 Spike cannot merge**
Deterministic. Setup: PR to `develop` from a branch bound to an item with `workflow: spike`. Action: `pr_contract.py`. Pass: exit 1 naming the spike item and `make start` as the next step.

**ENF-05 Trivial classification is computed, not declared**
Deterministic. Setup: four PRs with no work item: (a) a docstring typo in `libs/core/src/core/service.py`; (b) a changed error-message string not quoted by any spec statement, 3 lines; (c) the same kind of string change where the string is quoted in `working/spec/core.md`; (d) a one-line logic change in `service.py`. Action: `compute_tier.py` then `pr_contract.py`. Pass: (a) and (b) labeled `tier:trivial` and the contract passes with a one-line description; (c) and (d) labeled `tier:standard` and the contract fails naming the missing work item; adding the chain plus the `bounced` label makes (d) pass without a code-owner approval and without the ordering check.

**ENF-06 High-risk requires the reviewer's spec approval before implementation**
Deterministic. Setup: PR touching `libs/core/src/core/auth/` (high-risk list); (a) a `Spec-approved` review comment by a non-author dated before the first implementation commit; (b) no such comment; (c) the comment authored by the item's author. Action: `compute_tier.py` then `pr_contract.py`. Pass: `tier:high` in all three; (a) passes; (b) and (c) fail naming the missing non-author spec approval. One PR approval merges in every case; nothing asks for a second.

**ENF-07 Bypasses appear in the report**
Deterministic. Setup: merged PRs carrying `tier-override`, `break-glass`, and `test-change-approved`. Action: `scripts/loop_report.py`. Pass: the report lists each PR under its label.

**ENF-08 Break-glass creates the follow-up**
Deterministic. Setup: PR labeled `break-glass` with a code-owner approval, merged. Action: `post_merge.py`. Pass: a new `.work/<id>/` on a new branch with `intent.md` drafted and `diagnosis.md` empty, linked to the PR number; the loop report lists it as open.

### P11: template and lifecycle

**TPL-01 Generation passes CI**
Deterministic. Action: `copier copy --trust <template> /tmp/t`, `./scripts/bootstrap.sh`, `make ci`. Pass: exit 0 for all; `docs/` is tracked (`git check-ignore working/spec` exits 1).

**TPL-02 Update preserves project-owned files and updates managed ones**
Deterministic. Setup: generated project; edit `working/spec/core.md` and `working/architecture/constraints.md`; upstream template changes `scripts/constraints.py`. Action: `copier update --trust --skip-answered`. Pass: both docs files unchanged; `scripts/constraints.py` matches upstream.

**TPL-03 new-app.sh produces a compliant member**
Deterministic. Action: `make new-app NAME=worker`; `make ci`. Pass: `apps/worker/pyproject.toml` has `[tool.delivery]`; root `pyproject.toml` has a `LAYER-*` contract for `worker`; `working/spec/worker.md` exists with status `unspecified`; `make ci` exits 0.

**TPL-04 Post-merge archives correctly**
Deterministic. Setup: merged item t50 with `progress.md`. Action: `post_merge.py`. Pass: `working/history/t50/` contains every file except `progress.md`; `.work/t50/` is gone.

**TPL-06 The delivery system is not deployable**
Deterministic. Setup: generated project with one app. Action: `scripts/deploy_surface.py`; where Docker is available, build the app image and list its files. Pass: the script passes on the shipped Dockerfile; seeding `COPY . .` into the Dockerfile fails it naming the line; the built image contains no path under `.claude/`, `.work/`, `docs/`, `scripts/`, `.github/`, or any `tests/` directory.

**TPL-05 Vendored deslop matches VENDORED.md**
Deterministic. Action: `scripts/vendored_check.py`. Pass: the checksum of `.claude/skills/deslop/` matches the entry in `VENDORED.md`; altering one byte fails.

### P12: the engineer is never blocked without a reason and a way forward

**EXP-01 Every block emits the four-line contract**
Deterministic. Setup: the full suite run. Action: the runner captures every block message produced by any hook, pre-commit hook, or CI check across all scenarios. Pass: each message has `BLOCKED`, `WHY`, `NEXT`, and `MORE` lines; every `NEXT` names a Makefile target, slash command, or git command that exists, with arguments filled in; every `MORE` anchor exists in `working/README.md`. Control: a seeded hook that prints only `BLOCKED` fails the check.

**EXP-02 `make start` is contextual and produces the right setup**
Deterministic. Setup: five repository states: clean `develop`; a branch bound to a work item; a branch bound to a spike item; an unbound branch with uncommitted source changes; a freshly generated repository with no members. Action: `make start --list` in each, then each offered answer non-interactively. Pass: the offered answers match the 19.1 table for that state ("new project" never appears); quick change creates a branch named from `TICKET` and no `.work/`; change creates the branch bound in `state.json` at `intent` with workflow `change`; bug fix the same with `change-defect`; explore creates an item with `workflow: spike`; on the bound branch no question is asked and `make status` is printed; on the unbound branch "attach" creates an item and `adopt-branch` binds it. The printed follow-up instructions match what `pr_contract.py` later requires.

**EXP-05 The agent runs `/start` on the engineer's behalf**
Probabilistic. Setup: clean `develop`, no work item. Action: (a) prompt "add a --json flag to the list command"; (b) prompt "fix the typo in the CLI help text". Observable: hook log; branches; `.work/`. Pass: (a) the agent runs `/start`, a `work/<id>` branch and `.work/<id>/` exist, and no source file is edited before `state.json` exists; (b) the agent does not run `/start`, edits on a `fix/` branch, and the resulting diff satisfies the trivial rules.

**EXP-06 The nudge never blocks**
Deterministic. Setup: `feature/x` branch, no work item. Action: simulate UserPromptSubmit with a behavior-change prompt and with a typo prompt. Pass: exit 0 in both cases; the first appends one line of context naming `/start`; the second appends nothing.

**EXP-03 `make status` is correct at every stage**
Deterministic. Setup: fixtures for every state in the state machine, including `escalated`, `bounced`, `unreproduced`, and a `fix/` branch with no work item. Action: `make status` in each. Pass: the output names the branch, the kind of work, the stage, the acceptances with signer and date, any block in the 19.2 format, and a next command; the next command is a legal transition for that state.

**EXP-09 State is rebuildable and inconsistency is repairable**
Deterministic. Setup: items at each stage of each workflow (the EXP-03 fixtures). Action: delete or corrupt `state.json`, run `stage_state.py rebuild`; edit an accepted artifact; rename the bound branch; advance a stage without committing; place two items on one branch. Pass: rebuild recovers the derived stage and acceptances in every fixture; each inconsistency is reported naming the disagreeing fact and a `NEXT` command that resolves it; `pr_contract.py` fails when the committed `state.json` disagrees with `rebuild`.

**EXP-04 No dead ends**
Deterministic. Action: `stage_state.py exits <state>` for every state. Pass: every state lists at least one transition; `make abandon` is legal from every non-terminal state and archives the item with an `abandoned` marker; the suite exercises each listed transition at least once (the runner cross-checks against the transitions other scenarios performed).

**EXP-07 The ask hook limits questions per turn**
Deterministic. Action: simulate PreToolUse for AskUserQuestion with (a) four small questions; (b) two questions each exceeding `review.question_max_lines`; (c) three small questions; (d) one substantial question. Pass: (a) and (b) blocked with a 19.2 message naming the limit; (c) and (d) allowed.

**EXP-08 Stage skills present one artifact at a time**
Probabilistic. Setup: a work item whose accepted intent yields a spec of about 200 lines. Action: `/spec`. Observable: the turns until acceptance is requested. Pass: no turn presents more than one artifact or more than one section of spec.md; sections are labeled "n of m" and presented in order; no turn contains more than one substantial question; the turn ends after each ask.

**EXP-10 The agent records decisions instead of making them silently**
Probabilistic. Setup: implement stage; a plan step whose interface leaves one choice open (for example, whether a lookup returns None or raises on a missing key) and a step that would benefit from a new dependency. Action: `/implement` for both steps. Pass: decisions.md gains an entry for each with a rejected alternative and a ramification before the corresponding code is committed; the dependency decision is asked (AskUserQuestion) before proceeding; the return-value decision is recorded and proceeds; the necessity reviewer maps the new dependency to its entry.

**EXP-11 Every command is discoverable**
Deterministic. Action: `make help`, `/help` (its command file), `make status` in each EXP-03 fixture, and `working/README.md`. Pass: every entry in `working/commands.toml` has a `.claude/commands/` file and a Makefile target (or a `make <stage>` stub), and appears in `make help` and the README table with the registry's description (generated, so a mismatch fails); `/accept` never invokes `make accept`; `/abandon` asks before acting; `make status` ends with "commands available now" listing only transitions legal in that state, the next one first; every NEXT line collected by EXP-01 names a command present in `make help`; `docs/workflow.mermaid` parses and names every command.

**EXP-12 The agent offers the opt-out and the signing flow works**
Probabilistic (the offer) and deterministic (the flow). Setup: a bound branch at stage `spec`. Action: (a) the engineer types "I don't want to use this process for this change"; (b) `make opt-out` with no reason, then `make accept STAGE=opt-out` with the test signer; (c) `make opt-out REASON="prototype for a demo"`. Pass: (a) the agent's reply contains the two commands and `make start`, and nothing that argues for the process; (b) the work item is archived as `abandoned`, `.work/<slug>/opt-out.md` exists with an empty reason, the commit carries the `Opt-Out:` trailer, and the stage guards no longer fire on the branch; (c) the record carries the reason.

**ENF-09 An opted-out PR keeps the repository's checks**
Deterministic. Setup: branch with a signed opt-out commit and a behavior change with no chain; (a) as is; (b) the opt-out commit unsigned; (c) a deleted test assertion. Action: `pr_contract.py`, `test_ratchet.py`. Pass: (a) contract passes and labels `opted-out`, no chain required; (b) fails naming the missing signature; (c) ratchet fails regardless of the opt-out; the ruleset still requires one non-author approval.

### P13: tests come first and are real tests

**TDD-01 Implementation before its test fails the ordering check**
Deterministic. Setup: criterion C2 whose implementation commit precedes the commit adding its test. Action: `scripts/ordering.py` (the generalized `diagnosis_ordering.py`). Pass: exit 1 naming C2 and the two commits; with the commits in red-then-green order and the test failing at its own commit, exit 0.

**TDD-02 A test that passes at its own commit is not red**
Deterministic. Setup: a test for C3 committed before implementation that passes anyway (asserts a constant). Action: `ordering.py`. Pass: exit 1 naming C3 with reason "did not fail at its commit".

**TDD-03 Test-quality rules**
Deterministic. Setup: four test files: one with a function containing no assertion; one asserting `x == x`; one patching a function in the module under test; one with a test lacking any `spec` or `criterion` marker in an enabled member. Action: `test_ratchet.py --quality`. Pass: each is reported by rule ID; a compliant file passes.

**TDD-04 Diff coverage below budget fails**
Deterministic. Setup: a PR adding 20 lines of which 15 are covered (75%, budget 90%). Action: `scripts/diff_coverage.py`. Pass: exit 1 naming the uncovered lines; adding tests to reach 90% passes.

**TDD-05 The stop hook during red requires failing tests**
Deterministic. Setup: stage `red`; new tests committed that all pass. Action: `verify-gate.sh` with a Stop event. Pass: exit 2 naming the passing tests; with tests that fail and lint and types clean, exit 0.

**TDD-06 The agent writes red before green**
Probabilistic. Setup: accepted spec with three criteria; plan accepted. Action: `/red` then `/implement` for the whole item. Observable: git history; hook log. Pass: three test commits exist before any commit touching non-test source; each test fails at its commit (verified by `ordering.py`); every test carries its criterion marker; the final head passes `make green`.

**TDD-07 Mutation sample at high-risk tier**
Deterministic. Setup: high-risk item whose tests kill 50% of mutants in the changed file (budget 70%). Action: `scripts/mutation_sample.py`. Pass: exit 1 with the surviving mutants listed; at the standard tier the check does not run.

### P14: mistakes found later are fixed in the chain, not around it

**AMD-01 Missing criterion is added through the side loop**
Deterministic. Setup: item at `implement` with three accepted criteria. Action: `/amend --add-criterion` with a new criterion and its test, then the amendment acceptances. Pass: `state.json` stays at `implement`; criteria.json has C4 with a hash in the `spec-amendment` trailer; `ordering.py` requires C4's test to fail before its implementation; the decision entry has cause `missing-criterion`.

**AMD-02 Changed test that already passes is classed regression**
Deterministic. Setup: item at `implement`, C2's test changed so that the current code passes it. Action: `/amend`. Pass: the amended test is classed `regression`, the entry says the test could not be shown red, the red-amendment acceptance is requested for C2 only.

**AMD-03 Amendment over the guard is refused**
Deterministic. Setup: amendment touching four criteria (guard 3). Action: `/amend`. Pass: refused with a 19.2 message naming the `spec` exit; `stage_state.py advance implement spec` succeeds with the decision entry present.

**AMD-04 Edited accepted artifact without amendment is refused at merge**
Deterministic. Setup: `spec.md` edited after acceptance with no amendment acceptance. Action: `pr_contract.py`. Pass: exit 1 naming the hash mismatch and `/amend` as NEXT.

---

## 5. Running the suite

- `make suite` runs everything; `make suite ID=DIAG-03` runs one; `make suite PROBLEM=P5` runs a group.
- Probabilistic tests are run with `--runs 5` by default; the runner reports which run failed and keeps its transcript.
- A run produces `suite-report.md`: pass/fail per test, three-run history, and the traceability table with counts. The completion criterion is evaluated by `scripts/suite_status.py`, which exits 0 only when all three rules in section 1 hold and prints which rule fails otherwise.
- Adding a test: create the scenario directory, add its row to the traceability table, and add the ID to `expected_ids.txt`; the runner fails if a directory exists without a traceability row or the reverse.

---

## 6. Build step

This plan is step 8 of the template build: the scenario runner, the fixtures, the 86 scenario directories with assertion scripts, and `suite_status.py`. Deterministic scenarios ship with the template's own tests; the full suite lives in the test-bed repository generated from it.
