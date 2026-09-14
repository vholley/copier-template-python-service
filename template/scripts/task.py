"""Entry point for the project's tasks: `python scripts/task.py <command>`.

The Makefile calls this for every task that used to be a shell script, so there
is one implementation. On macOS and Linux use `make <target>`; on Windows, where
there is no make, call this directly:

    uv run python scripts/task.py new-app worker

`python scripts/task.py` with no arguments lists the commands.
"""

from __future__ import annotations

import sys
from pathlib import Path

# scripts/ must be on the path before the tasks package can be imported.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tasks import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
