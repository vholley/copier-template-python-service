#!/usr/bin/env bash
# Copy the delivery system into a project generated from an earlier template version.
# Usage: scripts/migrate-to-delivery.sh --from <path to a freshly generated project>
set -euo pipefail

SRC=""
while [ $# -gt 0 ]; do
  case "$1" in
    --from) SRC="$2"; shift 2 ;;
    *) echo "usage: $0 --from <generated-project>"; exit 2 ;;
  esac
done
[ -n "$SRC" ] || { echo "usage: $0 --from <generated-project>"; exit 2; }
[ -d "$SRC/working" ] || { echo "$SRC does not look like a project with the delivery system"; exit 2; }

for d in working scripts/delivery scripts/hooks .claude; do
  mkdir -p "$(dirname "$d")"
  cp -R "$SRC/$d" "$d"
done
cp "$SRC/.dockerignore" .dockerignore
mkdir -p .github/workflows .github/actions/setup
for w in delivery-checks review-agents spec-draft post-merge entropy-audit; do
  cp "$SRC/.github/workflows/$w.yml" ".github/workflows/$w.yml"
done
cp "$SRC/.github/actions/setup/action.yml" .github/actions/setup/action.yml
cp "$SRC/MIGRATION.md" MIGRATION.md

echo "Copied: working/, scripts/delivery/, scripts/hooks/, .claude/, .dockerignore, delivery workflows."
echo "Files the template replaces; merge by hand where marked modified:"
for f in Makefile .github/workflows/ci.yml AGENTS.md .github/pull_request_template.md .pre-commit-config.yaml pyproject.toml; do
  if [ -f "$f" ] && ! cmp -s "$f" "$SRC/$f"; then
    echo "  $f: modified (compare with $SRC/$f)"
  else
    cp "$SRC/$f" "$f" 2>/dev/null && echo "  $f: replaced" || echo "  $f: missing in source"
  fi
done
echo "Next: make hooks; register your SSH signing key; read working/README.md"
