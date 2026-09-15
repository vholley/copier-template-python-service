"""Classify a pull request from its diff, never from what anyone said.

  trivial   only trivial-eligible paths, or Python that is AST-identical once
            docstrings and comments are stripped, or string-constant-only
            changes not quoted by the living spec; all under budget, no
            protected paths, no dependency additions
  high      any changed file on a high-risk path
  standard  everything else
Prints `tier: <tier>` and one `because: ...` line per reason. A standard change
on a branch with no work item also prints the bounce block on stderr.
Run: uv run python -m delivery.compute_tier --base REF [repo]. Exit 0, or 2 on usage.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from delivery import gitx, paths, state
from delivery.block import render

PROTECTED_PREFIXES = ("working/architecture/", "working/standards/", ".claude/", "scripts/")
IGNORED_PREFIXES = (".work/", "working/history/")


@dataclass
class Tier:
    """Classification result."""

    tier: str
    reasons: list[str] = field(default_factory=lambda: [])
    lines: int = 0


def _glob_to_re(pattern: str) -> re.Pattern[str]:
    out = "^"
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
            continue
        if pattern.startswith("**", i):
            out += ".*"
            i += 2
            continue
        if c == "*":
            out += "[^/]*"
        elif c == "?":
            out += "[^/]"
        else:
            out += re.escape(c)
        i += 1
    return re.compile(out + "$")


def matches_any(path: str, patterns: list[str]) -> bool:
    """True when path matches one of the glob patterns (** spans directories)."""
    return any(_glob_to_re(p).match(path) for p in patterns)


def _strip_docstrings(tree: ast.AST) -> ast.AST:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            and node.body
        ):
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                node.body = node.body[1:] or [ast.Pass()]
    return tree


def ast_identical(old: str, new: str) -> bool:
    """True when the two sources differ only in comments, docstrings, or formatting."""
    try:
        return ast.dump(_strip_docstrings(ast.parse(old))) == ast.dump(
            _strip_docstrings(ast.parse(new))
        )
    except SyntaxError:
        return False


def string_only_diff(old: str, new: str) -> list[str] | None:
    """Changed string values when the sources differ only in string constants, else None."""
    try:
        a, b = ast.parse(old), ast.parse(new)
    except SyntaxError:
        return None
    changed: list[str] = []
    for x, y in zip(ast.walk(a), ast.walk(b), strict=False):
        if type(x) is not type(y):
            return None
        if not (isinstance(x, ast.Constant) and isinstance(y, ast.Constant)) or x.value == y.value:
            continue
        if not (isinstance(x.value, str) and isinstance(y.value, str)):
            return None
        changed.extend([x.value, y.value])
    # Structure must match once string values are normalized.
    norm_a = re.sub(r"Constant\(value='[^']*'\)", "S", ast.dump(a))
    norm_b = re.sub(r"Constant\(value='[^']*'\)", "S", ast.dump(b))
    return changed if norm_a == norm_b else None


def _spec_text(repo: Path) -> str:
    return "\n".join(p.read_text() for p in (repo / paths.SPEC_DIR).glob("**/*.md"))


@dataclass
class Diff:
    """What the classifier looks at."""

    files: list[str]
    lines: int
    budgets: paths.Budgets


def _diff(repo: Path, base: str) -> Diff:
    names = gitx.run(repo, "diff", "--name-only", base, "HEAD", check=False).split()
    files = [f for f in names if not f.startswith(IGNORED_PREFIXES)]
    lines = 0
    if files:
        numstat = gitx.run(repo, "diff", "--numstat", base, "HEAD", "--", *files, check=False)
        for ln in numstat.splitlines():
            parts = ln.split("\t")
            if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
                lines += int(parts[0]) + int(parts[1])
    return Diff(files, lines, paths.read_budgets(repo))


def _adds_dependency(repo: Path, base: str, files: list[str]) -> bool:
    manifests = [f for f in files if f.endswith("pyproject.toml")]
    if not manifests:
        return False
    added = gitx.run(repo, "diff", base, "HEAD", "--", *manifests, check=False)
    return re.search(r"^\+\s*\"[A-Za-z0-9_.-]+[>=<~!]", added, re.M) is not None


def _python_rule(repo: Path, base: str, d: Diff) -> Tier | None:
    """The AST-identical and string-only rules; None when neither applies."""
    py = [f for f in d.files if f.endswith(".py")]
    if not py:
        return None
    olds = {f: gitx.run(repo, "show", f"{base}:{f}", check=False) for f in py}
    news = {f: (repo / f).read_text() if (repo / f).exists() else "" for f in py}
    trivial_budget = d.budgets.get("diff.trivial.max_lines") or 0
    if all(olds[f] and ast_identical(olds[f], news[f]) for f in py) and d.lines <= trivial_budget:
        return Tier(
            "trivial", ["Python changes are comments, docstrings, or formatting only"], d.lines
        )
    strings: list[str] = []
    for f in py:
        diff = string_only_diff(olds[f], news[f]) if olds[f] else None
        if diff is None:
            return None
        strings.extend(diff)
    if d.lines > (d.budgets.get("diff.string_only.max_lines") or 0):
        return None
    spec = _spec_text(repo)
    quoted = [s for s in strings if s and s in spec]
    if quoted:
        return Tier("standard", [f"string {quoted[0]!r} is quoted by the living spec"], d.lines)
    return Tier(
        "trivial", ["only string constants changed, none quoted by the living spec"], d.lines
    )


def _precedence_rules(repo: Path, base: str, d: Diff) -> Tier | None:
    """Rules that decide before the path and Python rules, in order."""
    high = [f for f in d.files if matches_any(f, d.budgets.lists.get("high_risk_paths", []))]
    if high:
        return Tier("high", [f"high-risk path {high[0]}"], d.lines)
    if not d.files:
        return Tier("trivial", ["no changes"], d.lines)
    if any(f.startswith(PROTECTED_PREFIXES) for f in d.files):
        return Tier("standard", ["touches a protected path"], d.lines)
    if _adds_dependency(repo, base, d.files):
        return Tier("standard", ["adds a dependency"], d.lines)
    return None


def _path_rule(d: Diff) -> Tier | None:
    """Trivial when every file is on a trivial-eligible path and the diff is under budget."""
    trivial_globs = d.budgets.lists.get("trivial_paths", [])
    budget = d.budgets.get("diff.trivial.max_lines") or 0
    if all(matches_any(f, trivial_globs) for f in d.files):
        if d.lines <= budget:
            return Tier("trivial", ["only trivial-eligible paths"], d.lines)
        return Tier(
            "standard", [f"trivial paths but {d.lines} lines > budget {int(budget)}"], d.lines
        )
    non_py = [f for f in d.files if not f.endswith(".py")]
    if not all(matches_any(f, trivial_globs) for f in non_py):
        return Tier("standard", ["non-Python source changed"], d.lines)
    return None


def classify(repo: Path, base: str) -> Tier:
    """Apply the 6.5 rules to the diff base..HEAD, in order of precedence."""
    d = _diff(repo, base)
    return (
        _precedence_rules(repo, base, d)
        or _path_rule(d)
        or _python_rule(repo, base, d)
        or Tier("standard", ["changes behavior"], d.lines)
    )


def main(argv: list[str]) -> int:
    """Entry point; see module docstring."""
    if "--base" not in argv:
        print(
            render(
                "usage",
                "--base REF is required",
                "see docstring",
                ["uv run python -m delivery.compute_tier --base develop [repo]"],
                "working/README.md#checks",
            )
        )
        return 2
    base = argv[argv.index("--base") + 1]
    rest = [a for i, a in enumerate(argv) if not a.startswith("--") and argv[i - 1] != "--base"]
    repo = Path(rest[0]) if rest else Path.cwd()
    t = classify(repo, base)
    print(f"tier: {t.tier}")
    for r in t.reasons:
        print(f"because: {r}")
    if t.tier != "trivial":
        branch = gitx.current_branch(repo)
        try:
            bound = state.bound_item(repo, branch)
        except state.ConsistencyError:
            bound = None
        if bound is None:
            import sys

            print(
                render(
                    "tier",
                    f"this PR changes behavior ({t.reasons[0]}), so it needs a work item",
                    "behavior changes need an accepted spec before merge",
                    [
                        'make start  (choose "add or change behavior" or "fix a bug")',
                        f"make adopt-branch <new-id>  (binds {branch}; "
                        "the ordering check is waived for bounced items)",
                    ],
                    "working/README.md#bounced",
                ),
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
