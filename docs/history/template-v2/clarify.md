# Clarify: template-v2

## Contradictions

- C1: The design (5.5, DEC-02) verifies acceptance by commit author: "the commit author is not the agent identity." In an interactive Claude Code session, commits are authored under the engineer's git identity, so author identity cannot distinguish a human acceptance from one the agent made on the engineer's behalf. The check as written passes agent-made acceptances.
  proposed resolution: signed acceptance commits with a software SSH key protected per use (passphrase not cached, or an agent that confirms each use); CI verifies signatures on acceptance commits only, against the org members' GitHub-registered signing keys fetched at run time; no repository-wide signing requirement; the agent is blocked in-session from committing any message containing `Accept:`; the trailer binds to the artifact's SHA-256. Full mechanism in decisions.md D2.
  resolution [human]: accepted, with the addition that the agent prepares the acceptance commit (message and staging) and the engineer signs it (D2, D6).

- C2: pytest exits with code 5 when it finds no tests at all. The template's `make test` deliberately treats that as success, because a freshly generated project has no code yet and would otherwise fail CI on its first day. The design uses test results as the evidence that criteria are met (`make green` must pass before a turn ends, and every criterion maps to a test). If `make green` inherited the same tolerance, a member with zero tests would report "green" and an item could be verified as done with no tests behind it. The two targets want opposite behavior for the same exit code.
  proposed resolution: keep both targets and give them different jobs. `make test` stays as the template has it, workspace-wide, exit 5 tolerated, so a new project's CI passes. `make green` runs per enabled member and treats exit 5 as a failure with the message "no tests collected in <member>; the red stage requires at least one test per criterion." A fresh project has no enabled members, so nothing changes on day one; the first member to be enabled is the first place a missing test is refused.
  resolution [human]: use the proposed resolution (D3).

