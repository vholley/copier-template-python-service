# Constraints

Every line here names the check that enforces it (D19): Ruff rule, import-linter
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

- INV-01 (check: constraints.py INV-01) [allow: shared.config, shared.logging_setup]: the environment is read only in the listed modules (and any module named `config.py`).
- INV-02 (check: ruff T20): no print() in library code; log through `shared.logging_setup`.
- PKG-01 (check: importlinter PKG-01): libs do not import apps.

## Protected paths

Changed only through a reviewed pull request; the agent cannot edit them in a session
(the test ratchet and review protect tests and the living spec instead, D37).

- working/architecture/**
- working/standards/**
- .claude/**
- scripts/**
- .github/**

## High-risk paths

Listed in `working/standards/budgets.md` (`high_risk_paths`); a change there gets the
reviewer's spec approval before implementation.
