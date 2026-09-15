---
name: start
description: Begin work. Runs make start, which asks only what applies to this branch, and sets up the work item. Use before editing source on a branch with no work item.
argument-hint: [TICKET=<key>] [ANSWER=<key>]
---

1. Run `make start` and show the offered answers to the engineer verbatim. Never offer "new project"; that is copier's job.
2. If the engineer described the task already, choose the answer yourself when it is unambiguous:
   - docs, config, a dependency bump, or a Python change that leaves the code identical once comments are stripped: `quick-change`
   - the software will do something differently: `change`
   - something broken that should work: `bug-fix`
   - otherwise ask one question (AskUserQuestion) with the offered answers as options.
3. Run `make start TICKET=<key> ANSWER=<answer>`. The ticket key is the work-item id and branch name; ask for it if none was given (one small question).
4. Relay the output. For `change` and `bug-fix`, the next step is `/intent`; say so and stop.
5. If the output is a BLOCKED message, relay it verbatim and stop.
