# Plan: template-v2

Each step is one commit series: red (tests) then green (implementation), per design 7.8, for the steps that produce scripts. Steps that produce Jinja templates, docs, or configuration are verified by generation tests (D5 scoping). Interfaces are fixed here so the red tests can be written against them before any script exists.

## Interfaces (shared by all scripts)

- Package `scripts/delivery/` importable as `delivery`; every script is a module with `main(argv: list[str]) -> int` and a `python -m delivery.<name>` entry; exit 0 pass, 1 violation, 2 usage or environment error.
- `delivery.block.render(rule_id: str, what: str, why: str, next_: list[str], more: str) -> str` produces the four-line message; `delivery.block.fail(...)` prints it to stderr and returns 1 (or 2 for environment errors). No other module prints "BLOCKED".
- `delivery.state` owns `.work/<id>/state.json`: `create(id, workflow, branch)`, `read(id)`, `advance(id, to)`, `exits(state) -> list[str]`, `abandon(id)`; every write records `checksum` over the other fields; `verify(id)` recomputes it.
- `delivery.paths`: reads `working/standards/budgets.md`, `working/architecture/constraints.md` (layer manifest, protected paths, high-risk and trivial lists), and each member's `[tool.delivery]`.
- Checks (`constraints`, `budgets`, `spec_coverage`, `test_ratchet`, `ordering`, `diff_coverage`, `deploy_surface`, `spec_check`) print `path:line: RULE-ID message` lines on stdout and a single four-line block on stderr summarizing the first failure.
- Git access through `delivery.gitx` (subprocess wrappers: `changed_files(base)`, `commits_on_branch(base)`, `blob_at(commit, path)`, `verify_commit(sha, signers_file)`), so tests can point every script at a temporary repository.
- Signer list: `delivery.signers.load(source)` where source is `github:<org>` or `file:<path>`; on any fetch failure returns an error the caller must fail closed on.

## Steps

| Step | Produces | Criteria | Commits |
|------|----------|----------|---------|
| S1 | Repository skeleton in the template repo: `tests/` layout, `tests/scenarios/` runner, `tests/check_traceability.py`, generation fixture that renders the template once per session; `copier.yaml` changes (S1.1 to S1.4) | C01, C02, C04, C34, C35 (runner only) | red: generation tests; green: copier.yaml |
| S2 | `block.py`, `state.py`, `paths.py`, `gitx.py` (the shared layer) | C17, C18 | red then green per module |
| S3 | `constraints.py` with rule registry, `budgets.py`, `spec_coverage.py`, `spec_check.py`, `deploy_surface.py` | C19, C20, C21, C38, C39 | red then green per script |
| S4 | `test_ratchet.py` (ratchet and `--quality`), `ordering.py`, `diff_coverage.py` | C22, C23, C24 | red then green per script |
| S5 | `signers.py`, `pr_contract.py`, `compute_tier.py` | C25, C26, C37 | red then green per script |
| S6 | `start.py`, `status.py`, `accept.py` (prepare and sign), `post_merge.py`, `observe.py`, `audit_observations.py`, `vendored_check.py`, `loop_report.py` | C27, C28 | red then green per script |
| S7 | Hook shell wrappers under `scripts/hooks/` and `.claude/settings.json`; `verify-gate.sh`, stage guards, nudge, ask limiter, accept block | C30, C31, C32, C33 | red (hook tests drive the wrappers with event JSON) then green |
| S8 | `pyproject.toml`, `Makefile`, `.pre-commit-config.yaml`, `.github/` (CODEOWNERS, setup action, six workflows, PR template), `.dockerignore` | C09, C10, C11, C12, C16 | generation tests |
| S9 | `working/` skeleton and standards (four standards files, README, criteria templates, budgets with B.5 defaults), `docs/DELIVERY-SYSTEM.md`, rewritten template docs, `AGENTS.md`, `MIGRATION.md`, `migrate-to-delivery.sh` | C06, C14, C15, C36 | generation tests; deslop pass on human-facing files |
| S10 | `.claude/commands/`, `.claude/skills/` (twelve stage skills with templates), `.claude/agents/` (four), vendored `deslop/` with `VENDORED.md`, `.claude/rules/ruff-remediation.md` | C07, C08 (usage), C05, C03 | generation tests; A4 verified against the subagent and settings references before writing |
| S11 | `app-template/` layer skeleton and `new-app.sh` extension | C13 | generation tests |
| S12 | Discipline check `tests/test_discipline.py`; full suite run; C29 | C29, C35 | verification |

Order rationale: S2 first because every later script imports it and every block message depends on it (C17 spans the suite); S3 to S6 in dependency order; S7 after the scripts it wraps; S8 to S11 are configuration and content that the generation tests verify against the scripts already built; S12 last because it checks the history the other steps produced.

Stopping points for review: after S2 (the shared layer sets every script's shape), after S7 (all executable behavior exists), and after S12.

## Diff budget

Not applicable to a template repository as a single PR budget; each step is its own PR to the template's `main` in the sequence above, so review is per step.
