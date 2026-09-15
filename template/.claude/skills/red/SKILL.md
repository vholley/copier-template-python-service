---
name: red
description: One failing test per criterion, committed before any implementation, each marked with the living-spec statement it proves; then tests.json and the engineer's signature.
---

1. For each criterion in `criteria.json` (skip `budget` class): write a test that fails now and would pass when the criterion holds. Mark it `@pytest.mark.spec("<file>.md#<anchor>")` with the living-spec statement it proves (a statement must exist; write it in the spec edits first if not). No test without an assertion; no assertion of a constant; never patch the module under test.
2. Run each new test and confirm it fails. A test that passes now is not red: rewrite it, or if the behavior already exists, class the criterion `regression` and say so in a decision entry.
3. Commit the tests with subject `test(<id>): red <criteria>`. Record each test and its commit in `.work/<id>/tests.json` (`templates/tests.json`).
4. `make green` must pass except for the new tests (lint and types clean). The stop hook checks this.
5. Present the tests for review, one criterion's tests at a time when there are more than about 80 lines. On approval: `make accept-prepare STAGE=red`, then tell the engineer `make accept STAGE=red` and stop.
