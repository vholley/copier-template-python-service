# Migrating an existing project to this template version

This version adds the delivery system. If your project was generated from an earlier
version, `copier update --trust --skip-answered` brings in the new files, and these
files that the template replaces will show conflicts if you changed them:

- `Makefile` (new targets are added; your targets stay if you merge them back)
- `.github/workflows/ci.yml` (three delivery steps are added)
- `AGENTS.md` (replaced; your project-specific content goes below the marker line)
- `.github/pull_request_template.md` (replaced)
- `.pre-commit-config.yaml` (delivery hooks and the `accept` commit type are added)
- `pyproject.toml` (Ruff rules, import-linter, a pytest marker, dev dependencies are added)

`scripts/migrate-to-delivery.sh --from <a freshly generated project>` does the
mechanical part for you: it copies `working/`, `scripts/delivery/`, `scripts/hooks/`,
`.claude/`, `.dockerignore`, and the delivery workflows into your project, and prints
which of the replaced files you had modified so you can merge those by hand.

Afterward: `make hooks`, register your SSH key as a GitHub signing key, and read
`working/README.md`.
