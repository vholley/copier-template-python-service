# Decisions: template-v2

How to read this file: each decision answers five questions in plain words. Anyone
on the team should be able to restate a decision in one sentence after reading
it. "accepted-by" is the engineer who signed it and the date.

---

## D1: Everything ships in the copier template, not as a separate plugin

**What we decided.** The skills, hooks, and agents that make up the process live in `.claude/` inside the template, and copier installs and updates them like every other file.

**Why.** Copier already versions and updates everything in a generated project. A separate plugin would add a second thing to install, a second version to track, and a compatibility check between the two, for no benefit to projects that came from the template.

**What we considered instead.** A plugin repository with a marketplace. Kept as a later option for a repository that was not generated from the template.

**If this turns out to be wrong.** A repository not made from the template would have to copy `.claude/` by hand. If that becomes common, the plugin is extracted then; the skills themselves do not change.

**What it touches.** Everything under `template/.claude/`.

scope: durable → decision record · accepted-by: overseer, 2026-09-12

---

## D2: Signing off is a signed git commit; the agent is blocked from making one

**What we decided.** When an engineer accepts an intent, spec, or set of tests, they make a git commit signed with their SSH key. CI checks the signature on those commits only. In the Claude Code session, a hook refuses any `git commit` whose message contains an acceptance line, so the agent cannot make one.

**Why.** Inside a session the agent commits under the engineer's own name, so "who authored it" cannot tell a human sign-off from one the agent made. A signature can, as long as the key needs an action each time it is used.

