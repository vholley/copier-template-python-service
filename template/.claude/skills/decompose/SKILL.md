---
name: decompose
description: New project, after the architecture is approved. Write the living-spec skeleton and the first work items in dependency order; each becomes a change with its own intent.
---

1. `working/spec/<member>.md` for each member: `status: unspecified` until statements exist; write the statements the architecture already implies.
2. A feature list in dependency order, each entry a draft `intent.md` for a future work item (`../intent/templates/intent.md`). Small enough that one item fits `diff.standard.max_lines`.
3. Present the list as one artifact. On approval, create the first item with `make start TICKET=<key> ANSWER=change` and hand off to `/intent`. Build nothing here.
