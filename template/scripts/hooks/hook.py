"""Entry point for the Claude Code hooks (D36): all logic is in scripts/delivery/hooks.py.

Claude Code runs hook commands with the project root as the working directory, so
delivery.hooks resolves the repository itself. This file exists only to put
scripts/ on sys.path -- the delivery package is not installed, and a shell wrapper
that exported PYTHONPATH would not run on Windows.

Usage: python scripts/hooks/hook.py <event>
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from delivery import hooks  # noqa: E402  (sys.path must be set before the import)

if __name__ == "__main__":
    sys.exit(hooks.main(sys.argv[1:]))
