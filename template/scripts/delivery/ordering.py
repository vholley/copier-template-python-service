"""Red before green, for every criterion; and for defects, the fix lands where the diagnosis says.

The criterion-to-test map is .work/<id>/tests.json (D29).

  ORDER-01 implementation committed before the criterion's test (or no test on the branch)
  ORDER-02 the test passed at the commit that added it (it was never red)
  ORDER-03 defect: the diff does not touch the diagnosed location
Run: uv run python -m delivery.ordering --item ID --base REF [repo]. Exit 0/1/2.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from delivery import gitx
from delivery.block import fail

_SRC_RE = re.compile(r"^(libs|apps)/[^/]+/src/")


def _first_commit_adding(repo: Path, base: str, path: str, name: str) -> str | None:
    out = gitx.run(
        repo,
        "log",
        "--reverse",
        "--format=%H",
        f"{base}..HEAD",
        f"-Sdef {name}(",
        "--",
        path,
        check=False,
    )
    shas = out.split()
    return shas[0] if shas else None


def _source_commits_before(repo: Path, base: str, until: str) -> list[str]:
    """Commits in base..until (exclusive of until) that touch source paths."""
    out: list[str] = []
    for sha in gitx.run(
        repo, "log", "--reverse", "--format=%H", f"{base}..{until}^", check=False
    ).split():
        files = gitx.run(repo, "show", "--name-only", "--format=", sha, check=False).split()
        if any(_SRC_RE.match(f) for f in files):
            out.append(sha)
    return out


def _run_test_at(repo: Path, sha: str, test: str) -> int:
    """Exit code of one test run at a commit, in a temporary worktree."""
    with tempfile.TemporaryDirectory() as tmp:
        wt = Path(tmp) / "wt"
        gitx.run(repo, "worktree", "add", "--detach", "-q", str(wt), sha)
        try:
            env = dict(os.environ)
            src_dirs = [str(p) for p in [*wt.glob("libs/*/src"), *wt.glob("apps/*/src")]]
            env["PYTHONPATH"] = os.pathsep.join([*src_dirs, env.get("PYTHONPATH", "")])
            result = subprocess.run(  # noqa: S603 - fixed interpreter
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "-o",
                    "addopts=",
                    test,
                ],
                cwd=wt,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode
        finally:
            gitx.run(repo, "worktree", "remove", "--force", str(wt), check=False)


def _function_span(path: Path, name: str) -> tuple[int, int] | None:
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
            return node.lineno, node.end_lineno or node.lineno
    return None


def _changed_lines(repo: Path, base: str, rel: str) -> set[int]:
    diff = gitx.run(repo, "diff", "-U0", base, "HEAD", "--", rel, check=False)
    lines: set[int] = set()
    for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", diff, re.M):
        start, count = int(m.group(1)), int(m.group(2) or 1)
        lines.update(range(start, start + count))
    return lines


def check_location(repo: Path, base: str, item: str) -> list[str]:
    """ORDER-03 lines for a defect item."""
    diag = repo / ".work" / item / "diagnosis.md"
    m = (
        re.search(r"^location:\s*(?P<file>\S+?):(?P<fn>\w+)\s*$", diag.read_text(), re.M)
        if diag.exists()
        else None
    )
    if not m:
        return [f".work/{item}/diagnosis.md:1: ORDER-03 no `location: file:function` line"]
    rel, fn = m.group("file"), m.group("fn")
    changed = _changed_lines(repo, base, rel)
    if not changed:
        return [f".work/{item}/diagnosis.md:1: ORDER-03 diff does not touch diagnosed file {rel}"]
    span = _function_span(repo / rel, fn) if (repo / rel).exists() else None
    if span and not any(span[0] <= ln <= span[1] for ln in changed):
        return [f"{rel}:{span[0]}: ORDER-03 diff does not touch diagnosed function {fn}"]
    return []


def check(repo: Path, base: str, item: str) -> list[str]:
    """All ORDER-xx lines for a work item."""
    out: list[str] = []
    data = json.loads((repo / ".work" / item / "criteria.json").read_text())
    tests_path = repo / ".work" / item / "tests.json"
    tmap: dict[str, list[dict[str, str]]] = (
        json.loads(tests_path.read_text()) if tests_path.exists() else {}
    )
    for c in data.get("criteria", []):
        cid = str(c.get("id"))
        if c.get("class") == "budget":
            continue
        tests = [str(e.get("test")) for e in tmap.get(cid, [])]
        if not tests and data.get("change_type") != "trivial":
            out.append(f".work/{item}/tests.json:1: ORDER-01 {cid} lists no tests (D29)")
            continue
        for t in tests:
            path, _, name = t.partition("::")
            sha = _first_commit_adding(repo, base, path, name)
            if sha is None:
                if gitx.run(repo, "show", f"{base}:{path}", check=False):
                    continue  # pre-existing test at base: a regression criterion
                out.append(f"{path}:1: ORDER-01 {cid} test {name} was not added on this branch")
                continue
            if _source_commits_before(repo, base, sha):
                out.append(
                    f"{path}:1: ORDER-01 {cid} implementation was committed before test {name}"
                )
            if _run_test_at(repo, sha, t) == 0:
                out.append(
                    f"{path}:1: ORDER-02 {cid} test {name} passed at its own commit "
                    f"{sha[:8]}; it was never red"
                )
    if data.get("change_type") == "defect":
        out.extend(check_location(repo, base, item))
    return out


def main(argv: list[str]) -> int:
    """Entry point; see module docstring."""
    if "--item" not in argv or "--base" not in argv:
        return fail(
            "usage",
            "--item ID and --base REF are required",
            "see docstring",
            ["uv run python -m delivery.ordering --item ID --base develop [repo]"],
            "working/README.md#checks",
            env=True,
        )
    item = argv[argv.index("--item") + 1]
    base = argv[argv.index("--base") + 1]
    rest = [
        a
        for i, a in enumerate(argv)
        if not a.startswith("--") and argv[i - 1] not in ("--item", "--base")
    ]
    repo = Path(rest[0]) if rest else Path.cwd()
    lines = check(repo, base, item)
    for ln in lines:
        print(ln)
    if lines:
        return fail(
            "ordering",
            f"{len(lines)} ordering problem(s) listed above",
            "every criterion's test is committed, failing, before its implementation",
            [
                "rewrite history so the red commit precedes the green one, "
                "or label retroactive-chain (reviewed)"
            ],
            "working/README.md#red-first",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
