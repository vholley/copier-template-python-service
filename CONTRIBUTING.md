# Contributing to copier-template-python-service

This is a personal [copier](https://copier.readthedocs.io/) template. Changes to it affect every project that runs `copier update --trust`. Test before merging.

## Testing a template change

Copier can copy directly from a local directory. `enable_delivery` is the widest axis -- it
changes roughly half the tree -- so test it in both positions, then the framework and cloud
combinations:

```sh
# 0. The base template on its own, with no delivery system
copier copy --trust . /tmp/test-plain \
  -d project_name=test-plain -d enable_delivery=false
cd /tmp/test-plain && ./scripts/bootstrap.sh && make ci && cd -
```

Then the delivery-enabled combinations:

```sh
# 1. Generic Python — the default path (minimal, no GCP)
copier copy --trust . /tmp/test-minimal \
  -d project_name=test-minimal -d use_gcp=false -d app_framework=minimal -d include_docker=false
cd /tmp/test-minimal && ./scripts/bootstrap.sh && make ci && cd -

# 2. FastAPI, no GCP
copier copy --trust . /tmp/test-fastapi \
  -d project_name=test-fastapi -d use_gcp=false -d app_framework=fastapi -d include_docker=false
cd /tmp/test-fastapi && ./scripts/bootstrap.sh && make ci && cd -

# 3. GCP + FastAPI (full stack)
copier copy --trust . /tmp/test-gcp \
  -d project_name=test-gcp -d use_gcp=true -d gcp_project_dev=my-project-dev -d gcp_project_prod=my-project-prod -d app_framework=fastapi
cd /tmp/test-gcp && ./scripts/bootstrap.sh && make ci && cd -

# 4. GCP + minimal
copier copy --trust . /tmp/test-gcp-min \
  -d project_name=test-gcp-min -d use_gcp=true -d gcp_project_dev=my-project-dev -d gcp_project_prod=my-project-prod -d app_framework=minimal
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

## Commit conventions

Commits carry no LLM co-author trailer. Each commit is one contributor's, and the
author field says who that is. If a tool helped write it, that is between you and
the tool -- the history records the person accountable for the change, not the
means.

CI enforces it:

```sh
git log origin/main..HEAD --format=%B | grep -q Co-Authored-By && exit 1
```

Messages follow Conventional Commits, as the generated projects do.

## Citations go stale

Do not cite the artefacts a process produces, in this repository or in the projects
generated from it. That means design-document sections, decision numbers, criteria
identifiers, and ticket or issue references.

They read as precision and decay into noise. The document gets renamed, superseded or
deleted; the decision is revised by a later one; the tracker is migrated and the numbers
are reassigned. The citation keeps pointing, and a reader who chases it learns nothing
and cannot tell whether the surrounding claim is still true. Code outlives the scaffolding
that produced it, and it is copied into projects that never had that scaffolding at all —
a generated project has no design document to look a decision number up in.

This branch shipped 37 such references before they were removed: 24 decision numbers,
10 design-section pointers, and 3 in the repository's own tests.

Write the reason instead of a pointer to it. `# bind to a branch that exists` survives
every rename; `# bind to a branch that exists (D18)` does not. If the reasoning is too
long to restate, it belongs in a docstring or a comment near the code, not in a reference
to somewhere else.
