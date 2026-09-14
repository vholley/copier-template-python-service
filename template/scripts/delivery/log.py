"""The issue log: working/log.md, append-only (D42).

Usage: log.py add --source S --what W --missing M [--fix F] [repo]
       log.py close L-<n> --fix F [repo]
       log.py open [repo]            (prints open entries; exit 1 if any)
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from delivery.block import fail

LOG_FILE = Path("working/log.md")
_HEAD = re.compile(
    r"^## (?P<id>L-\d+) · (?P<date>\S+) · (?P<source>.+?) · (?P<status>open|closed)\s*$", re.M
)


def _arg(argv: list[str], name: str) -> str:
    return argv[argv.index(name) + 1] if name in argv else ""


def _repo(argv: list[str], flags: tuple[str, ...]) -> Path:
    rest = [
        a
        for i, a in enumerate(argv[1:], start=1)
        if not a.startswith("--") and argv[i - 1] not in flags
    ]
    return Path(rest[-1]) if rest and not rest[-1].startswith("L-") else Path.cwd()


def entries(text: str) -> list[dict[str, str]]:
    """Parsed entries in file order."""
    out: list[dict[str, str]] = []
    for m in _HEAD.finditer(text):
        out.append(
            {
                "id": m.group("id"),
                "date": m.group("date"),
                "source": m.group("source"),
                "status": m.group("status"),
            }
        )
    return out


def add(repo: Path, source: str, what: str, missing: str, fix: str) -> str:
    """Append an entry; returns its id."""
    path = repo / LOG_FILE
    text = (
        path.read_text()
        if path.exists()
        else "# Issue log\n\nAppend-only. Status moves from open to closed only.\n"
    )
    ids = [int(e["id"][2:]) for e in entries(text)]
    lid = f"L-{(max(ids) if ids else 0) + 1}"
    today = datetime.now(UTC).date().isoformat()
    status = "closed" if fix else "open"
    entry = f"\n## {lid} · {today} · {source} · {status}\nWhat happened: {what}\nWhich definition was missing: {missing}\n"
    entry += f"Fix: {fix} Closed {today}.\n" if fix else "Fix: (open)\n"
    path.write_text(text.rstrip("\n") + "\n" + entry)
    return lid


def close(repo: Path, lid: str, fix: str) -> bool:
    """Mark an entry closed with its fix. Returns False when the id is unknown or already closed."""
    path = repo / LOG_FILE
    text = path.read_text()
    m = re.search(rf"^## {re.escape(lid)} · (\S+) · (.+?) · open\s*$", text, re.M)
    if not m:
        return False
    today = datetime.now(UTC).date().isoformat()
    text = text[: m.start()] + f"## {lid} · {m.group(1)} · {m.group(2)} · closed" + text[m.end() :]
    text = re.sub(
        rf"(## {re.escape(lid)} ·[^\n]*\n(?:[^\n]*\n)*?)Fix: \(open\)",
        rf"\1Fix: {fix} Closed {today}.",
        text,
        count=1,
    )
    path.write_text(text)
    return True


MORE = "working/README.md#log"
FLAGS = ("--source", "--what", "--missing", "--fix")


def _cmd_add(argv: list[str], repo: Path) -> int:
    what, missing = _arg(argv, "--what"), _arg(argv, "--missing")
    if not what or not missing:
        return fail(
            "log",
            "--what and --missing are required",
            "an issue is recorded with the definition it exposed",
            ['make log WHAT="..." MISSING="..." [FIX="..."]'],
            MORE,
            env=True,
        )
    lid = add(repo, _arg(argv, "--source") or "session", what, missing, _arg(argv, "--fix"))
    print(f"logged {lid}")
    return 0


def _cmd_close(argv: list[str], repo: Path) -> int:
    lid = argv[1] if len(argv) > 1 else ""
    if not lid or not close(repo, lid, _arg(argv, "--fix") or "(no fix given)"):
        return fail(
            "log",
            f"{lid or '?'} is not an open entry",
            "entries close once",
            ["make log-open"],
            MORE,
        )
    print(f"closed {lid}")
    return 0


def _cmd_open(repo: Path) -> int:
    path = repo / LOG_FILE
    opened = entries(path.read_text()) if path.exists() else []
    opened = [e for e in opened if e["status"] == "open"]
    for e in opened:
        print(f"{e['id']} {e['date']} {e['source']}")
    return 1 if opened else 0


def main(argv: list[str]) -> int:
    """Entry point."""
    cmd = argv[0] if argv else ""
    repo = _repo(argv, FLAGS) if argv else Path.cwd()
    if cmd == "add":
        return _cmd_add(argv, repo)
    if cmd == "close":
        return _cmd_close(argv, repo)
    if cmd == "open":
        return _cmd_open(repo)
    return fail("usage", "add | close | open", "see docstring", ["make log-open"], MORE, env=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
