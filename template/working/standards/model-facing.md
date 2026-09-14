# Writing standard: text the model reads

Applies to AGENTS.md, `.claude/rules/`, skills, `.work/<id>/` artifacts (intent, spec,
criteria, plan, diagnosis, progress), the living spec, and area docs. Decisions
(`decisions.md`) follow the human-facing standard instead, because a person signs them.

Every line costs context on every turn and is read literally. So:

1. Stay within the line budget in `budgets.md`. AGENTS.md under 150 lines.
2. Only universal content in files that always load; task- and domain-specific content
   in files loaded on demand (`.claude/rules/`, area docs).
3. Never restate what a linter or formatter enforces.
4. Instruction first, reason second, and the reason only when it changes behavior.
5. Enumerate cases; state non-goals; make every criterion checkable by a command.
6. Workflows as ordered steps with explicit decision points ("if X, do 4; else 5").
7. Give the shape (a template) rather than a description of the shape.
8. Reference code as `path:line`; never paste code.
9. No hedging, no history, no rationale prose. Rationale for humans goes in decision
   records or in HTML comments in AGENTS.md (stripped before the model sees them).
10. Include only what the model does not already do reliably; the weekly audit removes
    instructions that traces show are unnecessary.

Checked mechanically: line budgets (`make budgets`), required sections in artifact
templates (`make accept-prepare`), duplication of Ruff rules in AGENTS.md
(`make budgets --agents-md`).
