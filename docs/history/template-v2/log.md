# Issue log: template-v2

Append-only. One entry per thing that went wrong, with the definition that was
missing and the fix. Status moves from open to closed only.

L-1 to L-10 are from the build. L-11 onward are from the review that followed
it: one entry per class of finding, each naming the commit that closed it.

Discipline evidence: verified on 2026-09-13 by tests/test_discipline.py, since
removed: every script's test commit preceded its implementation commit.

## L-1 · 2026-09-13 · spec stage · closed
What happened: criteria.json was written without the `failure` class the criteria template requires.
Which definition was missing: the check that enforces required classes (spec_check.py) did not exist yet; the manual walk of the template was skipped.
Fix: C37 to C39 added; the "no check yet" rule added to the criteria template (G1). Closed 2026-09-13.

## L-2 · 2026-09-13 · S5 fixture · closed
What happened: the red-acceptance commit was empty; the design put the test map inside criteria.json, already hashed at spec.
Which definition was wrong: where the criterion-to-test map lives.
Fix: tests.json, hashed at red (D29). Closed 2026-09-13.

## L-3 · 2026-09-13 · S5 fixture · closed
What happened: every correct item failed the contract's hash check because implementation writes status and evidence into criteria.json.
Which definition was wrong: the acceptance hash covered mutable fields.
Fix: the hash covers definition fields only (D30). Closed 2026-09-13.

## L-4 · 2026-09-13 · S7 fixture · closed
What happened: test directories were both edit-blocked and required to be written by the agent at the red stage.
Which definition was wrong: the protected-path list included tests.
Fix: tests protected by the ratchet and review, not the edit block (D37). Closed 2026-09-13.

## L-5 · 2026-09-13 · S8 build · closed
What happened: `ruff --unsafe-fixes` deleted every print() in the scripts; the lint config extracted for the sandbox lost the per-file ignore because the pattern was relative to the config's directory.
Which definition was missing: a location-independent per-file pattern; nothing in the process forbids unsafe autofixes.
Fix: pattern `**/scripts/delivery/**`; `make green` uses safe fixes only; caught by 50 failing tests. Closed 2026-09-13.

## L-6 · 2026-09-13 · S8 build · closed
What happened: constraints.py flagged the template's own logging_setup for reading the environment.
Which definition was wrong: the template shipped an opinion (only config.py reads the environment) as an active rule.
Fix: constraints run only when the project lists them; parameters on the constraint line (D39, D40). Closed 2026-09-13.

## L-7 · 2026-09-13 · S9 build · closed
What happened: the writing check found em-dashes in the template's own README and RATIONALE.
Which definition was missing: the human-facing standard had not been applied to the template's existing docs.
Fix: docs corrected; the check now runs on them in the generation tests. Closed 2026-09-13.

## L-8 · 2026-09-13 · review · closed
What happened: decision entries were written in the model-facing style and were hard for a human to read.
Which definition was wrong: decisions.md was under the model-facing standard.
Fix: the five-question format; human-facing standard applies (D35). Closed 2026-09-13.

## L-9 · 2026-09-13 · S11 · closed
What happened: a minimal-variant app's generated conftest.py failed `ruff format --check` on a trailing blank line; the base template had the same latent defect, unseen because no app was ever generated in its tests.
Which definition was missing: the template's own generation tests never scaffolded an app and ran `make ci` on it.
Fix: whitespace in the Jinja conditional; TPL-03 now runs `make ci` after `new-app`. Closed 2026-09-13.

## L-10 · 2026-09-13 · S12 · open
What happened: the evaluator step (a fresh-context, read-only agent grading the criteria) could not run in this build; the sandbox has no Claude Code session.
Which definition was missing: none; the check exists (DONE-05, DONE-06) and needs a live session.
Fix: (open) milestone 2, the test bed, runs the evaluator against this item's criteria.json as its first act.

## L-11 · 2026-09-14 · review · closed
What happened: `state.py` used PEP 758 unparenthesized multi-`except`, which is Python 3.14 syntax, while `copier.yaml` still offered 3.13 as a choice. On 3.13 the module would not import, so every hook and every check failed at import.
Which definition was missing: nothing generated or ran a project at the older offered version; conftest and the CI matrix both hardcoded 3.14.
Fix: parenthesized, and a py313-no-gcp leg added to the matrix so the offered choice is exercised. Closed 2026-09-14 (dcede19).

## L-12 · 2026-09-14 · review · closed
What happened: all eight session hooks exited 1 with ModuleNotFoundError and silently did nothing. The wrappers ran `python -m delivery.hooks` without `PYTHONPATH=scripts`, and Claude Code treats only exit 2 as a block.
Which definition was missing: the wrappers were asserted to exist and to be referenced, never executed. Every other call site set the path; nothing compared them.
Fix: one Python entry point that sets its own path (D44), plus tests that run all eight events end to end in a generated project. Closed 2026-09-14 (c2359c0).

## L-13 · 2026-09-14 · review · closed
What happened: a discipline test pointed ruff at a config file nothing in the repository creates, so the generation-tests job was red on every platform. The failure message was empty because ruff writes config errors to stderr and the assertion printed stdout.
Which definition was missing: no check that a test's fixtures exist; a test that cannot pass looks the same as one that has not been run.
Fix: lint inside the generated project instead, the way `make lint` does. Closed 2026-09-14 (be6c1c4).

