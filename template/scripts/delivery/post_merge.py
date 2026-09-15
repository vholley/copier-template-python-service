"""After merge: archive .work/<id>/ to working/history/<id>/, drop progress.md (3.2)."""

from __future__ import annotations

import shutil
from pathlib import Path

from delivery import state
from delivery.block import fail


def archive(repo: Path, item: str) -> Path:
    """Move the item's records to history; returns the destination."""
    src = state.item_dir(repo, item)
    dst = repo / state.HISTORY_DIR / item
    progress = src / "progress.md"
    if progress.exists():
        progress.unlink()
    for msg in src.glob("accept-*.msg"):
        msg.unlink()
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return dst


def main(argv: list[str]) -> int:
    """Entry point: --item ID [repo]."""
    if "--item" not in argv:
        return fail(
            "usage",
            "--item ID is required",
            "see docstring",
            ["uv run python -m delivery.post_merge --item ID"],
            "working/README.md#checks",
            env=True,
        )
    item = argv[argv.index("--item") + 1]
    rest = [a for i, a in enumerate(argv) if not a.startswith("--") and argv[i - 1] != "--item"]
    repo = Path(rest[0]) if rest else Path.cwd()
    if not state.item_dir(repo, item).exists():
        return fail(
            "post-merge",
            f"no .work/{item}",
            "only active items are archived",
            ["make status"],
            "working/README.md#checks",
        )
    dst = archive(repo, item)
    print(f"archived to {dst.relative_to(repo)}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
