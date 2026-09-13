"""Delivery system scripts.

Every module exposes main(argv) -> int and is runnable as
`uv run python -m delivery.<name>`. Exit codes: 0 pass, 1 violation,
2 usage or environment error. Blocks are emitted only through delivery.block.
"""
