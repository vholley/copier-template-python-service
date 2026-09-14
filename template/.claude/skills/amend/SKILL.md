---
name: amend
description: Change an accepted artifact after acceptance, one criterion at a time, as a side loop; re-accept only the affected part. Large amendments go back to spec.
argument-hint: [--to spec]
---

1. Classify the cause: mistake, discovered fact, missing criterion, wrong interface. Record a decision entry (blocking: ask before proceeding).
2. Guard: if the amendment touches more than `amend.max_criteria` criteria or changes the intent's What, refuse the side loop and move the item to spec (`--to spec`; a decision entry explains why).
3. Apply the edit to the artifact. The stage does not move.
4. Re-acceptance of only the affected part: a missing or changed criterion means `make accept-prepare STAGE=spec` covering the amended criteria.json (the message lists the changed ids) and, if its test changed, `STAGE=red`; a changed test that the current code already passes is classed `regression` and the entry says so.
5. `make log WHAT="..." MISSING="..." FIX="..."` for the issue the amendment fixed.
6. Present the one changed part for review, then tell the engineer which `make accept` to run, and stop.
