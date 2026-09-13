"""Tests may only get stronger, and tests must be real tests.

Ratchet (--base REF): compares each changed test file at REF and HEAD.
  RATCHET-01 a test function lost an assertion
  RATCHET-02 an assertion was weakened (== to in, is to ==, dropped operand)
  RATCHET-03 a test function was deleted
  RATCHET-04 a skip or xfail marker was added
The label `test-change-approved` (--labels a,b) allows the change but the lines are still printed.

Identity (D24, D26): a test is identified by the living-spec anchor in its
@pytest.mark.spec("<file>.md#<anchor>") marker. Assertions are aggregated per
anchor across the tests that claim it, so renames, splits, and merges that keep
the assertions are not findings. Unmarked tests fall back to the function name.

Quality (--quality): every test function in the repository.
  TQ-01 no assertion (and no pytest.raises)
  TQ-02 tautology: `x == x`, or a constant assertion
  TQ-03 patches the module under test from its own member's tests
  TQ-04 no @pytest.mark.spec marker in an enabled member
Output: `path:line: RULE message`. Exit 0/1/2.
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from delivery import gitx, paths
from delivery.block import fail

_SKIP_MARKERS = {"skip", "xfail", "skipif"}
_LINK_MARKERS = {"spec"}


@dataclass
class TestFn:
    """What the ratchet compares per test function."""

    name: str
    line: int
    atoms: Counter[tuple[str, str]] = field(default_factory=lambda: Counter())
    n_asserts: int = 0
    markers: set[str] = field(default_factory=lambda: set())
    anchors: set[str] = field(default_factory=lambda: set())
    has_raises: bool = False
    patched: list[str] = field(default_factory=lambda: [])


def _marker_names(fn: ast.FunctionDef) -> set[str]:
    names: set[str] = set()
    for d in fn.decorator_list:
        target = d.func if isinstance(d, ast.Call) else d
        if isinstance(target, ast.Attribute):
            names.add(target.attr)
    return names


def _spec_anchors(fn: ast.FunctionDef) -> set[str]:
    out: set[str] = set()
    for d in fn.decorator_list:
        if (
            isinstance(d, ast.Call)
            and isinstance(d.func, ast.Attribute)
            and d.func.attr == "spec"
            and d.args
            and isinstance(d.args[0], ast.Constant)
        ):
            out.add(str(d.args[0].value))
    return out


def _atoms(test: ast.expr) -> list[tuple[str, str]]:
    """Assertion atoms as (left-expression, operator) pairs; BoolOp(And) splits."""
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        out: list[tuple[str, str]] = []
        for v in test.values:
            out.extend(_atoms(v))
        return out
    if isinstance(test, ast.Compare) and test.ops:
        return [(ast.dump(test.left), type(test.ops[0]).__name__)]
    return [(ast.dump(test), "Truth")]


def _collect(tree: ast.AST) -> dict[str, TestFn]:
    fns: dict[str, TestFn] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
            continue
        tf = TestFn(
            node.name, node.lineno, markers=_marker_names(node), anchors=_spec_anchors(node)
        )
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assert):
                tf.n_asserts += 1
                tf.atoms.update(_atoms(sub.test))
            elif isinstance(sub, ast.Call):
                f = sub.func
                if isinstance(f, ast.Attribute) and f.attr == "raises":
                    tf.has_raises = True
                if (
                    (
                        (isinstance(f, ast.Name) and f.id == "patch")
                        or (isinstance(f, ast.Attribute) and f.attr == "patch")
                    )
                    and sub.args
                    and isinstance(sub.args[0], ast.Constant)
                ):
                    tf.patched.append(str(sub.args[0].value))
        fns[node.name] = tf
    return fns


_WEAKENINGS = {("Eq", "In"), ("Is", "Eq"), ("Eq", "Truth"), ("Is", "Truth")}


@dataclass
class Group:
    """Tests sharing one identity (a spec anchor, or a bare function name)."""

    line: int
    atoms: Counter[tuple[str, str]] = field(default_factory=lambda: Counter())
    names: list[str] = field(default_factory=lambda: [])
    skipped: set[str] = field(default_factory=lambda: set())


def _group(fns: dict[str, TestFn]) -> dict[str, Group]:
    """Aggregate per identity: every spec anchor a test claims, or `name:<fn>` when unmarked."""
    groups: dict[str, Group] = {}
    for tf in fns.values():
        keys = tf.anchors or {f"name:{tf.name}"}
        for key in keys:
            g = groups.setdefault(key, Group(tf.line))
            g.line = min(g.line, tf.line)
            g.atoms.update(tf.atoms)
            g.names.append(tf.name)
            if tf.markers & _SKIP_MARKERS:
                g.skipped.add(tf.name)
    return groups


def _compare(path: str, base: dict[str, TestFn], head: dict[str, TestFn]) -> list[str]:
    out: list[str] = []
    bg, hg = _group(base), _group(head)
    for key, b in bg.items():
        label = key[5:] if key.startswith("name:") else f"anchor {key}"
        h = hg.get(key)
        if h is None:
            out.append(
                f"{path}:{b.line}: RATCHET-03 {label} lost its last test ({', '.join(b.names)})"
            )
            continue
        newly_skipped = h.skipped - b.skipped
        if newly_skipped:
            out.append(
                f"{path}:{h.line}: RATCHET-04 {label}: {sorted(newly_skipped)[0]} "
                "gained a skip/xfail marker"
            )
        weakened = False
        for (left, op), n in b.atoms.items():
            if h.atoms[(left, op)] >= n:
                continue
            for b_op, h_op in _WEAKENINGS:
                if b_op == op and h.atoms[(left, h_op)] > 0:
                    out.append(f"{path}:{h.line}: RATCHET-02 {label}: {op} weakened to {h_op}")
                    weakened = True
                    break
        total_b, total_h = sum(b.atoms.values()), sum(h.atoms.values())
        if not weakened and total_h < total_b:
            out.append(f"{path}:{h.line}: RATCHET-01 {label} lost {total_b - total_h} assertion(s)")
    return out


def ratchet(repo: Path, base: str) -> list[str]:
    """RATCHET-xx lines for every changed test file between base and HEAD."""
    out: list[str] = []
    changed = gitx.run(repo, "diff", "--name-only", f"{base}...HEAD", check=False).split()
    for rel in changed:
        if not re.search(r"(^|/)tests/.*\.py$", rel):
            continue
        base_src = gitx.run(repo, "show", f"{base}:{rel}", check=False)
        if not base_src:
            continue  # new file: nothing to ratchet against
        head_path = repo / rel
        head_src = head_path.read_text() if head_path.exists() else ""
        out.extend(_compare(rel, _collect(ast.parse(base_src)), _collect(ast.parse(head_src))))
    return out


def _member_of(repo: Path, test_file: Path) -> tuple[Path | None, str | None, bool]:
    """(member dir, src package name, enabled) for a test file."""
    parts = test_file.relative_to(repo).parts
    if len(parts) < 3 or parts[0] not in ("libs", "apps"):
        return None, None, False
    member = repo / parts[0] / parts[1]
    pkgs = (
        [p.name for p in (member / "src").iterdir() if p.is_dir()]
        if (member / "src").exists()
        else []
    )
    py = member / "pyproject.toml"
    enabled = (
        bool(re.search(r"\[tool\.delivery\][^\[]*enabled\s*=\s*true", py.read_text(), re.S))
        if py.exists()
        else False
    )
    return member, (pkgs[0] if pkgs else None), enabled


def quality(repo: Path) -> list[str]:
    """TQ-xx lines for every test function in the repository."""
    out: list[str] = []
    for f in paths.test_files(repo):
        _member, pkg, enabled = _member_of(repo, f)
        rel = paths.rel(repo, f)
        for tf in _collect(ast.parse(f.read_text())).values():
            if tf.n_asserts == 0 and not tf.has_raises:
                out.append(f"{rel}:{tf.line}: TQ-01 test {tf.name} has no assertion")
            for left, op in tf.atoms:
                if op == "Truth" and left.startswith("Constant("):
                    out.append(f"{rel}:{tf.line}: TQ-02 test {tf.name} asserts a constant")
            out.extend(
                f"{rel}:{tf.line}: TQ-02 test {tf.name} compares an expression to itself"
                for sub in ast.walk(ast.parse(f.read_text()))
                if isinstance(sub, ast.Assert)
                and isinstance(sub.test, ast.Compare)
                and len(sub.test.comparators) == 1
                and ast.dump(sub.test.left) == ast.dump(sub.test.comparators[0])
                and sub.lineno >= tf.line
                and sub.lineno < tf.line + 200
                and _owner(sub, f) == tf.name
            )
            if pkg:
                out.extend(
                    f"{rel}:{tf.line}: TQ-03 test {tf.name} patches {target}, "
                    "part of the module under test"
                    for target in tf.patched
                    if target.startswith(pkg + ".")
                )
            if enabled and not tf.anchors:
                out.append(
                    f"{rel}:{tf.line}: TQ-04 test {tf.name} has no @pytest.mark.spec marker "
                    "naming the living-spec statement it proves"
                )
    return sorted(set(out))


def _owner(node: ast.AST, path: Path) -> str:
    """Name of the test function containing node (by line span)."""
    tree = ast.parse(path.read_text())
    best = ""
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.lineno <= getattr(node, "lineno", 0) <= (
            fn.end_lineno or fn.lineno
        ):
            best = fn.name
    return best


def main(argv: list[str]) -> int:
    """Entry point; see module docstring."""
    labels: set[str] = set()
    base = None
    rest: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--base":
            base = argv[i + 1]
            i += 2
        elif a == "--labels":
            labels = {s.strip() for s in argv[i + 1].split(",") if s.strip()}
            i += 2
        elif a == "--quality":
            base = "__quality__"
            i += 1
        else:
            rest.append(a)
            i += 1
    if base is None:
        return fail(
            "usage",
            "--base REF or --quality is required",
            "see docstring",
            ["uv run python -m delivery.test_ratchet --base develop [repo]"],
            "working/README.md#checks",
            env=True,
        )
    repo = Path(rest[0]) if rest else Path.cwd()
    lines = quality(repo) if base == "__quality__" else ratchet(repo, base)
    for ln in lines:
        print(ln)
    if not lines:
        return 0
    if base != "__quality__" and "test-change-approved" in labels:
        print("allowed by label test-change-approved")
        return 0
    return fail(
        "test-ratchet" if base != "__quality__" else "test-quality",
        f"{len(lines)} finding(s) listed above",
        "tests may only get stronger, and every test must assert something real",
        [
            "restore or strengthen the test",
            "if the change is right: label test-change-approved (reviewed)",
        ],
        "working/README.md#tests",
    )


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
