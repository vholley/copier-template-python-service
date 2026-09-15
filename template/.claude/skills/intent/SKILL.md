---
name: intent
description: Write .work/<id>/intent.md (what, why, constraints, non-goals, done means) from a short conversation, then prepare it for the engineer's signature.
---

Inputs: the bound work item (`make status`), what the engineer has said so far.

1. Read `working/spec/<member>.md` for the members the change is likely to touch, and `working/architecture/overview.md`.
2. Draft `intent.md` from `templates/intent.md`, or from `templates/intent-project.md` when the item's workflow is `project` (`make status` names it). Fill What and Why from the engineer's words. Non-goals is mandatory: list at least one thing this item will not do. Done means: observable outcomes the requester would accept.
3. Ask at most three questions before drafting, all about the why and the non-goals (AskUserQuestion, options where the answer space is small). Never ask about implementation.
4. Present intent.md for review as one artifact. If it is over 80 lines, shorten it; an intent is short by nature.
5. When the engineer says it is right: `make accept-prepare STAGE=intent`, then tell the engineer `make accept STAGE=intent` and stop. You never run `make accept`.

Stop conditions: the engineer has not answered; the artifact is presented; a BLOCKED message (relay it, stop).