## L-14 · 2026-09-14 · review · closed
What happened: the shipped app-template Dockerfile violated the template's own DEPLOY-01 rule. A multi-stage copy reads from another build stage, not from the repository, but the rule treated the source as a repository path, so every generated project with Docker failed its first CI run.
Which definition was wrong: DEPLOY-01 did not distinguish a stage copy from a context copy. Compounding it, `make ci` omitted `deploy-surface` while the generated workflow ran it, so the template never saw its own failure.
Fix: skip stage sources; add `deploy-surface` to `make ci` so the two agree. Closed 2026-09-14 (5afc1e6).

## L-15 · 2026-09-14 · review · closed
What happened: content that only makes sense under an answer was emitted regardless of it. The spec pytest marker was registered only under enable_delivery while --strict-markers and the app template's marker were unconditional, so `make new-app` broke `make test` in a plain project. AGENTS.md told a plain project's agent to run `make green` and read working/README.md, neither of which exists. The .dockerignore was gated on enable_delivery rather than include_docker. A commented-out INV-01 example was still parsed and run, failing every GCP project.
Which definition was missing: _exclude had 27 conditional entries across six questions, and CI generated four combinations, none varying enable_delivery.
Fix: gate each on its actual condition; skip HTML comment blocks when reading constraints; widen the matrix to eight combinations. Closed 2026-09-14 (4b3a25c, d7a3903, 2e2235a, eb62bd0).

## L-16 · 2026-09-14 · review · closed
What happened: MIGRATION.md and docs/DELIVERY-SYSTEM.md each existed as both a plain file and a .jinja file. Both render to one destination, so which won depended on directory scan order, and the two versions contradicted each other about how to run the migration.
Which definition was missing: nothing forbids two sources for one output, and the test fixtures passed overwrite, which silently takes whichever was scanned last.
Fix: one source each; the surviving text corrected. Closed 2026-09-14 (622d4bc).

## L-17 · 2026-09-14 · review · closed
What happened: three test classes were defined twice in one file, so Python kept the second and dropped seven tests at import with no error. Two further assertions ended in a constant disjunction and could not fail; one of them asserted nothing at all. When the shadowed tests were restored, one failed immediately -- it had been hiding a real defect.
Which definition was missing: the tautology detector the template ships was never run against the template's own tests.
Fix: the duplicated block removed, the unique test kept and corrected, both tautologies replaced. Closed 2026-09-14 (4c0b407).

## L-18 · 2026-09-14 · review · closed
What happened: three sites compared git's output, which is always forward-slashed, against a platform path string, which is backslashed on Windows; `make accept` could never succeed there. The vendored-skill digest sorted Path objects, which compare case-insensitively on Windows, so the same bytes hashed differently per platform. A test fixture raced a detached `git gc` and failed only on macOS.
Which definition was missing: the repository claimed cross-OS support but CI ran on one platform.
Fix: compare as posix, sort by relative posix path, disable auto-gc in the fixture; generation tests now run on ubuntu and macOS. Closed 2026-09-14 (e8d0d57, d7a3903, 2622e77).

## L-19 · 2026-09-14 · review · closed
What happened: 41 bytecode files were committed, and the root .gitignore had no Python entries at all. A stale bytecode file shadows imports for anyone running the scripts in place.
Which definition was missing: nothing checked what the repository tracks.
Fix: untracked, and the ignore file extended. Closed 2026-09-14 (edba499).

## L-20 · 2026-09-14 · review · closed
What happened: a fail-closed check always failed. The delivery-checks workflow passes a signer source built from the repository owner, but the resolver implemented it as an organisation member lookup only. On a personal repository -- the documented target -- that is a 404, which became a fetch error, and every pull request was blocked.
Which definition was missing: the contract was specified for organisations and deployed to a personal account.
Fix: fall back to the account itself, but only after confirming it is a user, so a real organisation we cannot read still fails closed. Closed 2026-09-14 (2c41153).

## L-21 · 2026-09-14 · review · closed
What happened: the repository's own README and CONTRIBUTING were never updated. The README contained no occurrence of "delivery", and its question table omitted enable_delivery, which defaults to true -- so the documented default output did not match what the template produced. The design document the implementation cites by decision number was not in the repository at all, leaving every D-number reference across 32 files dangling.
Which definition was missing: the writing check runs on generated docs, not on the template repository's own.
Fix: the table and a section on the delivery system added; the design record committed under docs/. Closed 2026-09-14 (a42cdee, 622d4bc).

## L-22 · 2026-09-14 · review · closed
What happened: the supported platforms changed twice. The shell scripts were ported to Python so Windows would need no shell, then the port was reversed when Windows moved to WSL 2, which is Linux.
Which definition was missing: the repository named Windows as supported without saying what that meant -- native, or through WSL.
Fix: macOS and Linux are the supported platforms; Windows is served by WSL 2, stated in the README and in docs/SETUP.md. The hook entry point was kept, because it fixed a defect present on every platform (L-12). Closed 2026-09-14 (eb62bd0).
