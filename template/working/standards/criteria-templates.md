# Criteria templates

Which classes of criterion a spec must include, by change type. `make contract` fails a
`criteria.json` missing any listed class (the table is the source; nothing is
hard-coded). Coverage is decided here, before code.

| change type | required classes |
|---|---|
| new-behavior | positive, negative, failure, boundary |
| changed-behavior | positive, negative, failure, boundary, regression |
| defect | reproduction, regression, location |
| trivial | |

Class meanings:

- positive: the behavior works as intended on a normal input.
- negative: the behavior refuses what it should refuse (bad input, missing permission).
- failure: what happens when a dependency is down, times out, or fails part-way.
- boundary: behavior at a limit (empty, maximum, zero, exactly the budget).
- regression: something that worked before still works.
- reproduction: for a bug, the test that fails before the fix and passes after.
- location: for a bug, the fix lands at the file and function the diagnosis names.
- budget: a numeric limit from `budgets.md`, verified by a measurement command; has no test.
- e2e: the member's public entry point exercised as a client would (CLI call, request).

Rules that apply during a work item:

- When a check this file relies on does not exist yet (adoption, a first project), the
  spec author walks this table by hand and notes the walk in `spec.md`.
- A criterion added after the spec was signed is an amendment (`/amend`) and is signed on
  its own; it cannot be added silently.
