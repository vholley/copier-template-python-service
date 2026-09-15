# Writing for people

Applies to: README files, `docs/`, pull request descriptions, code comments,
commit messages, release notes, decision records, and the prose in
decisions.md.

The test for every document: an engineer on their first day, who has not read
the design or the conversation that produced the change, can read it and act
on it without asking.

## Principles

1. Say the specific thing. No opener that announces the document, no summary
   that repeats it, no closing that reassures.
2. One idea per sentence. Plain words. A term of art is defined where it first
   appears or linked to where it is defined.
3. Explain why, not what. Code says what.
4. Where a fact is missing, say so. Never fill a gap with plausible prose.
5. Name paths. "the contract check" is `scripts/delivery/pr_contract.py`.
6. No manufactured emphasis: no "not just X but Y", no question you answer
   yourself, no "serves as", no trailing "which ensures...". The `deslop`
   skill removes these; the writing check (`make green` on docs) flags them.

## By document type

- Code comments: why, never what. Density ceiling in `budgets.md`. A comment a
  new engineer could not act on is deleted.
- Commit messages: imperative subject under 72 characters; a body of two to
  four sentences on what changed and why; the work item id.
- Pull request descriptions: the template's sections, in order. Intent and
  risk first. The diff mapped to criteria. Evidence linked, not pasted.
- README: enough to run the thing without asking anyone.
- Decision records: the five questions (what we decided, why, what we
  considered instead, if this turns out to be wrong, what it touches), at most
  three sentences each.

## Voice

Neutral and direct. No persona. Varied sentence length. The `deslop` skill's
reference list of AI tells is the source for what to avoid; it has a review
date and the weekly audit checks it.
