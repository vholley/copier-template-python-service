"""Work-item state: `.work/<id>/state.json` and its transitions.

This module is the only writer of state.json. The file is a cache: everything
in it is derivable from git history (acceptance commits carry `Accept:`
trailers) and from the artifact files, so `rebuild()` can always regenerate
it. Every read verifies a checksum and a set of consistency facts and reports
the specific disagreement with the command that repairs it (design 12.4).
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from delivery import gitx

WORK_DIR = ".work"
HISTORY_DIR = Path("working") / "history"
RETRY_CAP = 3

STATES: tuple[str, ...] = (
    "intent",
    "clarify",
    "spec",
    "diagnose",
    "plan",
    "red",
    "implement",
    "verify",
    "review",
    "merged",
    "escalated",
    "bounced",
    "unreproduced",
    "abandoned",
)
TERMINAL: frozenset[str] = frozenset({"merged", "abandoned", "unreproduced"})

# Legal transitions. "abandoned" is added to every non-terminal state below.
_TRANSITIONS: dict[str, list[str]] = {
    "intent": ["clarify", "diagnose"],
    "clarify": ["spec"],
    "spec": ["plan"],
    "diagnose": ["plan", "unreproduced"],
    "plan": ["red", "implement"],  # implement directly only for the defect variant
    "red": ["implement"],
    "implement": ["verify", "escalated", "spec"],
    "verify": ["review", "implement"],
    "review": ["merged", "implement"],
    "escalated": ["implement", "spec"],
    "bounced": ["intent"],
}

WORKFLOWS: tuple[str, ...] = ("change", "change-defect", "project", "spike")

_ACCEPT_RE = re.compile(r"^Accept: (?P<stage>[\w-]+)(?P<hashes>(?: sha256=[0-9a-f]{64})+)", re.M)
_ITEM_RE = re.compile(r"^Work-Item: (?P<id>\S+)", re.M)


class StateError(Exception):
    """A request that the state machine refuses (not a corruption)."""


class TransitionError(StateError):
    """The requested transition is not in exits(current stage)."""


class GateError(StateError):
    """The transition is legal but its gate (an acceptance, the retry cap) is not met."""


class IntegrityError(Exception):
    """state.json does not match its checksum or cannot be parsed."""


class ConsistencyError(Exception):
    """state.json disagrees with git or the artifacts. The message names the repair."""


@dataclass
class State:
    """The contents of state.json (checksum excluded from payload())."""

    id: str
    workflow: str
    branch: str
    stage: str = "intent"
    accepted: dict[str, str] = field(default_factory=lambda: {})
    retries: int = 0
    runs: list[str] = field(default_factory=lambda: [])
    checksum: str = ""

    def payload(self) -> dict[str, object]:
        """Fields that the checksum covers."""
        data = asdict(self)
        data.pop("checksum")
        return data


# ----------------------------------------------------------------- helpers


def file_hash(path: Path) -> str:
    """SHA-256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


_CRITERIA_DEFINITION_FIELDS = ("id", "class", "statement", "verify")


