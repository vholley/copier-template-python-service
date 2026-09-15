---
description: What to change when a Ruff rule fails; loaded when the linter reports a rule listed here
paths:
  - "libs/**/*.py"
  - "apps/**/*.py"
---

Ruff's messages are fixed. When one of these rules fails, this is the change:

- C901 (complexity over budget): split the function at its decision points into named helpers; the budget is `complexity.max` in `working/standards/budgets.md`.
- PLR0913 (too many arguments): group related parameters into a dataclass, or split the function.
- PLR0915 / PLR0912 / PLR0911 (too many statements / branches / returns): extract the branch bodies into helpers; a dispatch table beats a chain of `if`.
- TID251 (banned import): the message names the replacement module and an example file; use it.
- TID253 (banned module-level import): import inside the function that needs it, or remove the dependency.
- T20 (print in library code): log through `shared.logging_setup`; only declared CLI modules print.
- S603 / S607 (subprocess): use a fixed executable path (`shutil.which`) and a list argument, never a shell string.
- D (docstrings): one sentence stating what the object does, Google style; do not restate the signature.
- ANN (annotations): annotate every parameter and return; use `object` rather than `Any` when the type is unknown.
