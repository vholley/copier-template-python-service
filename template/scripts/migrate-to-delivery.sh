#!/usr/bin/env bash
# Migrate a project generated from an earlier template version (MIGRATION.md).
# Usage: scripts/migrate-to-delivery.sh [--from <generated-project-with-delivery>]
# With --from, files are copied from that project; otherwise from this project's
# own template output (after copier update).
set -euo pipefail

SRC=""
if [ "${1:-}" = "--from" ]; then SRC="$2"; fi
SRC="${SRC:-.}"

echo "== creating working/ (existing files are kept)"
for f in README.md commands.toml observations.md standards/model-facing.md standards/human-facing.md \
         standards/criteria-templates.md standards/budgets.md architecture/overview.md \
         architecture/constraints.md architecture/constraints-baseline.txt architecture/decisions/README.md \
         spec/README.md history/.gitkeep; do
  if [ ! -e "working/$f" ] && [ -e "$SRC/working/$f" ]; then
    mkdir -p "$(dirname "working/$f")"
    cp "$SRC/working/$f" "working/$f"
    echo "   added working/$f"
  fi
done

echo "== replaced files you had modified (merge by hand):"
for f in Makefile .github/workflows/ci.yml AGENTS.md .github/pull_request_template.md .pre-commit-config.yaml; do
  if [ -e "$f" ] && git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
    if ! git diff --quiet HEAD -- "$f" 2>/dev/null; then
      echo "   $f: modified locally"
    fi
  fi
done

if [ -x scripts/restore-from-template.sh ]; then
  echo "== restoring docs/ from the template"
  scripts/restore-from-template.sh >/dev/null 2>&1 || true
fi
echo "done. Next: make hooks; see MIGRATION.md"