def accept_hash(path: Path) -> str:
    """The value carried in Accept: trailers (D30).

    For criteria.json, the hash covers the definition only (change_type and each
    criterion's id, class, statement, verify), because status, evidence,
    evaluator, and plan_steps are written after acceptance by design. Every
    other file is hashed by its bytes.
    """
    if path.name != "criteria.json":
        return file_hash(path)
    data = json.loads(path.read_text())
    projection = {
        "change_type": data.get("change_type"),
        "criteria": [
            {k: c.get(k) for k in _CRITERIA_DEFINITION_FIELDS} for c in data.get("criteria", [])
        ],
    }
    canonical = json.dumps(projection, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _checksum(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def item_dir(repo: Path, item_id: str) -> Path:
    """Directory holding a work item's records."""
    return repo / WORK_DIR / item_id


def _state_path(repo: Path, item_id: str) -> Path:
    return item_dir(repo, item_id) / "state.json"


def _replace(src: Path, dst: Path) -> None:
    src.replace(dst)


def _write(repo: Path, st: State) -> None:
    payload = st.payload()
    st.checksum = _checksum(payload)
    data = {**payload, "checksum": st.checksum}
    path = _state_path(repo, st.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    try:
        _replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def load_unchecked(repo: Path, item_id: str) -> State:
    """Load state.json verifying only its checksum (no git or artifact checks)."""
    path = _state_path(repo, item_id)
    if not path.exists():
        raise IntegrityError(
            f"{path.relative_to(repo)} is missing. NEXT: make rebuild ID={item_id}"
        )
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise IntegrityError(
            f"{path.relative_to(repo)} is not valid JSON ({exc.msg}). "
            f"NEXT: make rebuild ID={item_id}"
        ) from exc
    st = State(**data)
    if _checksum(st.payload()) != st.checksum:
        raise IntegrityError(
            f"{path.relative_to(repo)} checksum mismatch: the file was edited outside "
            f"stage_state. NEXT: make rebuild ID={item_id}"
        )
    return st


# ---------------------------------------------------------- acceptances (git)


def acceptances(repo: Path, item_id: str) -> dict[str, tuple[str, list[str]]]:
    """Map stage -> (commit sha, [hashes]) from Accept: trailers on this item's commits."""
    found: dict[str, tuple[str, list[str]]] = {}
    for sha, msg in gitx.commits(repo):
        item = _ITEM_RE.search(msg)
        if not item or item.group("id") != item_id:
            continue
        for m in _ACCEPT_RE.finditer(msg):
            stage = m.group("stage")
            if stage not in found:  # newest wins
                hashes = re.findall(r"sha256=([0-9a-f]{64})", m.group("hashes"))
                found[stage] = (sha, hashes)
    return found


_STAGE_FILES: dict[str, list[str]] = {
    "intent": ["intent.md"],
    "spec": ["spec.md", "criteria.json"],
    "diagnosis": ["diagnosis.md"],
    "red": ["tests.json"],
}


def accepted_file_problems(repo: Path, item_id: str) -> list[str]:
    """Accepted artifacts whose content no longer matches their acceptance hash."""
    problems: list[str] = []
    for stage, (_sha, hashes) in acceptances(repo, item_id).items():
        files = _STAGE_FILES.get(stage, [])
        for name, expected in zip(files, hashes, strict=False):
            path = item_dir(repo, item_id) / name
            if path.exists() and accept_hash(path) != expected:
                problems.append(
                    f"{name} changed since Accept: {stage}. "
                    f"NEXT: make accept STAGE={stage} (or /amend)"
                )
    return problems


# ------------------------------------------------------------------ public API


def create(repo: Path, item_id: str, workflow: str, branch: str) -> State:
    """Create a work item at stage intent, bound to branch (created if missing)."""
    if workflow not in WORKFLOWS:
        raise StateError(f"unknown workflow {workflow!r}")
    if _state_path(repo, item_id).exists():
        raise StateError(f"work item {item_id} already exists")
    if not gitx.branch_exists(repo, branch):
        gitx.run(repo, "branch", branch)  # bind to a branch that exists (D18)
    st = State(id=item_id, workflow=workflow, branch=branch)
    _write(repo, st)
    return st


def read(repo: Path, item_id: str) -> State:
    """Load state, verifying checksum and consistency with git and artifacts."""
    st = load_unchecked(repo, item_id)
    problems = accepted_file_problems(repo, item_id)
    if not gitx.branch_exists(repo, st.branch):
        problems.append(f"branch {st.branch} not found. NEXT: make adopt-branch {item_id}")
    if problems:
        raise ConsistencyError("; ".join(problems))
    return st


def check(repo: Path, item_id: str) -> list[str]:
    """Non-raising consistency report, one line per disagreement, with repairs."""
    report: list[str] = []
    try:
        st = load_unchecked(repo, item_id)
    except IntegrityError as exc:
        return [str(exc)]
    report.extend(accepted_file_problems(repo, item_id))
    if not gitx.branch_exists(repo, st.branch):
        report.append(f"branch {st.branch} not found. NEXT: make adopt-branch {item_id}")
    rel = str(_state_path(repo, item_id).relative_to(repo))
    if not gitx.is_clean(repo, rel):
        report.append(f"state.json has uncommitted changes. NEXT: commit {rel}")
    derived = derive_stage(repo, item_id)
    if derived != st.stage and st.stage not in ("escalated", "bounced"):
        report.append(
            f"recorded stage {st.stage} but artifacts imply {derived}. "
            f"NEXT: make rebuild ID={item_id}"
        )
    return report


def exits(stage: str) -> list[str]:
    """Legal next stages; empty only for terminal stages."""
    if stage in TERMINAL:
        return []
    return [*_TRANSITIONS.get(stage, []), "abandoned"]


def advance(repo: Path, item_id: str, to: str, *, force: bool = False) -> State:
    """Move to a legal next stage; without force, the transition's gate must be met."""
    st = load_unchecked(repo, item_id)
    if to not in exits(st.stage):
        raise TransitionError(f"illegal transition {st.stage} -> {to}")
    if not force:
        _check_gate(st, to)
    st.stage = to
    if to == "implement":
        st.retries = 0
    _write(repo, st)
    return st


def _check_gate(st: State, to: str) -> None:
    required = {
        "clarify": "intent",
        "diagnose": "intent",
        "plan": "diagnosis" if st.workflow == "change-defect" else "spec",
        "implement": "red" if st.stage == "red" else None,
    }.get(to)
    if to == "escalated":
        if st.retries < RETRY_CAP:
            raise GateError(f"escalation requires {RETRY_CAP} retries, have {st.retries}")
        return
    if required and required not in st.accepted:
        raise GateError(f"{st.stage} -> {to} requires Accept: {required}")


def record_acceptance(repo: Path, item_id: str, stage: str, sha: str) -> State:
    """Record the commit that accepted a stage."""
    st = load_unchecked(repo, item_id)
    st.accepted[stage] = sha
    _write(repo, st)
    return st


def bump_retry(repo: Path, item_id: str) -> int:
    """Increment the stop-hook retry counter and return it."""
    st = load_unchecked(repo, item_id)
    st.retries += 1
    _write(repo, st)
    return st.retries


def abandon(repo: Path, item_id: str) -> Path:
    """Close an item from any non-terminal stage and archive it to working/history."""
    st = load_unchecked(repo, item_id)
    if st.stage in TERMINAL:
        raise TransitionError(f"{item_id} is already {st.stage}")
    st.stage = "abandoned"
    _write(repo, st)
    src = item_dir(repo, item_id)
    dst = repo / HISTORY_DIR / item_id
    progress = src / "progress.md"
    if progress.exists():
        progress.unlink()
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return dst


def rebind(repo: Path, item_id: str, workflow: str, stage: str) -> State:
    """Change an item's workflow and stage (used when a spike becomes a change)."""
    st = load_unchecked(repo, item_id)
    if workflow not in WORKFLOWS or stage not in STATES:
        raise StateError(f"cannot rebind to {workflow}/{stage}")
    st.workflow, st.stage = workflow, stage
    _write(repo, st)
    return st


def bound_item(repo: Path, branch: str) -> str | None:
    """The work item bound to a branch, or None. Refuses a branch with two items."""
    work = repo / WORK_DIR
    if not work.exists():
        return None
    matches: list[str] = []
    for d in sorted(work.iterdir()):
        if not (d / "state.json").exists():
            continue
        try:
            data = json.loads((d / "state.json").read_text())
        except json.JSONDecodeError:
            continue
        if data.get("branch") == branch:
            matches.append(d.name)
    if len(matches) > 1:
        raise ConsistencyError(
            f"branch {branch} has more than one item ({', '.join(matches)}). "
            f"NEXT: make abandon ID=<the wrong one>"
        )
    return matches[0] if matches else None


# --------------------------------------------------------------- derivation


def derive_stage(repo: Path, item_id: str) -> str:
    """Compute the stage from acceptances in git and the artifact files present."""
    d = item_dir(repo, item_id)
    acc = acceptances(repo, item_id)
    defect = (d / "diagnosis.md").exists() or "diagnosis" in acc
    if "red" in acc or ("diagnosis" in acc and (d / "plan.md").exists()):
        return _build_stage(d)
    if "diagnosis" in acc:
        return "plan"
    if "spec" in acc:
        return "red" if (d / "plan.md").exists() else "plan"
    if defect and "intent" in acc:
        return "diagnose"
    if "intent" in acc:
        return "spec" if (d / "spec.md").exists() else "clarify"
    return "intent"


def _build_stage(d: Path) -> str:
    """implement, verify, or review, from criteria.json's status and evaluator fields."""
    path = d / "criteria.json"
    if not path.exists():
        return "implement"
    try:
        crit = json.loads(path.read_text()).get("criteria", [])
    except json.JSONDecodeError:
        return "implement"
    if not crit:
        return "implement"
    if all(c.get("status") == "pass" and c.get("evidence") for c in crit):
        if all(c.get("evaluator") == "confirmed" for c in crit):
            return "review"
        return "verify"
    return "implement"


def rebuild(repo: Path, item_id: str) -> State:
    """Regenerate state.json from git and artifacts. Repairs a corrupt or missing file."""
    workflow = "change"
    branch = gitx.current_branch(repo)
    retries = 0
    path = _state_path(repo, item_id)
    if path.exists():
        try:
            old = json.loads(path.read_text())
            workflow = str(old.get("workflow", workflow))
            branch = str(old.get("branch", branch))
            retries = int(old.get("retries", 0))
        except json.JSONDecodeError, ValueError, TypeError:
            pass
    if (item_dir(repo, item_id) / "diagnosis.md").exists():
        workflow = "change-defect"
    accepted = {stage: sha for stage, (sha, _h) in acceptances(repo, item_id).items()}
    st = State(
        id=item_id,
        workflow=workflow,
        branch=branch,
        stage=derive_stage(repo, item_id),
        accepted=accepted,
        retries=retries,
    )
    _write(repo, st)
    return st
