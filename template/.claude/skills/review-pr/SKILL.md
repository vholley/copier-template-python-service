---
name: review-pr
description: Run the two read-only reviewer agents on a pull request and post their closed-question reports. Never a verdict; the human reviewer decides.
argument-hint: <pr-number>
---

1. Fetch the PR description and diff (`gh pr view`, `git diff origin/develop...HEAD`). Find the bound work item (`make status`).
2. Run the necessity-reviewer agent: for each hunk, which criterion or plan step requires it; for each new dependency, interface, or default, which decision entry covers it. Output the mapped list and the unmapped list.
3. Run the spec-reviewer agent: does the delivered behavior (the living-spec edits) match the intent; are the clarify questions answered or carried; does the diff change behavior no spec statement describes.
4. Human-facing check: does the PR description let a reader without the work item understand what changed and why; is every term of art defined; could an engineer restate each decision in one sentence.
5. Post both reports as a PR comment under the headings "Unmapped hunks", "Spec traceability", "Readability". No recommendations, no summary judgement.
