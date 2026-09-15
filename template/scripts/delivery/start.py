"""`make start` / `/start`: the one entry point, contextual (19.1).

offers(repo) lists the answers that apply to the current branch and tree.
main(["--answer", KEY, "--ticket", ID, repo]) performs one.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from delivery import block, gitx, state, status
from delivery.block import fail

if TYPE_CHECKING:
    from collections.abc import Callable

ANSWERS = {
    "set-up": "Set the project up (what it is for, its members, its architecture)",
    "quick-change": "Make a quick change (typo, docs, config, dependency bump)",
    "change": "Add or change behavior",
    "bug-fix": "Fix a bug",
    "explore": "Explore first (a spike; nothing merges from it)",
    "opt-out": "Do not use the process for this work",
    "continue": "Continue the current work item",
    "abandon": "Abandon the current work item",
    "to-change": "Turn this spike into a change",
    "to-bug-fix": "Turn this spike into a bug fix",
    "keep-exploring": "Keep exploring",
    "attach": "Attach this branch to a new work item",
}
WORKFLOW_FOR = {
    "set-up": "project",
    "change": "change",
    "bug-fix": "change-defect",
    "explore": "spike",
}
PROJECT_INTENT_TEMPLATE = Path(".claude/skills/intent/templates/intent-project.md")
MORE = "working/README.md#start"


def _has_changes(repo: Path) -> bool:
    return gitx.run(repo, "status", "--porcelain", "--", "libs", "apps", check=False).strip() != ""


def _is_fresh(repo: Path) -> bool:
    """True while the project has no members: nothing to change yet, only to define.

    working/spec/README.md ships with the template and describes no member, so it
    does not count. The first app or the first spec member retires the answer.
    """
    if any((repo / "apps").glob("*/pyproject.toml")):
        return False
    spec = (repo / "working" / "spec").glob("*.md")
    return not [p for p in spec if p.name != "README.md"]


def offers(repo: Path) -> list[str]:
    """Answers that apply now (never 'new-project': that is copier's job)."""
    branch = gitx.current_branch(repo)
    try:
        bound = state.bound_item(repo, branch)
    except state.ConsistencyError:
        bound = None
    if bound:
        st = state.load_unchecked(repo, bound)
        return (
            ["to-change", "to-bug-fix", "keep-exploring"]
            if st.workflow == "spike"
            else ["continue", "abandon"]
        )
    if branch not in ("develop", "main") and _has_changes(repo):
        return ["quick-change", "attach"]
    base = ["quick-change", "change", "bug-fix", "explore", "opt-out"]
    return ["set-up", *base] if _is_fresh(repo) else base


_PROJECT_FALLBACK = (
    "# Intent: <title>\nid: <work-id>\nworkflow: project\nrisk: standard\n\n"
    "## What\n\n## Why\n\n## Members\n\n## Constraints\n\n"
    "## Non-goals\n\n## Done means\n\n## Open questions\n"
)


def _project_intent(repo: Path, item: str) -> str:
    """The stub for a project item, from the intent skill's template when it ships."""
    tpl = repo / PROJECT_INTENT_TEMPLATE
    text = tpl.read_text(encoding="utf-8") if tpl.exists() else _PROJECT_FALLBACK
    return text.replace("<work-id>", item).replace("<title>", item)


def _draft_intent(repo: Path, item: str, notes: str = "") -> None:
    d = state.item_dir(repo, item)
    workflow = state.load_unchecked(repo, item).workflow
    if workflow == "project":
        (d / "intent.md").write_text(_project_intent(repo, item), encoding="utf-8")
        return
    body = (
        f"# Intent: {item}\nid: {item}\nworkflow: {workflow}\nrisk: standard\n\n"
        "## What\n\n## Why\n\n## Constraints\n\n## Non-goals\n\n"
        "## Done means\n\n## Open questions\n"
    )
    if notes:
        body += f"\n## Notes carried from the spike\n{notes}"
    (d / "intent.md").write_text(body, encoding="utf-8")


def _need_ticket(ticket: str | None) -> int | None:
    if ticket:
        return None
    return fail(
        "start",
        "a ticket or name is required",
        "the work item id and branch name come from it",
        ["make start TICKET=<key>"],
        MORE,
    )


# ---------------------------------------------------------------- actions


def _quick_change(repo: Path, ticket: str | None) -> int:
    if gitx.current_branch(repo) in ("develop", "main"):
        gitx.run(repo, "checkout", "-q", "-b", ticket or "quick-change")
    print(f"On {gitx.current_branch(repo)}. Edit, commit, open a PR with a one-line description.")
    return 0


def _new_item(answer: str) -> Callable[[Path, str | None], int]:
    def run(repo: Path, ticket: str | None) -> int:
        if (code := _need_ticket(ticket)) is not None:
            return code
        assert ticket is not None  # noqa: S101 - narrowed by _need_ticket
        if gitx.branch_exists(repo, ticket):
            gitx.run(repo, "checkout", "-q", ticket)
        else:
            gitx.run(repo, "checkout", "-q", "-b", ticket)
        workflow = WORKFLOW_FOR[answer]
        state.create(repo, ticket, workflow, ticket)
        if workflow == "spike":
            (state.item_dir(repo, ticket) / "notes.md").write_text(
                "# Spike notes\n", encoding="utf-8"
            )
            print(
                f"Spike {ticket} on branch {ticket}. Nothing merges from here; "
                "run make start when you know what to build."
            )
        elif workflow == "project":
            _draft_intent(repo, ticket)
            print(f"Project {ticket} on branch {ticket}. Next: /intent, then /architect")
        else:
            _draft_intent(repo, ticket)
            print(f"Work item {ticket} on branch {ticket}. Next: /intent")
        return 0

    return run


def _attach(repo: Path, ticket: str | None) -> int:
    if (code := _need_ticket(ticket)) is not None:
        return code
    assert ticket is not None  # noqa: S101
    branch = gitx.current_branch(repo)
    state.create(repo, ticket, "change", branch)
    _draft_intent(repo, ticket)
    print(
        f"Work item {ticket} bound to {branch}. Next: /intent "
        "(the ordering check is waived for bounced items)"
    )
    return 0


def _convert(answer: str) -> Callable[[Path, str | None], int]:
    def run(repo: Path, _ticket: str | None) -> int:
        item = state.bound_item(repo, gitx.current_branch(repo))
        if item is None:
            return fail(
                "start",
                "no spike on this branch",
                "conversion applies to a bound spike",
                ["make status"],
                MORE,
            )
        workflow = "change" if answer == "to-change" else "change-defect"
        state.rebind(repo, item, workflow, "intent")
        notes_path = state.item_dir(repo, item) / "notes.md"
        _draft_intent(repo, item, notes_path.read_text() if notes_path.exists() else "")
        print(f"{item} is now a {workflow}. Next: /intent")
        return 0

    return run


def _continue(repo: Path, _ticket: str | None) -> int:
    print(status.report(repo))
    return 0


def _abandon(repo: Path, _ticket: str | None) -> int:
    item = state.bound_item(repo, gitx.current_branch(repo))
    if item:
        state.abandon(repo, item)
        print(f"{item} abandoned and archived to working/history/{item}/")
    return 0


def _opt_out(_repo: Path, _ticket: str | None) -> int:
    print(
        'To opt out: make opt-out [REASON="..."], then make accept STAGE=opt-out in your shell. '
        "To rejoin: make start"
    )
    return 0


def _noop(_repo: Path, _ticket: str | None) -> int:
    return 0


ACTIONS: dict[str, Callable[[Path, str | None], int]] = {
    "set-up": _new_item("set-up"),
    "quick-change": _quick_change,
    "change": _new_item("change"),
    "bug-fix": _new_item("bug-fix"),
    "explore": _new_item("explore"),
    "attach": _attach,
    "to-change": _convert("to-change"),
    "to-bug-fix": _convert("to-bug-fix"),
    "continue": _continue,
    "abandon": _abandon,
    "opt-out": _opt_out,
    "keep-exploring": _noop,
}


@block.guard_unborn
def main(argv: list[str]) -> int:
    """Entry point: --list, or --answer KEY [--ticket ID]."""
    rest = [
        a
        for i, a in enumerate(argv)
        if not a.startswith("--") and argv[i - 1] not in ("--answer", "--ticket")
    ]
    repo = Path(rest[0]) if rest else Path.cwd()
    if "--list" in argv or "--answer" not in argv:
        print("What are you here to do?")
        for key in offers(repo):
            print(f"  {key:15} {ANSWERS[key]}")
        return 0
    answer = argv[argv.index("--answer") + 1]
    ticket = argv[argv.index("--ticket") + 1] if "--ticket" in argv else None
    if answer not in offers(repo):
        return fail(
            "start",
            f"{answer!r} does not apply here",
            "make start offers only what applies to this branch",
            ["make start  (to see the answers that apply)"],
            MORE,
        )
    return ACTIONS[answer](repo, ticket)


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
