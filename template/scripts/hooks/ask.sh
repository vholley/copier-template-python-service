#!/usr/bin/env sh
# Thin wrapper (D36): all logic is in scripts/delivery/hooks.py
exec uv run --quiet python -m delivery.hooks ask "$(git rev-parse --show-toplevel)"
