---
name: diagnose
description: For a bug, after the intent is signed. Reproduce, gather evidence you can link, and confirm the cause with a discriminating test before any fix; then the engineer's signature.
---

Source edits are blocked by the hook until `diagnosis.md` has a reproduction and a cause with `status: confirmed`. Test files and probes are allowed.

1. Reproduction: the exact command or steps and the observed output, attached. If it cannot be reproduced after real attempts, record the attempts and close the item as unreproduced (`make status` shows how). Do not fix what you cannot reproduce.
2. Evidence: everything examined, as links a reviewer can open (log query and result, stack trace, `git bisect` result, a probe's output). Descriptions without links do not count. Logs: `gcloud logging read` where GCP is on.
3. Cause claims: each tagged `observed(E<n>)`, `inferred(E<n>,...)`, or `hypothesized`. A hypothesis is resolved by a discriminating test: write what you would observe if it is true and if it is false, run it, record the result. Only then set `status: confirmed`. Record rejected hypotheses with what ruled them out (durable ones promote to the area doc).
4. Confirmation test: a committed failing test whose assertion or message names the mechanism. Record `location: <file>:<function>` where the fix will go; CI checks the fix lands there.
5. Write `diagnosis.md` from `templates/diagnosis.md`. Present it as one artifact. On approval: `make accept-prepare STAGE=diagnosis`, then tell the engineer `make accept STAGE=diagnosis` and stop. Next: `/plan`.
