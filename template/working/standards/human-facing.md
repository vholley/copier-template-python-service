# Writing standard: text people read

Applies to README files, `docs/`, pull-request descriptions, commit messages, code
comments, decision records, and `decisions.md`.

The test for every document: an engineer without context on this codebase or this
change can read it and understand it without asking. The voice is plain and unadorned:
say the specific thing, not the general version of it.

## Rules, in priority order

1. Structure and substance. No opening that announces the document, no narration of its
   own structure, no inflated importance, no manufactured balance, no closing summary.
   Where a fact is missing, say so instead of writing plausible prose around the gap.
2. Sentence level. No "it is not X, it is Y" framing; no question posed and answered in
   the next sentence; no "serves as" or "stands as" for "is"; no trailing clause that
   explains a benefit; no vague attribution ("experts agree"); nothing promotional.
   Vary sentence length and openings.
3. Surface. Plain words. No filler intensifiers. Minimal em-dashes. The vendored `deslop`
   skill's reference list is the source for words to avoid; it runs on every
   human-facing artifact before a pull request.
4. Readability. Every term of art is defined at first use or linked to its definition.
   Every component named carries its path.

## Per document type

- Code comments explain why, never what. No comment that restates the line below it.
  Density ceiling per file in `budgets.md`.
- Commit messages: conventional-commit subject under 72 characters; body says what
  changed and why in two to four sentences; references the work item.
- Pull-request descriptions: the template in `.github/pull_request_template.md`. Intent
  and risk first, then the diff mapped to criteria, then links to evidence. Written for
  a reviewer who has not read the work item.
- Decision records and `decisions.md`: the five questions (what we decided, why, what we
  considered instead, if this turns out to be wrong, what it touches), each at most three
  sentences, no internal reference without a plain-word explanation beside it.
- README: for an engineer on their first day; enough to run the member without asking.

Checked mechanically: comment density, commit-message shape, PR description sections
(`make contract`), and `scripts/delivery/writing_check.py` (a small list of tells).
The reviewer agents ask: does this comment add information not in the line; is every
term of art defined; could an engineer restate this decision in one sentence.
