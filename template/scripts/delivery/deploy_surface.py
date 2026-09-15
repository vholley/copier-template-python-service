"""Nothing from the delivery system is deployable.

DEPLOY-01  a Dockerfile COPY/ADD source outside the allowed list
DEPLOY-02  .dockerignore missing a required entry
DEPLOY-03  a built image contains an excluded path (--image NAME; needs docker)
Run: uv run python -m delivery.deploy_surface [--image NAME] [repo]. Exit 0/1/2.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from delivery import paths
from delivery.block import fail

ALLOWED_COPY_PREFIXES = (
    "pyproject.toml",
    "uv.lock",
    "libs/",
    "apps/",
    ".python-version",
    "README.md",
)
REQUIRED_IGNORES = (
    ".claude/",
    ".work/",
    "working/",
    "docs/",
    "scripts/",
    ".github/",
    "**/tests/",
    "*.md",
)
EXCLUDED_IN_IMAGE = (".claude/", ".work/", "working/", "docs/", "scripts/", ".github/", "/tests/")
_COPY_RE = re.compile(r"^\s*(COPY|ADD)\s+(?P<flags>(?:--\S+\s+)*)(?P<srcs>.+?)\s+\S+\s*$")


def docker_available() -> bool:
    """True when a docker CLI is on PATH."""
    return shutil.which("docker") is not None


def image_files(name: str) -> list[str]:
    """Paths inside an image, via a throwaway container running find."""
    docker = shutil.which("docker") or "docker"
    out = subprocess.run(
        [docker, "run", "--rm", "--entrypoint", "find", name, "/", "-xdev", "-type", "f"],
        capture_output=True,
        text=True,
        check=False,
    )
    return out.stdout.splitlines()


def check_dockerfiles(repo: Path) -> list[str]:
    """DEPLOY-01 lines."""
    out: list[str] = []
    for df in sorted(repo.glob("**/Dockerfile")):
        if ".venv" in df.parts:
            continue
        for i, line in enumerate(df.read_text().splitlines(), start=1):
            m = _COPY_RE.match(line)
            if not m:
                continue
            # COPY --from=<stage|image> reads from another build stage, not from the
            # repository, so its sources are not part of the deploy surface.
            if "--from=" in m.group("flags"):
                continue
            for src in m.group("srcs").split():
                if src.startswith("--"):
                    continue
                if not src.startswith(ALLOWED_COPY_PREFIXES):
                    out.append(
                        f"{paths.rel(repo, df)}:{i}: DEPLOY-01 COPY source {src!r} "
                        "is outside the allowed list "
                        f"{ALLOWED_COPY_PREFIXES}; copy only what the app runs from"
                    )
    return out


def check_dockerignore(repo: Path) -> list[str]:
    """DEPLOY-02 lines."""
    di = repo / ".dockerignore"
    if not di.exists():
        return [
            ".dockerignore:1: DEPLOY-02 file missing; required entries: "
            + ", ".join(REQUIRED_IGNORES)
        ]
    have = {ln.strip() for ln in di.read_text().splitlines()}
    return [
        f".dockerignore:1: DEPLOY-02 missing entry {req!r}"
        for req in REQUIRED_IGNORES
        if req not in have
    ]


def check_image(name: str) -> list[str]:
    """DEPLOY-03 lines, or a single explicit skip notice when docker is absent."""
    if not docker_available():
        print("image check skipped: docker not available")
        return []
    bad = [p for p in image_files(name) if any(x in p for x in EXCLUDED_IN_IMAGE)]
    return [f"image:{name}:1: DEPLOY-03 contains excluded path {p}" for p in bad]


def main(argv: list[str]) -> int:
    """Entry point; see module docstring."""
    image = argv[argv.index("--image") + 1] if "--image" in argv else None
    rest = [
        a
        for i, a in enumerate(argv)
        if not a.startswith("--") and (i == 0 or argv[i - 1] != "--image")
    ]
    repo = Path(rest[0]) if rest else Path.cwd()
    lines = check_dockerfiles(repo) + check_dockerignore(repo)
    if image:
        lines += check_image(image)
    for ln in lines:
        print(ln)
    if lines:
        return fail(
            "deploy-surface",
            f"{len(lines)} deployable-surface problem(s) listed above",
            "skills, work records, and process docs must never reach a deployed artifact",
            ["fix the Dockerfile COPY list or .dockerignore as the line says"],
            "working/README.md#deploy",
        )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
