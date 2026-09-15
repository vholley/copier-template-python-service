---
name: architect
description: New project, after the project intent is signed. Produce the architecture overview, the constraints with their checks, the standards as instantiated for this project, budgets with numbers, and the criteria templates. Builds nothing.
---

1. Run the explorer agent (Agent tool, `explorer`) on the generated repository to map members and layers.
2. `working/architecture/overview.md`: members and what each is for, the layer model, the provider module for cross-cutting concerns, where configuration enters. Within `area_doc.max_lines`.
3. `working/architecture/constraints.md`: each invariant as `- ID (check: tool id) [params]: text`. A constraint without a check does not go in. Add the import-linter contract per app in `pyproject.toml`. Enable the example rule only if the project wants it.
4. `working/standards/budgets.md`: numbers, decided with the engineer (each number that departs from the default is a decision entry).
5. `working/standards/criteria-templates.md`: adjust required classes if this project needs more.
6. Decision records for every choice that is expensive to reverse (`../spec/templates/decision.md`), one artifact per turn for acceptance.
7. Present each artifact separately; the approval of the whole is the architecture pull request. Next: `/decompose`.
