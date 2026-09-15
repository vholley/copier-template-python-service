# Spec: template-v2
id: template-v2
delta-against: vholley/copier-template-python-service at commit of 2026-09-11 (8 commits)
accepted-by [human]: overseer, 2026-09-13 (sandbox record; in the system a signed accept(work-template-v2): spec commit)
detail: design document sections cited per statement; this file states behavior, the design states mechanism

## S1 copier.yaml
- S1.1 `enable_delivery` (bool, default true) is asked after `include_terraform`. When false, no file listed in S2 is generated and no other output changes.
- S1.2 When true, a `delivery` group asks: `owner_group` (optional handle, default empty; when set, CODEOWNERS is generated for the protected paths), `high_risk_paths` (list, default `["**/auth/**", "**/migrations/**"]`), `trivial_paths` (list, default `["docs/**", "*.md", ".github/**", "**/tests/**", "pyproject.toml", "uv.lock"]`).  Budgets are not asked; B.5 defaults are written.
- S1.3 `_skip_if_exists` lists: `working/spec/**`, `working/architecture/**`, `working/standards/budgets.md`, `working/observations.md`, `AGENTS.md` (below its managed header marker), `.github/CODEOWNERS`. `docs/` stays untracked and regenerated as in the current template.
- S1.4 `_message_after_update` names `MIGRATION.md`. `_tasks` prints the `make hooks` and signing-key setup lines when `enable_delivery`.
- S1.5 Existing questions and their effects are unchanged (design 17.5, register #80).

## S2 Generated files when enable_delivery (design 3.1, 17.5)
- S2.1 Tracked `working/` (register #87): `README.md` (one-page process guide with command table), `architecture/{overview,constraints}.md`, `architecture/decisions/`, `spec/README.md`, `standards/{model-facing,human-facing,criteria-templates,budgets}.md`, `observations.md`, `history/.gitkeep`. Untracked `docs/` gains `DELIVERY-SYSTEM.md` (the system overview) and `workflow.mermaid` (the workflow diagram) and keeps the four existing template docs; `.gitignore` is unchanged.
- S2.2 `.claude/settings.json` (hooks per design 11.1, `includeCoAuthoredBy: false`), `.claude/rules/ruff-remediation.md`, `.claude/commands/*.md` for every registry entry (start, status, help, green, ci, contract, accept, adopt-branch, amend, abandon, new-app, and the LLM stages), `.claude/skills/*/SKILL.md` for start, intent, clarify, spec, plan, red, implement, diagnose, architect, decompose, review-pr, entropy-audit, and vendored `deslop/` with `VENDORED.md`; `.claude/agents/{evaluator,necessity-reviewer,spec-reviewer,explorer}.md`.
- S2.3 `scripts/`: `working/` package with `block.py` (19.2 helper), `stage_state.py`, `constraints.py`, `budgets.py`, `spec_coverage.py`, `test_ratchet.py`, `ordering.py`, `diff_coverage.py`, `pr_contract.py`, `compute_tier.py`, `post_merge.py`, `observe.py`, `audit_observations.py`, `vendored_check.py`, `loop_report.py`, `spec_check.py`, `deploy_surface.py`, `start.py`, `status.py`, `accept.py`, `migrate-to-delivery.sh`; hook shell wrappers under `scripts/hooks/`.
- S2.4 `.github/`: `CODEOWNERS` only when `owner_group` is set; `actions/setup/action.yml`; workflows `ci.yml` (extended), `delivery-checks.yml`, `review-agents.yml`, `spec-draft.yml`, `post-merge.yml`, `entropy-audit.yml`; `pull_request_template.md` replaced by A.7 with the `Intent-match:` field.
- S2.5 `Makefile` gains `constraints`, `budgets`, `spec-coverage`, `green`, `contract`, `start`, `status`, `help`, `accept-prepare`, `accept`, `adopt-branch`, `abandon`, `amend`, `new-app`, and one `make <stage>` target per LLM stage that prints the slash command; `ci` includes the first three. `working/commands.toml` is the registry; `make help`, the slash-command descriptions, the README table, and `make status` are generated from it (design 19.7).
- S2.6 `.pre-commit-config.yaml` adds local hooks for `constraints.py`, `budgets.py`, and an `Accept:` trailer validator on `commit-msg`; conventional-pre-commit allows type `accept`.
- S2.7 `pyproject.toml` adds the B.1 Ruff rules, `[tool.importlinter]`, the `spec` and `criterion` pytest markers, and `import-linter`, `diff-cover`, `mutmut` to the dev group.
- S2.8 `app-template/` gains the layer directories; `scripts/new-app.sh` writes `[tool.delivery]`, a layers contract, and `working/spec/<app>.md` marked `unspecified`.
- S2.9 `AGENTS.md` is the design 7.1 content within 150 lines, with a managed-header marker; `CLAUDE.md` stays `@AGENTS.md`.
- S2.10 `MIGRATION.md` at the project root describes the changes for projects generated from earlier versions.
- S2.11 Nothing from the delivery system is deployable: a root `.dockerignore` excludes `.claude/`, `.work/`, `working/`, `docs/`, `scripts/`, `.github/`, `**/tests/`, and `*.md`; the app Dockerfile keeps its explicit `COPY` list; `scripts/deploy_surface.py` fails if any Dockerfile in the repository copies a path outside `pyproject.toml`, `uv.lock`, `libs/*/src`, `apps/*/src`, or per-app manifests, and (where Docker is available) if a built image contains any excluded path.

## S3 Script behavior (each statement is a criterion; design section in parentheses)
- S3.1 `block.py` renders exactly the four-line message; every other script and hook emits blocks only through it (19.2).
- S3.2 `stage_state.py` is the only writer of `state.json`; it records a checksum; `exits <state>` lists transitions; every state has one; `abandon` works from any non-terminal state (12.4, 19.3).
- S3.3 `constraints.py` reports `path:line: RULE-ID message`; grandfathered baseline honored; the example rule is replaced by a rule registry with tests (7.2, B.1).
- S3.4 `budgets.py` enforces every numeric budget in `budgets.md` and fails on a constraint with no check (4.5, DEF-01).
- S3.5 `spec_coverage.py` reports living-spec anchors with no marked test (B.2).
- S3.6 `test_ratchet.py` fails on deleted or weakened assertions without the label, and `--quality` enforces the 7.8 rules.
- S3.7 `ordering.py` verifies each criterion's test fails at its own commit and passes at head, and the defect location check (7.8, 6.4).
- S3.8 `diff_coverage.py` fails below `coverage.diff.min` (7.8).
- S3.9 `pr_contract.py` implements 8.1 items 1 to 10 including signature verification against an allowed-signers list (fetched from GitHub, or a local file with `--signers`), the hash and ancestry checks, the co-author rejection, and the Trivial short path.
- S3.10 `compute_tier.py` applies the 6.5 rules (paths, AST-equivalence, string-constant-only) and the risk paths; emits the tier and, when standard without a work item, the bounce message.
- S3.11 `start.py` implements the 19.1 contextual table; `status.py` the 19.3 output; `accept.py` the 5.5 prepare and sign steps.
- S3.12 `post_merge.py`, `observe.py`, `audit_observations.py`, `vendored_check.py`, `loop_report.py`, `spec_check.py` behave per 3.2, 9.2, 7.7, 12.5, 11.3, 4.4.
- S3.14 Scripts that depend on an external service or tool fail closed when it is unavailable, or skip the dependent check with an explicit statement in their output; none passes silently (`pr_contract.py` signer fetch, `deploy_surface.py` image check).
- S3.13 Every script passes Ruff and Pyright strict under the generated project's configuration and has red-first tests in the template repository.

## S4 Hooks (11.1, 19.6)
- S4.1 Stage guards apply only on a branch bound to a work item (`state.json` records `branch`; the guard checks the current branch against it). Branch names are free, typically the ticket key; `make start` takes `TICKET=<key>` and uses it as the work-item id and default branch name. The nudge on unbound branches never blocks. Spikes are marked in `state.json` (`workflow: spike`), not by branch prefix.
- S4.2 The AskUserQuestion hook enforces the per-turn limits.
- S4.3 The Bash hook blocks agent-run `git commit` with `Accept:` or `Accept-Decision:` in the message.
- S4.4 The Stop hook runs `make green` semantics per stage, with the retry cap and escalation.

## S5 Template repository
- S5.1 `tests/test_generation.py` generates with `enable_delivery` true and false and asserts S1 to S2.
- S5.2 `tests/scenarios/` holds the deterministic scenarios from intent.md "done means", run against a generated project.
- S5.3 `README.md` and `docs/RATIONALE.md` describe the delivery scaffold to the human-facing standard.

## Non-goals restated
GCP, Docker, and Terraform files are unchanged except the `use_gcp and enable_delivery` allowlist line. No live Claude Code or GitHub verification.
