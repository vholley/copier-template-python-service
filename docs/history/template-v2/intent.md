# Intent: Implement the delivery system in copier-template-python-service
id: template-v2
workflow: project
risk: standard

## What
Produce a new version of `vholley/copier-template-python-service` that generates a project with the quality-first delivery system installed: the scaffold (docs, standards, constraints, scripts, Makefile targets, CI, hooks) and the process (skills, commands, agents, vendored deslop) under `.claude/`, per the design document sections 3, 5.5, 6, 7, 8, 10, 11, 12, 17.5, 19 and Appendix B, as of register entry 77.

## Why
The template is the delivery mechanism for every new project and the retrofit path for the existing monorepo. Building it first means the system is exercised on itself before it touches live work, and the test bed (milestone 2) can be generated from it rather than assembled by hand.

## Constraints
- Claude Code only; all process automation uses `.claude/` primitives (design register #2, #59).
- The template's existing conventions stand unless the design overrides them: uv workspace with `libs/*` and `apps/*`, `develop`/`main` branches, Ruff and Pyright strict, pre-commit with conventional commits, Makefile as the command surface (design 17.5).
- Every script the scaffold ships passes the scaffold's own checks (Ruff, Pyright strict) and has tests, written red-first (design 7.8 applied to this build).
- Every block emitted by any script or hook uses the four-line contract (design 19.2) through one shared helper.
- Everything written follows the two writing standards (design section 10). Model-facing files stay within their budgets.
- Deslop is vendored from `/mnt/skills/user/deslop/` with `VENDORED.md` provenance (design 12.5).
- Work happens in a sandbox with no Claude Code runtime and no GitHub. Verification here is limited to what is computable without them.

## Non-goals
- Retrofitting the existing monorepo (milestone 3).
- Building the test-bed repository or running probabilistic tests (milestone 2). Deterministic scenarios ship with the template's tests only where they can run against a generated project.
- Extracting a plugin.
- Tuning the human-facing standard to a team voice beyond the deslop baseline.
- Reworking the GCP, Docker, and Terraform options beyond the one `use_gcp` conditional the design needs.
- Verifying hook behavior inside a live Claude Code session, GitHub Actions execution, or rulesets. These are recorded as assumptions with their risk and are the first things milestone 2 checks.

## Done means
- `copier copy` from the new template generates a project; `./scripts/bootstrap.sh` and `make ci` (with the delivery targets) exit 0 on it (testing plan TPL-01).
- `working/` is tracked and `docs/` is untracked in the generated project; `copier update` after editing a project-owned file under `working/` leaves it unchanged (TPL-02).
- `make new-app NAME=x` produces a member with `[tool.delivery]`, a layers contract, and an `unspecified` spec skeleton, and `make ci` still passes (TPL-03).
- Every delivery script has unit tests, and the deterministic testing-plan scenarios that need no agent and no GitHub pass against the generated project: SPEC-01, CLR-04, DEC-01, ACC-01, REV-01, REV-02, REV-06, REV-07, DIAG-01, DIAG-02, DIAG-04, DIAG-05, DIAG-06, DIAG-07, SCOPE-03, SCOPE-04, SCOPE-05, DONE-01 to DONE-04, DEF-01 to DEF-05, WRT-01 to WRT-03, ENF-03, ENF-04, ENF-05 (classification and bounce, without the GitHub label step), EXP-01 to EXP-04, EXP-06, TDD-01 to TDD-05, TDD-07, TPL-04, TPL-05. Signature verification in DEC-02 is tested against a local allowed-signers file standing in for the GitHub fetch.
- The template's own `tests/test_generation.py` passes with the new assertions.
- `.claude/` contains every skill, command, and agent named in design 12.1 and 12.5 (including `start` and `red`), structurally valid, each within its line budget.
- `make start`, `make status`, `make green`, `make accept`, `make adopt-branch`, and `make abandon` exist and behave per design 19 and 7.3.
- `working/README.md` is the one-screen process guide (design 19.4) within its budget.

## Open questions
Carried to clarify.md.

accepted-by [human]: overseer, 2026-09-12 (sandbox: recorded here; in the system this is a signed `accept(work-template-v2): intent` commit)
