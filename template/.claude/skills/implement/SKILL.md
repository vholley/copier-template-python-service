---
name: implement
description: After the red tests are signed. One plan step at a time: make it green, commit, record evidence; then the evaluator, then PR preparation.
---

Per step, in order:

1. Implement only what the step's criteria require. Any choice a reviewer could disagree with (behavior, interface, dependency, data shape, default) is a decision entry (`../spec/templates/decision.md`); a new dependency or interface change is asked before proceeding.
2. `make green`. Fix what it reports. Commit with subject `feat(<id>): <step>` (or `fix(...)`).
3. In `criteria.json`, set `status: pass` and `evidence` (a run id, a log path, a command output link) for the criteria the step satisfies. Never `pass` without evidence.
4. Update `working/spec/<member>.md` for any behavior this step changes, in the same commit.
5. Findings: a concern must name the rule it violates (criterion, spec statement, constraint, lint rule). Blocking: in scope, fix it. Otherwise `make observe` with a concrete consequence, or nothing. Never act on out-of-scope findings.

After the last step:

6. Run the evaluator agent (Agent tool, `evaluator`). It writes `.work/<id>/evaluator-report.md`. If any criterion is `not-demonstrated`, fix and re-run; three consecutive failures on the same criterion is an escalation (`make status`).
7. PR preparation: draft promotions (durable decisions to `working/architecture/decisions/ADR-<n>-<slug>.md`; doc-gaps to the named doc), the PR description from `.github/pull_request_template.md`, and run the deslop skill over every human-facing artifact you wrote. If decisions were made during implementation: `make accept-prepare STAGE=decisions` and tell the engineer to sign.
8. `make contract` (local dry run). Fix what it reports. Then tell the engineer the branch is ready for a pull request, and stop.

Never end a turn with uncommitted source or a criterion marked pass without evidence; the stop hook will block, and after three blocks the item escalates.
