# Writing for the model

Applies to: AGENTS.md, `.claude/rules/`, skills, intent.md, spec.md,
criteria.json, decisions.md (structure only; its prose follows the human
standard), plan.md, diagnosis.md, progress.md, the living spec, area docs.

Every line costs context on every turn and is read literally.

1. Budgets. AGENTS.md under 150 lines. Area docs and spec files within
   `budgets.md`. Over budget: split, do not compress.
2. Universal content only in always-loaded files. Task- or domain-specific
   content goes in files loaded on demand (`.claude/rules/`, area docs).
3. Never restate what a linter or formatter enforces. `make budgets --agents-md`
   fails on it.
4. Instruction first, reason second, and only when the reason changes behavior.
5. Enumerate. Lists of cases, stated non-goals, checkable criteria. No prose a
   colleague would read charitably.
6. Workflows as ordered steps with explicit branches ("if X, step 4; else step 5").
7. Templates over descriptions. Give the shape to pattern-match.
8. `file:line` references. Never paste code that will go stale.
9. No hedging, no history, no rationale prose. Rationale for humans goes in
   decision records or in HTML comments in AGENTS.md (stripped before use).
10. Assume competence. Include only what the model does not already do
    reliably. The weekly audit proposes removing instructions traces show are
    unnecessary.
11. No citations to process artefacts. Never reference a decision number, a
    criterion id, a design-document section or a ticket in code, comments or
    shipped docs. They outlive what they point at, and they travel into
    repositories that never had it. State the reason instead of pointing at it.
