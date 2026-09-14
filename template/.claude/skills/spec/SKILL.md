---
name: spec
description: Write spec.md (a delta against the living spec) and criteria.json (every criterion starts failing, with the classes the criteria template requires), run the spec reviewer, and prepare for signature.
argument-hint: [--draft]
---

Inputs: accepted `intent.md`, `clarify.md`, `decisions.md`, `working/spec/<member>.md`, `working/architecture/constraints.md`, `working/standards/criteria-templates.md`, `working/standards/budgets.md`.

1. `spec.md`: declarative statements only, each a delta against the living spec, each mapped to at least one criterion. Draft the living-spec edits that will land in the PR (`working/spec/<member>.md`) at the same time.
2. `criteria.json` from `templates/criteria.json`: every criterion has a class, a testable statement, a `verify` command, `status: fail`, `evidence: null`. Include every class the criteria template requires for this change type; enumerate edge, negative, failure, and boundary cases explicitly. Applicable budgets become `budget`-class criteria with a measurement command. Where a required class does not apply, say so in one line in spec.md.
3. Run `PYTHONPATH=scripts uv run python -m delivery.spec_check --item <id>`. Fix what it names.
4. Run the spec-reviewer agent (Agent tool, `spec-reviewer`). It answers closed questions only. Attach its report to spec.md and fix untraced statements.
5. Present spec.md for review as one artifact (sections one at a time if over 80 lines). Then criteria.json. Never both in one turn.
6. On approval: `make accept-prepare STAGE=spec` (this batches every decision so far as Accept-Decision trailers), then tell the engineer `make accept STAGE=spec` and stop.

`--draft` (CI): write both files, run the checks and the reviewer, commit to the branch, stop; no questions.

Decisions made here go in `decisions.md` using `templates/decision.md`, written for the engineer who signs them.
