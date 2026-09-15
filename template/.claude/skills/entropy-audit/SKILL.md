---
name: entropy-audit
description: Weekly. Closed questions only about drift; drafts and issues, never commits.
---

Deterministic part first (the workflow runs it): expired observations deleted, vendored skills checked, open issue-log entries listed, the loop report written.

Then answer, each as a list of findings that cite the rule:

1. Does any file violate a constraint added after it was written? (`make constraints` with an emptied baseline in a scratch copy; report the delta.)
2. Does any living-spec statement lack a test? (`make spec-coverage`.)
3. Does any `working/architecture` doc or `AGENTS.md` line describe something the code no longer does? Cite the line and the code.
4. Does any decision record refer to code that no longer exists?
5. Is the vendored deslop reference past its review date? (Open an issue; do not edit it.)
6. Does any instruction in `AGENTS.md` or `.claude/rules/` describe behavior the agent already shows without it? Propose removal with the evidence.

Output: one draft work item per class of finding under `.work/audit-<date>/` with a draft intent, and a check summary. Commit nothing (no triggering engineer).
