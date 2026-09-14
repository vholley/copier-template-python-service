# Criteria templates

Which criteria classes a spec must include, by change type. `spec_check.py`
reads this table (D20); a spec missing a required class is refused. Coverage
is decided here, before code.

| change type | required classes |
|---|---|
| new-behavior | positive, negative, failure, boundary |
| changed-behavior | positive, negative, failure, boundary, regression |
| defect | reproduction, regression, location |
| trivial | |

Classes:

- positive: works when used as intended
- negative: refuses what it should refuse (bad input, unauthorized, not found)
- failure: behavior when a dependency is down or an operation fails midway
- boundary: behavior at a limit (empty, maximum, exactly the budget)
- regression: something that already worked still works
- reproduction: the failing test that shows the defect (fails before, passes after)
- location: the fix touches the diagnosed file and function
- budget: a numeric limit from `budgets.md`, verified by a check script, no test
- e2e: exercises the member's public entry point as a client would

Where a required class does not apply, the spec says so in one line and the
reviewer confirms it; the class is not silently omitted.

## When a check does not exist yet

A new repository has no tests for its own checks. When a check this table relies
on is not built yet, the required classes are walked by hand and the walk is
noted in the artifact. This rule exists because the first work item ran before
its own checks did.