- C3: The template gitignores `docs/` and its README states `copier update` will not recreate ignored files. The design requires `docs/` tracked. Already decided (register #55) and applied in the design; recorded here so the resolution is in the chain.
  resolution [human]: accepted in design 17.5

## Questions

- Q1: Acceptance commit format under the template's conventional-commit hook.
  options: `chore(work-<id>): accept intent` with the `Accept:` trailer in the body (no hook change) | a new type `accept(work-<id>): intent` added to the allowed types
  answer [human]: the `accept` type, added to the conventional-commit hook's allowed types.
  tag: local

- Q2: Should the delivery scaffold be unconditional in the template, or behind an `enable_delivery` copier question?
  options: unconditional (every generated project has it; simpler template, fewer conditionals) | opt-in question defaulting to true
  recommendation: unconditional. An opt-out path is a bypass with no label.
  answer [human]: add `enable_delivery` (default true). Every part of the template must be independently selectable; a project without GCP infrastructure may still need the delivery scaffold. The delivery scaffold depends on no other option; only the log-read allowlist renders under `use_gcp and enable_delivery`.
  tag: local

- Q3: This is a breaking change for projects already generated from the template (docs/ becomes tracked; Makefile, CI, AGENTS.md, and the PR template are replaced). Do any such projects exist that will run `copier update` from this version, and should the template carry a migration note for them?
  options: none exist, no note needed | some exist, add a MIGRATION.md and a `_message_after_update` in copier.yaml
  answer [human]: projects may exist; do what is reasonable. Resolution: `MIGRATION.md`, a `_message_after_update` pointing at it, and `scripts/migrate-to-delivery.sh` that un-ignores `docs/`, restores the template docs, and reports which replaced files (Makefile, CI, AGENTS.md, PR template) the project had modified.
  tag: doc-gap
  doc-gap-target: template README.md

- Q4: Should the headless CI identity be a dedicated bot account (name and email fixed in the workflows) so CI can recognize agent-authored commits by author, in addition to the Co-Authored-By check in C1?
  options: yes, dedicated identity | no, rely on the Co-Authored-By check only
  recommendation: yes. It is one line in each workflow and it makes DEC-02 deterministic for headless runs.
  answer [human]: changes are never co-authored by an LLM; every change is captured under, and is the sole responsibility of, one engineer. Consequences: `includeCoAuthoredBy` is off in the shipped settings, CI rejects any `Co-Authored-By` trailer naming an LLM, and the question of how headless runs' output is captured is reopened as Q5.

- Q5: Headless CI runs (spec draft on intent acceptance, entropy audit PRs, break-glass follow-up items) currently commit under a bot identity. That conflicts with "every change is captured under one engineer."
  options: (a) headless runs never commit: they post drafts as check outputs and PR comments, and `make pull-draft` lets the engineer's session bring a draft into the branch under the engineer; audit findings become draft work items, not PRs | (b) bot commits are allowed only for files under `.work/` and `working/history/`, never source, and an engineer adopts them by committing on top | (c) keep bot commits, treat the bot as a named non-human contributor and exclude it from the responsibility rule
  recommendation: (a). It keeps the rule absolute and costs one Makefile target; it also removes the bot's write access to branches entirely.
  answer [human]: none of the three as framed. There is no bot identity. The LLM is a tool, not an engineer; every commit it makes is under an engineer's identity. Resolution: engineer-triggered headless runs commit with the triggering engineer as author; runs with no triggering engineer (scheduled audit) do not commit and produce drafts for an engineer to adopt; headless runs can never sign, so they can never accept.
  tag: durable
  doc-gap-target: working/architecture/decisions (principle 1.7)
  tag: local

## Assumptions (not asked)

- A1: Python 3.14 is installable in the sandbox via `uv python install` and copier is installable via pip.
  risk: if not, generation tests run on 3.13 and the template's default stays 3.14 untested here.
  provenance: observed (overseer confirms both are installable)
  reviewed [human]: yes
  tag: local

- A2: copier supports `_skip_if_exists` for project-owned files and treats missing files as intentional deletes on update.
  risk: if `_skip_if_exists` behaves differently from what I recall, TPL-02 fails and the split between managed and project-owned files needs another mechanism.
  provenance: inferred (the template README states the missing-file behavior; `_skip_if_exists` is recalled and will be verified against the copier docs and by TPL-02 before the design is considered correct)
  reviewed [human]: yes, believed correct; verify in plan step 1
  tag: local

- A3: import-linter's `layers`, `forbidden`, and `independence` contract types and their `pyproject.toml` syntax are as written in Appendix B.1.
  risk: syntax errors in generated config fail `make ci` on every new project.
  provenance: inferred (recalled; verified by installing the pinned version and running it in plan step 3)
  reviewed [human]: yes; verify in plan step 3
  tag: local

- A4: Claude Code agent frontmatter accepts a `tools:` list with Bash patterns as sketched in Appendix C.3, and hooks in `.claude/settings.json` use the format in C.1.
  risk: a syntax error means the evaluator has broader tools than designed, or hooks do not fire. Cannot be observed in the sandbox.
  provenance: inferred (from the hooks reference read on 2026-09-11; agent frontmatter not re-verified)
  reviewed [human]: cannot verify; must be verified independently. Shape verified 2026-09-13 against the subagent reference (name, description, tools, model, disallowedTools, hooks, maxTurns) and the skills/rules documentation (name, description, argument-hint, context, agent; rules with `paths:`); live behavior is milestone 2 (DONE-05, EXP-05)
  tag: local

- A5: GitHub Actions workflows can only be validated for YAML shape here, not executed.
  risk: a workflow that is well-formed but wrong at runtime is found in milestone 2, not here.
  provenance: observed (sandbox has no runner)
  reviewed [human]: yes; not a major issue
  tag: local

- A6: SSH commit signing and `git verify-commit` against an allowed-signers file work in the sandbox (git 2.43, openssh-client installed during S5).
  risk: none; verified before the S5 tests were written.
  provenance: observed
  reviewed [human]: recorded during build
  tag: local

- A7: real signing uses the same tool as the tests: git's SSH signing shells out to `ssh-keygen -Y sign` and verification to `ssh-keygen -Y verify`, so OpenSSH is required on engineer machines and CI runners.
  risk: a machine without OpenSSH 8.8+ or git 2.34+ cannot sign or verify; bootstrap.sh checks both versions and reports.
  provenance: observed (git documentation and the sandbox run)
  reviewed [human]: recorded during build
  tag: doc-gap
  doc-gap-target: docs/SETUP.md (prerequisites)

## Doc-gaps found during spec (improvement loop entries)

- G1: criteria.json was written without the `failure` class that the criteria template requires for `new-behavior`. Cause: the check that enforces required classes (`spec_check.py`, SPEC-01) does not exist yet because this work item is the one that builds it, and the manual substitute (walking the template's required-class list) was not done. Fix applied: C37 to C39 added; S2.3 gained `spec_check.py` and `deploy_surface.py`, which the script list had omitted; S3.14 added. Lesson recorded in working/README.md draft: when a check the process relies on does not exist yet, its checklist is walked by hand and that walk is noted in the artifact.
  tag: doc-gap
  doc-gap-target: working/standards/criteria-templates.md (add the "no check yet" rule)
