"""`python -m delivery <module> [args]`: run a delivery script, or `--help` for its docstring."""

from __future__ import annotations

import importlib
import sys


def main(argv: list[str]) -> int:
    """Dispatch to delivery.<module>.main(args)."""
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    name, args = argv[0], argv[1:]
    try:
        mod = importlib.import_module(f"delivery.{name}")
    except ModuleNotFoundError:
        print(f"unknown delivery module {name!r}", file=sys.stderr)
        return 2
    if args and args[0] in ("-h", "--help"):
        print((mod.__doc__ or name).strip())
        return 0
    entry = getattr(mod, "main", None)
    if entry is None:
        print(f"delivery.{name} has no main()", file=sys.stderr)
        return 2
    return int(entry(args))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
