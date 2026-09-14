"""Shell-free entry point for the delivery checks: `python scripts/delivery/run.py <check>`.

pre-commit execs a hook's entry without a shell, so `env PYTHONPATH=scripts ...`
needs `env` to be a real binary on PATH. On Windows it is not: Git ships env.exe
in usr/bin, which the installer does not add to PATH. This sets the path itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

# scripts/ must be on the path before the delivery package can be imported.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CHECKS = {
    "constraints": "delivery.constraints",
    "budgets": "delivery.budgets",
    "accept-trailer": "delivery.accept_trailer",
    "spec-coverage": "delivery.spec_coverage",
    "deploy-surface": "delivery.deploy_surface",
    "vendored": "delivery.vendored_check",
    "writing": "delivery.writing_check",
}


def main(argv: list[str]) -> int:
    """Entry point: <check> [args]."""
    if not argv or argv[0] not in CHECKS:
        print(f"usage: python scripts/delivery/run.py <{'|'.join(CHECKS)}> [args]")
        return 1
    module = __import__(CHECKS[argv[0]], fromlist=["main"])
    return int(module.main(argv[1:]))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
