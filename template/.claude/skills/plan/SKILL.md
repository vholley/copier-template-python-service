---
name: plan
description: After the spec is signed. Fix the interfaces the tests will be written against and order the steps, each mapped to the criteria it satisfies; split the item if it will not fit the diff budget.
---

1. Read the accepted `spec.md` and `criteria.json`, `working/architecture/constraints.md` (layers), and the touched members' code.
2. Interfaces first: signatures, module boundaries, data shapes. These are what `/red` writes tests against. Any interface choice a reviewer could disagree with is a decision entry (ask before proceeding if it changes a public interface).
3. Steps: ordered, one step per commit, each listing the criteria it satisfies. Every criterion appears in at least one step. Estimate the diff; if it exceeds `diff.<tier>.max_lines` in `working/standards/budgets.md`, split into several work items now, each with its own spec, and say so.
4. Write `plan.md` from `templates/plan.md`. It is not signed. Present it as one artifact, then stop. Next: `/red`.