**What we considered instead.** Checking the commit author (fails for the reason above). Checking for Claude's co-author trailer (we are removing that trailer). Accepting through the GitHub website (the agent can drive `gh` with the engineer's login). Requiring signed commits repository-wide (would block everyone's normal commits). Hardware keys (not available).

**If this turns out to be wrong.** If an engineer's key sits in their SSH agent with no prompt, the agent can sign from their shell. Then only the session hook and the engineer's own care remain. The setup script warns about that configuration. Attribution and the content hash still hold.

**What it touches.** `scripts/delivery/accept.py`, `pr_contract.py`, the Bash hook, the setup checklist.

scope: durable → decision record · accepted-by: overseer, 2026-09-12

---

## D3: `make green` fails when a member has no tests; `make test` still tolerates it

**What we decided.** Two Makefile targets with different jobs. `make test` runs the whole workspace and treats "no tests found" as a pass, so a brand-new project's CI is green on day one. `make green` runs per member that has opted into the process and treats "no tests found" as a failure.

**Why.** The process uses test results as evidence that work is done. If "no tests" counted as green, a member with zero tests could be marked finished.

**What we considered instead.** Making `make test` strict everywhere. Rejected because a fresh project with no code would fail CI immediately.

**If this turns out to be wrong.** A member could be verified without tests only if `green` were ever routed through `test`. They are kept separate and `green` has its own tests.

**What it touches.** `Makefile`.

scope: local · accepted-by: overseer, 2026-09-12

---

## D4: The template's own tests include the deterministic scenarios

**What we decided.** Scenarios from the testing plan that need no live agent and no GitHub run inside the template repository's test suite, against a freshly generated project.

**Why.** Otherwise the scripts the template ships would be untested by the template's own CI.

**What we considered instead.** Keeping every scenario in the separate test-bed repository. Rejected for the reason above.

**If this turns out to be wrong.** Template tests get slower because they generate a project. They generate it once per test session and reuse it.

**What it touches.** `tests/`.

scope: local · accepted-by: overseer, 2026-09-12

---

## D5: Building the template follows the process's own rules where they apply

**What we decided.** Scripts are written tests-first (the test commit comes before the code commit), every block message goes through one shared helper, and `make green` runs after every step. Jinja templates, docs, and configuration are checked by generation tests instead, since tests-first does not apply to them.

**Why.** The design claims tests-first is enforceable. The first code the system produces should try it.

**What we considered instead.** Writing scripts and tests together and checking at the end.

**If this turns out to be wrong.** The build takes longer than a straight implementation. The step count in the plan makes that cost visible.

**What it touches.** How every commit on this branch is ordered.

scope: local · accepted-by: overseer, 2026-09-12

---

## D6: The agent prepares the acceptance commit; the engineer signs it

**What we decided.** `make accept-prepare STAGE=<stage>` (run by the agent) stages the item's files, computes their hashes, and writes the commit message. `make accept STAGE=<stage>` (run by the engineer in their own shell) checks the staged files still match, shows the message and a short diff, and runs `git commit -S`.

**Why.** A signature is part of the commit object, so there is no way to sign a commit after the agent has created it without creating a new commit. Splitting "prepare" from "sign" gives the agent the typing and the engineer the signature.

**What we considered instead.** The agent commits unsigned and the engineer amends with `-S`. That is still a new commit, and it would mean allowing agent-made acceptance commits, which removes the block that makes attempts visible.

**If this turns out to be wrong.** An engineer who signs without reading has still signed. The ramification field in each decision and the one-thing-at-a-time review rule exist to make reading likely; the mechanism cannot force it.

**What it touches.** `scripts/delivery/accept.py`.

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D7: The agent asks for review one thing at a time

**What we decided.** When the process needs a human's review or answer, it asks for one artifact (or one section of a long one), or one substantial question, or up to three small ones. Never more in a single turn.

**Why.** Presenting a whole set of documents at once produces shallow feedback on all of them. The overseer raised this after being asked to review everything at once.

**What we considered instead.** Presenting the full chain in one turn, which this build did once.

**If this turns out to be wrong.** More turns per stage. Accepted in exchange for feedback quality.

**What it touches.** Every stage skill; a hook on the agent's question tool; `AGENTS.md`.

scope: durable → `AGENTS.md` · accepted-by: overseer, 2026-09-13

---

## D8: `docs/` stays untracked; the process's own files live in `working/`

**What we decided.** `docs/` keeps the template's meaning: reference material generated by copier, not tracked by git, restored by a script. Everything the process reads and writes (the living spec, decision records, constraints, standards, history) lives in a tracked directory named `working/`.

**Why.** The overseer wants `docs/` untracked. The process needs its files versioned, and an untracked file is absent on a fresh clone until the restore script runs.

**What we considered instead.** Tracking `docs/`. Rejected by the overseer.

**If this turns out to be wrong.** Two text directories with different rules can confuse people. `working/README.md` states the split in its first lines, and every block message links into `working/`, never into `docs/`.

**What it touches.** The repository layout.

scope: durable → decision record · accepted-by: overseer, 2026-09-12

---

## D9: Default lists for "quick change" paths and "high risk" paths

**What we decided.** The template ships default path patterns: high-risk (`**/auth/**`, `**/migrations/**`) and quick-change-eligible (`docs/**`, `*.md`, `.github/**`, `**/tests/**`, `pyproject.toml`, `uv.lock`). Projects edit them in `working/standards/budgets.md`.

**Why.** A fresh project has nothing to base an answer on, so the template needs sensible defaults.

**What we considered instead.** Asking with no default.

**If this turns out to be wrong.** A path wrongly listed as quick-change lets behavior changes skip the process until the code-based checks catch them; a missing high-risk path loses the earlier spec review. Both lists are the project's to edit.

**What it touches.** `working/standards/budgets.md`, `copier.yaml`.

scope: local · accepted-by: overseer, 2026-09-13

---

## D10 (withdrawn)

Replaced by D16.

---

## D11: When the delivery system is switched off, its files are excluded by copier's exclude list

**What we decided.** Each delivery file has one line in `copier.yaml`'s `_exclude` list that applies when `enable_delivery` is false.

**Why.** Wrapping file contents in a Jinja conditional would still create empty files.

**What we considered instead.** Jinja conditionals inside each file.

**If this turns out to be wrong.** A new delivery file added without an exclude line would ship into projects that turned the system off. Test C01 catches that.

**What it touches.** `copier.yaml`.

scope: local · accepted-by: overseer, 2026-09-13

---

## D12: Every block message's "read more" link points into `working/README.md`

**What we decided.** The MORE line of a block message must start with `working/README.md#`. The helper refuses any other link.

**Why.** `docs/` is untracked and may be absent on a fresh clone (D8). A link that might not resolve is worse than none.

**What we considered instead.** Allowing any path.

**If this turns out to be wrong.** No other document can be a block's reference. If the README outgrows its budget, it links onward from there.

**What it touches.** `scripts/delivery/block.py`.

scope: durable → `AGENTS.md` · accepted-by: overseer, 2026-09-13

---

## D13: From "escalated", an item can go back to implementation, back to spec, or be abandoned

**What we decided.** When the stop hook has blocked three times and a human has to decide, the three legal moves are: back to implementation (after fixing the criterion or making the decision), back to spec (re-specify), or abandon.

**Why.** Without the "back to implementation" move, a one-line fix would cost a full re-acceptance of the spec, which is the kind of friction that makes people route around the process.

**What we considered instead.** Only "back to spec".

**If this turns out to be wrong.** An engineer could send an item back to implementation when the spec itself was wrong. The evaluator's report is shown at escalation and the reviewer sees the escalation in the PR.

**What it touches.** `scripts/delivery/state.py` (the transition table).

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D14: Abandoning an item archives it; nothing is deleted

**What we decided.** `make abandon` moves `.work/<id>/` to `working/history/<id>/` with the stage recorded as "abandoned" and drops the session notes file. The git branch is left alone.

**Why.** An abandoned intent is often the best record of why something was not done.

**What we considered instead.** Deleting the item's directory.

**If this turns out to be wrong.** History accumulates abandoned items. The weekly audit reports the count.

**What it touches.** `scripts/delivery/state.py`.

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D15: `state.json` is a cache that can always be rebuilt from git and the files

**What we decided.** Everything in `state.json` is derivable: sign-offs are signed commits, artifacts are files, criteria status is in `criteria.json`. `make rebuild` regenerates it; every read checks it against those sources and names the repair.

**Why.** Detecting a corrupt file without being able to repair it is a dead end.

**What we considered instead.** Treating `state.json` as the source of truth with only a checksum.

**If this turns out to be wrong.** If the rebuild logic and the recorded state were both wrong the same way, the CI cross-check would pass. The fixture-based tests (one per stage of each workflow) guard the rebuild logic.

**What it touches.** `scripts/delivery/state.py`.

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D16: Owners are optional; if given, GitHub auto-requests their review on process files

**What we decided.** `copier` asks for an optional `owner_group` (a team or user handle). If given, a CODEOWNERS file is generated so GitHub asks that group to review changes to process files. It adds no approval requirement. If empty, no file is generated.

**Why.** A template cannot know who is responsible for a project's process files, and the process never needs a specific person, only a second one. Auto-requesting review is still worth having as an option.

**What we considered instead.** A required owner question (a template cannot answer it). Requiring two approvals on process files (there is never a second approval, D17).

**If this turns out to be wrong.** With no owner group, process-file changes get the same single review as anything else and reviewers are picked by hand.

**What it touches.** `copier.yaml`, `.github/CODEOWNERS`.

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D17: One author and one reviewer, always; nothing ever needs two approvals

**What we decided.** Every pull request has one author and one approval from someone else. No path, risk level, or file type requires more. High-risk changes get more rigor by timing: the same reviewer approves the spec before implementation starts, and mutation testing runs.

**Why.** The overseer's rule.

**What we considered instead.** A second reviewer for high-risk changes.

**If this turns out to be wrong.** High-risk code gets one pair of eyes. The earlier spec review and the mutation sample compensate.

**What it touches.** Branch rules, `pr_contract.py`, the risk-tier logic.

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D18: Creating a work item creates its branch if it does not exist

**What we decided.** `state.create()` makes the branch the item binds to, when it is missing.

**Why.** Two approved tests create items on branches that do not exist yet, and `make start` creates the branch in the same step anyway.

**What we considered instead.** Failing when the branch is missing.

**If this turns out to be wrong.** A typo in a branch name silently creates a new branch. `make status` shows the bound branch, and the consistency check reports a mismatch if the engineer is on another one.

**What it touches.** `scripts/delivery/state.py`.

scope: local · accepted-by: overseer, 2026-09-13

---

## D19: Every constraint is written as one line that names the check enforcing it

**What we decided.** Lines in `working/architecture/constraints.md` look like `- INV-01 (check: constraints.py INV-01): text`. The check named must exist in Ruff's configuration, in an import-linter contract, or in `constraints.py`. A separate baseline file lists violations that existed at adoption; it may only shrink.

**Why.** A constraint with no mechanical check is a wish, not a constraint. Putting the check reference on the same line makes it impossible to write one without the other.

**What we considered instead.** Free prose with a separate table of checks.

**If this turns out to be wrong.** Rules that cannot be checked mechanically have no place in this file and go in the standards instead. That is the intended pressure.

**What it touches.** `working/architecture/constraints.md`, `scripts/delivery/budgets.py` (the orphan check).

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D20: Which criteria classes a spec needs is read from an editable table, not from code

**What we decided.** `spec_check.py` reads `working/standards/criteria-templates.md`, a table of change type to required classes, and fails a criteria file missing any of them.

**Why.** The criteria template is a quality definition the team edits. A copy in code would drift from it.

**What we considered instead.** A dictionary in the script.

**If this turns out to be wrong.** A malformed table would require nothing. The script fails closed when the table cannot be read or the change type is missing from it.

**What it touches.** `scripts/delivery/spec_check.py`.

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D21 (withdrawn)

The rule it excepted duplicated a Ruff rule. Replaced by D23.

---

## D22: Criteria are linked to their tests by a file, not by a marker on the test

**What we decided.** The link from a criterion to the tests that prove it is a file in the work item (see D29 for which file). Tests carry a marker naming the living-spec statement they prove, never a criterion id.

**Why.** Criteria ids are scoped to one work item and archived after merge; a marker like `criterion("C1")` would mean nothing in the codebase afterward and would collide across items.

**What we considered instead.** Discovering a criterion's tests from markers.

**If this turns out to be wrong.** A criterion whose list is empty cannot be checked for tests-first ordering; the ordering check treats that as a failure for any non-trivial change.

**What it touches.** `scripts/delivery/ordering.py`.

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D23: The example constraint is "read the environment only in the config module"

**What we decided.** `constraints.py` ships with one rule, `INV-01`: `os.environ` and `os.getenv` may be used only in a module named `config.py`. No exceptions.

**Why.** The previous example rule (no `print`) duplicated Ruff's `T20` and needed a special case for command-line tools. Configuration access is a boundary Ruff cannot express and that matters for these services.

**What we considered instead.** Keeping the no-print rule.

**If this turns out to be wrong.** Code that legitimately needs raw environment access lives outside the source trees or goes through config. That is the intended boundary.

**What it touches.** `scripts/delivery/constraints.py`; the C19 tests were amended to match.

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D24: The test ratchet identifies tests by the spec statement they prove, not by function name

**What we decided.** Assertions are counted per `@pytest.mark.spec("...")` marker across all tests that carry it. Renaming, splitting, or merging tests is not a finding as long as the assertions survive. A spec statement losing its last test is reported by name.

**Why.** Function names are the weakest identity available and tie the check to nothing the system cares about. The overseer called name matching flimsy.

**What we considered instead.** Name matching (first version). Similarity matching (thresholds cause both false passes and confusing messages).

**If this turns out to be wrong.** Two unrelated tests sharing a marker are compared as one. The spec-coverage check pushes toward one marker per statement.

**What it touches.** `scripts/delivery/test_ratchet.py`; the C22 tests were amended.

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D25: Diff coverage counts only lines that can execute

**What we decided.** Blank lines and comment-only lines in a diff are not counted when computing how much of the change the tests executed.

**Why.** Coverage tools never report those lines as executed, so counting them would make 100% unreachable.

**What we considered instead.** Counting every changed line.

**If this turns out to be wrong.** Nothing material; the script defers to the coverage report for edge cases like docstrings inside functions.

**What it touches.** `scripts/delivery/diff_coverage.py`.

scope: local · accepted-by: overseer, 2026-09-13

---

## D26: The only identity a test carries is the living-spec statement it proves

**What we decided.** Tests in members that use the process carry `@pytest.mark.spec("<file>.md#<anchor>")` and nothing else as identity. There is no criterion marker.

**Why.** See D22: criteria are temporary, spec statements are permanent.

**What we considered instead.** Keeping a criterion marker alongside.

**If this turns out to be wrong.** A test that proves behavior nobody has written into the living spec cannot be marked. That is the intended pressure: write the statement first.

**What it touches.** `test_ratchet.py` (rule TQ-04), fixtures in the C22 and C23 tests.

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D27: A member's living spec is the file with its name

**What we decided.** `libs/core` is described by `working/spec/core.md`. A pull request that changes anything under `libs/core/src` must also change that file.

**Why.** The one-file-per-member convention already exists (the new-app script creates it), and the PR contract needs to know which spec goes with which code.

**What we considered instead.** A separate manifest mapping paths to spec files. A second thing to keep in sync.

**If this turns out to be wrong.** A member with behavior described across several documents keeps them as sections of its one file. A pure refactor still has to touch the spec file, which is a prompt to confirm nothing changed; quick changes never reach this check.

**What it touches.** `scripts/delivery/pr_contract.py` (condition 08).

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D28: Signer identities from GitHub are email addresses

**What we decided.** When CI builds the list of who may sign from an organization's GitHub members, each member's signing keys are paired with their public GitHub email (if set) and their `<login>@users.noreply.github.com` address.

**Why.** Git checks a signature against the committer's email, so the list has to be keyed by email.

**What we considered instead.** GitHub login names. Git does not present those.

**If this turns out to be wrong.** An engineer whose git email is neither their public GitHub email nor the noreply address fails verification, with a message naming the email to register. The setup script compares `git config user.email` against the fetched list.

**What it touches.** `scripts/delivery/signers.py`. (Two C25 test fixtures were also corrected under this entry.)

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D29: The criterion-to-test map is its own file, `tests.json`, signed at the red stage

**What we decided.** `.work/<id>/tests.json` maps each criterion to its tests and the commit that added each. The red-stage sign-off hashes this file; the sign-off commit contains only it.

**Why.** `criteria.json` is hashed by the spec sign-off. Adding the test list there at the red stage would invalidate that sign-off, and without adding anything the red sign-off commit would be empty. The fixture found this.

**What we considered instead.** A `tests` field inside `criteria.json` (D22's first form).

**If this turns out to be wrong.** Two files describe one criterion; the spec check verifies every criterion has an entry once the item is past red.

**What it touches.** `ordering.py`, `accept.py`, `state.py`.

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D30: The spec sign-off hashes only the definition part of `criteria.json`

**What we decided.** The hash covers the change type and each criterion's id, class, statement, and verify command. It excludes status, evidence, evaluator, and plan steps, which are written after sign-off by design.

**Why.** Hashing the whole file would fail every correctly executed item at merge, because implementation and the evaluator write into it. The fixture found this.

**What we considered instead.** Hashing the whole file. Splitting progress into a second file.

**If this turns out to be wrong.** Changing a criterion's statement or verify command still invalidates the sign-off (intended). Changing which plan step covers it does not (accepted; the plan is not a signed artifact).

**What it touches.** `state.accept_hash()`, used by `accept.py` and the contract.

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D31: One file lists every command

**What we decided.** `working/commands.toml` declares each command once: name, one-line description, when it applies, and who may run it (agent, human, both). `make help`, the slash commands' descriptions, the README table, and `make status` are generated from it.

**Why.** Four surfaces that describe the same commands must not drift. One declaration, generated everywhere.

**What we considered instead.** Deriving the list from the slash-command files. The Makefile and `make status` would then have to parse Markdown.

**If this turns out to be wrong.** A command file without a registry entry, or the reverse, fails the consistency check.

**What it touches.** `working/commands.toml`, `scripts/delivery/registry.py`, `help.py`.

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D32: The artifact is validated when the sign-off message is prepared

**What we decided.** `make accept-prepare` checks the artifact (for example, that an intent lists at least one non-goal) before writing the message. The commit-message hook and CI use the same validator.

**Why.** The commit hook alone is advisory, and CI would otherwise need its own copy of the rules.

**What we considered instead.** Validating only in the commit hook.

**If this turns out to be wrong.** A rule not in the validator is enforced nowhere. New rules go into the per-stage validators in `accept.py`, listed in `working/README.md`.

**What it touches.** `scripts/delivery/accept.py`.

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D33: An intent can be accepted without a "Done means" list, for now

**What we decided.** When an engineer signs off on an intent, the tool checks that the Non-goals list has at least one item. It does not require a "Done means" list. If a "Done means" section exists, it has to have at least one item; if the section is absent, that is allowed.

**Why.** The intent form says "Done means" is required, but the tests we already approved create intents without it. Making it required now would mean changing approved tests again, and the tool that writes intents (`/intent`) is not built yet. That is the right moment to decide.

**What we considered instead.** Requiring "Done means" always. Rejected only for timing; it is a one-line change to the validator later.

**If this turns out to be wrong.** An intent could be signed without saying what finished looks like. The spec review step asks whether every intent statement has a criterion, so the gap would be caught there, one stage later than ideal.

**What it touches.** `scripts/delivery/accept.py` (the intent validator). Revisit when building `/intent` (plan step S10).

scope: local · accepted-by: overseer, 2026-09-13

---

## D34: The weekly report finds labels in commit messages, not by asking GitHub

**What we decided.** When a pull request is merged, the merge job writes the PR's labels into the merge commit as a line `Labels: tier-override, break-glass`. The weekly improvement report reads those lines from git history.

**Why.** Everything the process depends on should be readable from the repository alone, without network access or GitHub credentials. Writing the labels down once, at merge, achieves that.

**What we considered instead.** Reading labels from the GitHub API when the report runs. Rejected because the report would then need credentials and could not run offline or on a clone.

**If this turns out to be wrong.** A merge that skips the merge job (for example, an admin merging by hand) leaves no `Labels:` line, so its labels never appear in the report. The GitHub audit log still records such merges.

**What it touches.** `scripts/delivery/post_merge.py` (writes the line), `scripts/delivery/loop_report.py` (reads it).

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D35: Decision entries are written for the engineer who has to sign them

**What we decided.** Every decision entry answers five plain questions: what we decided, why, what we considered instead, what happens if it is wrong, and what it touches. Each answer is at most three sentences. No internal reference (a design section number, a criterion id) appears without a plain-word explanation in the same sentence. The human-facing writing standard and the deslop pass apply to this file.

**Why.** The overseer found the earlier entries hard to read. An engineer who cannot understand a decision will sign without reading it, which defeats the purpose of signing.

**What we considered instead.** Keeping the compact key-value format, which was written for the model to read rather than for a person.

**If this turns out to be wrong.** Entries are longer. The three-sentence cap per field keeps the whole entry under one screen.

**What it touches.** This file; the decision template in the design (Appendix A.3); the review subagent's question about decisions ("could an engineer who has not read the design restate this in one sentence?").

scope: durable → decision record · accepted-by: overseer, 2026-09-13

---

## D36: All hook logic lives in one Python module; the shell wrappers only call it

**What we decided.** `scripts/delivery/hooks.py` implements every session hook as `python -m delivery.hooks <event>`, reading the event JSON on stdin. The files under `scripts/hooks/` are one-line shell wrappers that Claude Code's `settings.json` points at.

**Why.** Hook behavior has to be tested, and a Python function that takes the event as data is testable without a shell or a live session. The wrappers stay too small to contain a bug.

**What we considered instead.** Writing each hook as a shell script. Harder to test, and the block-message helper would have to be reimplemented in shell.

**If this turns out to be wrong.** Every hook invocation starts a Python interpreter, which costs tens of milliseconds per tool call. If that proves noticeable, the hot hooks (the edit guard) can be reimplemented in shell against the same tests.

**What it touches.** `scripts/delivery/hooks.py`, `scripts/hooks/*.sh`, `.claude/settings.json`.

scope: local · accepted-by: ___

---

## D37: Test files are not blocked from agent edits; they are protected by the ratchet and by review

**What we decided.** The in-session block on "protected paths" covers process-defining files only: `working/architecture/`, `working/standards/`, `.claude/`, `scripts/`, `.github/`. Test directories are not in that list. Tests are protected differently: the ratchet refuses deleted or weakened assertions without a reviewed label, and a reviewer sees every test change.

**Why.** The red stage requires the agent to write tests. A block on editing tests would make the process impossible to follow. The fixture for the hook tests exposed the contradiction.

**What we considered instead.** Keeping tests in the edit block and having the agent write tests through a special path. Needless complexity for a rule that the ratchet already enforces better.

**If this turns out to be wrong.** An agent could weaken a test in-session, which the ratchet catches at merge and `make green` reports locally. The evaluator does not grade tests the agent weakened, because the ratchet runs before it.

**What it touches.** The design's protected-path list (11.2); `scripts/delivery/hooks.py`; the hook test fixture (an amendment: the fixture listed test directories as protected).

scope: durable → decision record · accepted-by: ___

---

## D38 (withdrawn)

Replaced by D39: the rule is parametrized instead of the violation being grandfathered.

---

## D39: A constraint can carry parameters on its line; INV-01's list of modules allowed to read the environment is one

**What we decided.** A constraint line may include `[key: value, value]` parameters after the check reference, for example `- INV-01 (check: constraints.py INV-01) [allow: shared.config, shared.logging_setup]: ...`. The checker reads them from `constraints.md`. For INV-01, `allow` lists the modules that may read the environment; with no list, only modules named `config.py` may.

**Why.** "Only `config.py` reads the environment" is a choice a real project may not make, and the overseer said so. The project owns the rule's parameters; the script owns only the mechanism. It also removes the need to grandfather the template's own logging code.

**What we considered instead.** Keeping the fixed rule and grandfathering the template's violation (D38). Dropping INV-01 as the example rule.

**If this turns out to be wrong.** A project can allow so many modules that the rule means little. The parameter list is in a protected file, so widening it is a reviewed change, and the weekly audit reports the list's length.

**What it touches.** `scripts/delivery/paths.py` (parses parameters), `constraints.py` (reads `allow`), `working/architecture/constraints.md` in the template, the C19 tests (one added case), and the baseline file (entry removed).

scope: durable → decision record · accepted-by: ___

---

## D40: No constraint runs unless the project lists it in `constraints.md`; the template ships none active

**What we decided.** `scripts/delivery/constraints.py` runs only the rules that `working/architecture/constraints.md` names. The template's `constraints.md` lists no invariant by default; it shows INV-01 (environment reads limited to listed modules) as a commented example the project can enable with its own `[allow: ...]` list. The import-linter package contract stays, because it only says libs do not import apps, which follows from the workspace layout.

**Why.** Where a project reads its configuration is the project's choice. The template should ship the mechanism for enforcing such rules, not an opinion about which rules to have. The overseer raised this.

**What we considered instead.** Shipping INV-01 active with the template's own modules allowed (D39's first form). Rejected because a default rule is still an imposed rule.

**If this turns out to be wrong.** A project that never writes a constraint gets no invariant checks, only Ruff and import-linter. The adoption steps ask the team to write their invariants, and the weekly audit reports a constraints file with no entries.

**What it touches.** `scripts/delivery/constraints.py` (runs listed rules only), `working/architecture/constraints.md` in the template, the C19 tests (one added case). Supersedes the template listing in D39; the parameter mechanism in D39 stands.

scope: durable → decision record · accepted-by: ___


---

## D41: Project-specific agent rules live in `.claude/rules/project.md`, not below a marker in `AGENTS.md`

**What we decided.** `AGENTS.md` is fully managed by the template (74 lines). The old file's domain sections (security, testing, conventions, API design, branching) moved to `.claude/rules/*.md`, loaded on demand. A project's own rules go in `.claude/rules/project.md`, which copier never overwrites.

**Why.** The design wanted a managed header with project content below a marker, but copier's skip-if-exists works per file, not per section. One managed file plus one project-owned file gives the same result without a partial-update mechanism. It also gets the root file under budget, since the domain sections were most of its 449 lines.

**What we considered instead.** A custom merge step in the migration script that preserves text below the marker. More machinery for a problem a second file solves.

**If this turns out to be wrong.** A project that edits `AGENTS.md` directly loses the edit on `copier update`; the file says where project rules go, and the migration script reports it as modified.

**What it touches.** `AGENTS.md`, `.claude/rules/`, `copier.yaml` (`_skip_if_exists`).

scope: durable → decision record · accepted-by: ___

---

## D42: A tracked, append-only issue log is the improvement loop's ledger

**What we decided.** `working/log.md` records every issue as it happens: a block that fired wrongly, a bounce, an escalation, a defect that escaped, a check that found a design defect, a test amendment. Each entry states what happened, which written definition was missing or wrong, and the fix, with a status that moves only from open to closed. `make log` adds an entry; the weekly report adds the week's labeled exits; the audit reports open entries.

**Why.** The improvement loop asks "which definition was missing" of every failure, but nothing recorded the failures in one place. Observations expire and decisions record choices; neither records what went wrong. The overseer asked for a running, tracked log.

**What we considered instead.** Reconstructing the record from labels and traces at report time (the previous design). Loses everything that never reached a label.

**If this turns out to be wrong.** The log grows unread. Entries are short, the audit reports the count of open ones, and closed entries link to the change that closed them, so it reads as a history rather than a backlog.

**What it touches.** `working/log.md`, `scripts/delivery/log.py`, the `log` Makefile target and registry entry, `working/README.md#log`, `loop_report.py`, the audit.

scope: durable → decision record · accepted-by: ___

## D44: The session hooks are one Python entry point, not eight shell wrappers (revises D36)

**What we decided.** `.claude/settings.json` invokes `scripts/hooks/hook.py <event>` for all eight Claude Code events. The file puts `scripts/` on `sys.path` and dispatches into `delivery.hooks`; `run(event, payload, repo)` remains the testable core. The eight `.sh` wrappers are removed.

**Why.** D36 made the wrappers thin on the argument that all logic belongs in `hooks.py`. They were too thin to be correct: each ran `uv run python -m delivery.hooks <event>` without `PYTHONPATH=scripts`, and the `delivery` package is not installed, so every hook exited 1 with `ModuleNotFoundError`. Claude Code treats only exit 2 as a block, so the stage guards, the protected-path guard, the accept guard and the stop gate all did nothing, silently, on every platform. Every other call site — the Makefile, the pre-commit hooks, the three delivery workflows — set the path explicitly; the wrappers were the exception. A Python entry point sets its own path, so the failure cannot recur.

**What we considered instead.** Adding `PYTHONPATH=scripts` to each of the eight wrappers, which is a smaller change but leaves eight copies of one line to keep in step. Installing the delivery package, which would put process tooling in the project's dependency graph. Keeping the wrappers and testing them, which fixes the detection but not the duplication.

**If this turns out to be wrong.** Claude Code changes how it invokes hooks, or a project needs a shell wrapper for its own reasons. The entry point is nine lines and the event contract is unchanged, so a wrapper can be reintroduced in front of it.

**What it touches.** `scripts/hooks/hook.py`, `.claude/settings.json`, `scripts/delivery/hooks.py` (docstring), `tests/scripts/test_hooks.py`, `tests/test_delivery_generation.py` (`TestHookEntryPoint`).

scope: durable → decision record · accepted-by: ___

<!--
D43 is intentionally absent. The review ported the shell scripts to
scripts/tasks/ with a scripts/task.py dispatcher so Windows would need no
shell, then reversed it when Windows moved to WSL 2, which is Linux. A
decision made and withdrawn inside one review never took effect, so it is
not recorded here. The reversal is in the history: 50eb5d5 made it, eb62bd0
took it back.
-->
