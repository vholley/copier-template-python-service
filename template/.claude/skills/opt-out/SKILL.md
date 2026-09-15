---
name: opt-out
description: When the engineer says, in any words, that they do not want the process for this work. Reply with the canonical text, prepare the record, do not argue.
argument-hint: [REASON="..."]
---

Reply with exactly this, then stop:

    To opt out of the process for this branch:
      1. make opt-out            (optional: make opt-out REASON="<one line>")
         I prepare the record and the commit message. A work item on this branch is archived, not deleted.
      2. make accept STAGE=opt-out
         Run this in your own shell; it signs with your SSH key. I cannot run it for you.
    To rejoin later: make start

If the engineer then asks you to prepare it: run `make opt-out` (with their reason if given) and report the output. You never run `make accept`.
