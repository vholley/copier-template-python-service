# Contributing to copier-template-python-service

This is a personal [copier](https://copier.readthedocs.io/) template. Changes to it affect every project that runs `copier update --trust`. Test before merging.

## Testing a template change

Copier can copy directly from a local directory. Test all four combinations of answers to catch regressions across the conditional paths:

```sh
# 1. Generic Python — the default path (minimal, no GCP)
copier copy --trust . /tmp/test-minimal \
  -- project_name=test-minimal use_gcp=false app_framework=minimal include_docker=false
cd /tmp/test-minimal && ./scripts/bootstrap.sh && make ci && cd -

# 2. FastAPI, no GCP
copier copy --trust . /tmp/test-fastapi \
  -- project_name=test-fastapi use_gcp=false app_framework=fastapi include_docker=false
cd /tmp/test-fastapi && ./scripts/bootstrap.sh && make ci && cd -

# 3. GCP + FastAPI (full stack)
copier copy --trust . /tmp/test-gcp \
  -- project_name=test-gcp use_gcp=true gcp_project_dev=my-project-dev gcp_project_prod=my-project-prod app_framework=fastapi
cd /tmp/test-gcp && ./scripts/bootstrap.sh && make ci && cd -

# 4. GCP + minimal
copier copy --trust . /tmp/test-gcp-min \
  -- project_name=test-gcp-min use_gcp=true gcp_project_dev=my-project-dev gcp_project_prod=my-project-prod app_framework=minimal
cd /tmp/test-gcp-min && ./scripts/bootstrap.sh && make ci && cd -
```

Clean up after testing:

```sh
rm -rf /tmp/test-minimal /tmp/test-fastapi /tmp/test-gcp /tmp/test-gcp-min
```

## What constitutes a breaking change

A breaking change is one that, when an existing project runs `copier update --trust`, causes unexpected file deletions, renames, or merge conflicts that require manual resolution:

- **Renaming or removing a copier question** — existing projects have the old answer stored in `.copier-answers.yml`. Rename causes copier to re-ask; remove drops the value silently.
- **Removing a file the template previously generated** — copier update deletes it from the existing project.
- **Changing `_answers_file`** — breaks copier's ability to find stored answers for future updates.

Non-breaking: adding new questions (they get defaults), adding new files, editing file content, changing question help text.

## Documentation

Update `docs/RATIONALE.md.jinja` alongside any structural change (new tool, new pattern, removed component). RATIONALE explains *why* each choice was made; it should stay current with the template.
