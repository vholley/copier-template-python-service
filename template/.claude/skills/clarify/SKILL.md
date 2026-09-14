---
name: clarify
description: After the intent is signed. Contradictions first, then only the questions whose answers change what is built; everything else becomes a logged assumption with its risk.
argument-hint: [--headless]
---

Inputs: the accepted `intent.md`, `working/spec/*.md` for touched members, `working/architecture/constraints.md`.

Order is fixed:

1. Contradictions. Compare each intent statement with the living spec and the constraints. Any conflict is a `C<n>` entry in `clarify.md` with a proposed resolution. Present them first, one at a time if more than one is substantial. The stage cannot advance until each has a human resolution.
2. Decision-relevant unknowns. Only questions whose answer changes what is built: a hidden assumption, an edge case, a role or permission boundary, a data lifecycle, a failure mode. Naming, styling, and implementation choices are not asked. At most five questions per round, at most two rounds; use AskUserQuestion with concrete options.
3. Everything else is an assumption: an `A<n>` entry with a risk (what goes wrong if false) and a provenance (observed, inferred, hypothesized). Never leave a risk empty.
4. Tag every answered question and assumption `local` or `doc-gap`. A doc-gap is a question the documentation should have answered; note the target file, and the implement stage drafts the doc edit.
5. Every decision made here is an entry in `decisions.md` (see `../spec/templates/decision.md`) with a ramification; a decision that changes what is built is asked before proceeding.

`--headless` (CI): ask nothing; every unknown becomes an assumption; write `reviewed [human]: no` on each and stop. The item stays at clarify until the engineer reviews the log.

Write `clarify.md` from `templates/clarify.md`. Present it as one artifact, then stop. Next: `/spec`.
