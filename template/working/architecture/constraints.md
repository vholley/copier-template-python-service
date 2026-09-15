# Constraints

Every line here names the check that enforces it: Ruff rule, import-linter
contract, or a rule in `scripts/delivery/constraints.py`. A rule with no check does
not belong in this file; it belongs in the standards. `make constraints` and
`make budgets --constraints` enforce this file; violations that existed at adoption
are listed in `constraints-baseline.txt`, which may only shrink.

## Layers

Within a member, code depends forward only: types → config → repo → service → runtime → ui.
Cross-cutting concerns (logging, telemetry) enter through a single provider module.

- LAYER-<app> (check: importlinter LAYER-<app>): each app declares its layers contract
  in `pyproject.toml` (`scripts/new-app.sh` writes it).

## Invariants

The project decides its invariants; none are active by default. A rule runs only
when listed here. Available in `scripts/delivery/constraints.py`:

<!-- INV-01: the environment is read only in the listed modules (plus any config.py).
     Enable by uncommenting and editing the allow list:
- INV-01 (check: constraints.py INV-01) [allow: shared.config, shared.logging_setup]: the environment is read only in the listed modules.
-->

- PKG-01 (check: importlinter PKG-01): libs do not import apps. The contract is written by `scripts/new-app.sh` with the first app and extended with each one after; it does not exist while the project has none.

## Protected paths

Changed only through a reviewed pull request; the agent cannot edit them in a session
(the test ratchet and review protect tests and the living spec instead). A branch bound
to a `project` item is that pull request, so the guard allows these edits there: `make
start` offers set-up for a new project and process-change for the process itself.

- working/architecture/**
- working/standards/**
- .claude/**
- scripts/**
- .github/**

## High-risk paths

Listed in `working/standards/budgets.md` (`high_risk_paths`); a change there gets the
reviewer's spec approval before implementation.
