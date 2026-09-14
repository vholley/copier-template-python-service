# How work flows here

This directory holds what the process reads and writes: the living spec, the
architecture and its constraints, the writing standards, and the history of
finished work. It is tracked. `docs/` is different: supplementary reference that
never changes, not tracked, restored with `scripts/restore-from-template.sh`.

Three commands are all you need to remember: `make start`, `make status`, `make help`.
The diagram is in `docs/workflow.mermaid`.

## start

`make start` asks one question, "What are you here to do?", and offers only the
answers that apply to your branch:

| Answer | What happens | What you will sign |
|---|---|---|
| A small fix with no change in behavior | a branch, no work item | nothing; open a PR with a one-line description |
| Something the software will do differently | a work item bound to your branch; `/intent` opens | the intent, the spec, the red tests |
| Something broken that should work | the same, on the bug-fix path; `/intent` then `/diagnose` | the intent, the diagnosis |
| Not sure yet, need to look first | an exploration item; nothing merges from it | nothing until you turn it into one of the above |
| Don't want this process for this work | see [opt-out](#opt-out) | one acknowledgment |

Use `make start TICKET=<key>`; the ticket becomes the work item id and the branch name.
In Claude Code the agent runs `/start` for you when it sees a behavior change.

## stages

A change moves through: intent → clarify → spec → plan → red → implement → verify → review.
A bug fix: intent → diagnose → plan → implement → verify → review. Until the spec (or the
diagnosis) is signed, the agent cannot edit source; it can plan, ask, and write the
documents. `make status` always shows the stage and the next command.

## signing

Signing off is a git commit signed with your SSH key. The agent prepares it
(`make accept-prepare STAGE=<stage>`); you sign it in your own shell
(`make accept STAGE=<stage>`). The agent cannot run the signing step. Your key must ask
you each time it is used: a passphrase that is not cached, or an agent such as
1Password's that prompts. Register the same key on GitHub as a signing key. A change is
three signatures (intent, spec, red); a bug fix is two; a quick change is none.

## green

`make green` autofixes formatting, then runs lint, types, the tests of the members you
touched, and the delivery checks. Every implementation step ends green and is one
commit. The session's stop hook will not let a turn end with uncommitted source,
unverified claims, or checks not run since the last edit; after three blocks the
item is [escalated](#escalated).

## red-first

Every criterion gets a failing test before its implementation. `make contract` and CI
verify the test failed at the commit that added it and passes now. A test that already
passes when added is not red and is reported.

## tests

Tests may only get stronger. Deleting or weakening an assertion fails CI unless a
reviewer applies `test-change-approved`. Every test in a member that uses the process
carries `@pytest.mark.spec("<file>.md#<anchor>")` naming the statement it proves.

## living-spec

`working/spec/<member>.md` describes what each member does. A pull request that changes
a member's source must also change its spec file. `make spec-coverage` reports statements
with no test.

## constraints

`working/architecture/constraints.md` lists the rules the project enforces mechanically,
each naming its check. Nothing is enforced that is not listed there; nothing is listed
that has no check. `make constraints` runs them.

## budgets

`working/standards/budgets.md` holds every numeric limit: diff size per tier, file and
function size, coverage of changed lines, review sizes. A dimension with no budget is,
by decision, not optimized.

## checks

`make ci` runs everything CI runs. Each delivery check is one script under
`scripts/delivery/`, prints `path:line: RULE message` lines, and ends with a block
message that names the fix.

## contract

Nothing merges to `develop` without the pull-request contract: signed acceptances that
still match their files, red-first ordering, every criterion confirmed with evidence,
every decision with its consequence stated and accepted, the living spec updated, the
diff within budget, the description in the required shape, and no commit naming an LLM
as co-author. `make contract` runs it locally.

## bounced

Opened a PR that changes behavior with no work item? CI says so and names the two
commands: `make start` (choose the kind of work), then `make adopt-branch TICKET=<key>`.
The code you already wrote stays; the red-first check is waived for bounced items.

## review

One author, one reviewer, always. The reviewer receives the whole chain and answers
three questions: did the spec solve the intent, were the accepted decisions sound, is
there anything the spec did not require. Their approval carries `Intent-match: yes |
partial | no`. Reviews are asked for one thing at a time.

## escalated

After three stop-hook blocks the item stops and a human decides: back to implement (after
fixing the criterion), back to spec, or abandon. `make status` lists the three.

## state

`.work/<id>/state.json` is a cache of what git and the files already say. If it is
missing or wrong, `make rebuild ID=<id>` regenerates it. `make status` names the exact
disagreement and the command that repairs it.

## diagnosis

A bug fix begins with `diagnosis.md`: the reproduction, the evidence as links, and the
cause with its provenance (observed, inferred, hypothesized). Source edits are blocked
until the cause is confirmed by a test. The fix must land where the diagnosis says.

## spec

`spec.md` states what will be true when the work is done; `criteria.json` lists each
statement as a criterion with the command that verifies it. Every criterion starts as
failing and needs a test. Which classes a spec needs (positive, negative, failure,
boundary, regression) is in `working/standards/criteria-templates.md`.

## evaluator

A separate agent with no ability to write grades each criterion against its evidence and
writes `evaluator-report.md`. It cannot mark a criterion confirmed without opening the
evidence.

## protected

`working/architecture/`, `working/standards/`, `.claude/`, `scripts/`, and `.github/`
change only through a reviewed pull request; the agent cannot edit them in a session.
Tests and the living spec are protected by the ratchet and by review instead.

## hooks

Session hooks are in `.claude/settings.json` and call `scripts/hooks/*.sh`. They are
advisory on your machine and exist to make the right path the easy one. The pull-request
contract is the gate that cannot be switched off.

## observations

Something you noticed that fits no rule? `make observe ARGS=...` records it only if its
consequence is inferred from something concrete; hypothesized consequences are not
recorded, observed ones are bugs. Entries expire at the next weekly audit unless turned
into work.

## skills

`.claude/skills/` holds the stage skills and the vendored `deslop` skill.
`.claude/VENDORED.md` records where vendored skills came from; they are never edited here.

## deploy

Nothing in this directory, `.claude/`, `.work/`, `scripts/`, or `docs/` reaches a deployed
image: `.dockerignore` excludes them and `make deploy-surface` checks every Dockerfile.

## opt-out

You can leave the process for a branch at any time: `make opt-out` (optionally
`REASON="..."`), then `make accept STAGE=opt-out` in your shell. After that, no stage
guards or prompts. What stays, because it belongs to the repository: `make ci`, the test
ratchet, protected paths, one reviewer approval. To rejoin: `make start`.

## commands

`make help` prints every command with who may run it. The list comes from
`working/commands.toml`; slash commands in Claude Code have the same names.
