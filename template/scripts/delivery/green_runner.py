"""Run each enabled member's tests.

"No tests collected" (exit 5) is a failure for enabled members (D3).
Usage: green_runner --base REF. Members with changes since REF are run; if none
changed, all enabled members run.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from delivery import gitx
from delivery.block import fail


def members(repo: Path) -> list[Path]:
    """Workspace members with [tool.delivery] enabled = true."""
    manifests = [*repo.glob("libs/*/pyproject.toml"), *repo.glob("apps/*/pyproject.toml")]
    out = [
        py.parent
        for py in manifests
        if re.search(r"\[tool\.delivery\][^\[]*enabled\s*=\s*true", py.read_text(), re.S)
    ]
    return sorted(out)


def test_command(member: Path) -> list[str]:
    """The member's declared test command, or the default."""
    text = (member / "pyproject.toml").read_text()
    m = re.search(r"\[tool\.delivery\][^\[]*test\s*=\s*\"([^\"]+)\"", text, re.S)
    return m.group(1).split() if m else ["uv", "run", "pytest", str(member)]


def main(argv: list[str]) -> int:
    """Entry point."""
    base = argv[argv.index("--base") + 1] if "--base" in argv else "develop"
    repo = Path.cwd()
    changed = gitx.run(repo, "diff", "--name-only", base, "HEAD", check=False).split()
    changed += gitx.run(repo, "status", "--porcelain", check=False).split()
    enabled = members(repo)
    selected = [m for m in enabled if any(c.startswith(str(m.relative_to(repo))) for c in changed)]
    selected = selected or enabled
    if not selected:
        print("no enabled members; nothing to run")
        return 0
    failures: list[str] = []
    for m in selected:
        r = subprocess.run(test_command(m), cwd=repo, check=False)
        rel = m.relative_to(repo)
        if r.returncode == 5:
            failures.append(
                f"no tests collected in {rel}; "
                "the red stage requires at least one test per criterion"
            )
        elif r.returncode != 0:
            failures.append(f"tests failed in {rel} (exit {r.returncode})")
    for f in failures:
        print(f)
    if failures:
        return fail(
            "green",
            "; ".join(failures),
            "green means every enabled member's tests pass",
            ["fix the failures, then: make green"],
            "working/README.md#green",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
