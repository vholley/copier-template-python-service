"""Allowed signers for acceptance-commit verification.

Sources: `file:<path>` (an OpenSSH allowed_signers file) or `github:<org>`
(every org member's registered SSH signing keys, paired with the email
principals git presents at verification, D28). Any failure raises FetchError;
callers fail closed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from delivery import gitx


class FetchError(Exception):
    """The signer list could not be obtained. Never treated as an empty list."""


def _gh(*args: str) -> str:
    gh = shutil.which("gh")
    if gh is None:
        raise OSError("gh CLI not found")
    out = subprocess.run([gh, "api", *args], capture_output=True, text=True, check=False)
    if out.returncode != 0:
        raise OSError(out.stderr.strip() or "gh api failed")
    return out.stdout


def _logins(owner: str) -> list[str]:
    """The accounts that may sign: an org's members, or the user themselves.

    github:<owner> is built from github.repository_owner, which is a personal
    account on a personal repository. orgs/<user>/members is a 404 there, and
    treating that as a fetch failure blocked every pull request.
    """
    try:
        members = json.loads(_gh(f"orgs/{owner}/members", "--paginate"))
    except OSError:
        account = json.loads(_gh(f"users/{owner}"))
        if str(account.get("type", "")) == "Organization":
            raise  # a real org whose members we could not read: fail closed
        return [str(account["login"])]
    return [str(m["login"]) for m in members]


def _github_signing_keys(owner: str) -> dict[str, list[str]]:
    """Map email principal -> keys for every signer with registered signing keys."""
    keys: dict[str, list[str]] = {}
    for login in _logins(owner):
        user = json.loads(_gh(f"users/{login}"))
        principals = [f"{login}@users.noreply.github.com"]
        if user.get("email"):
            principals.append(str(user["email"]))
        for k in json.loads(_gh(f"users/{login}/ssh_signing_keys")):
            for p in principals:
                keys.setdefault(p, []).append(str(k["key"]))
    return keys


def load(source: str) -> dict[str, list[str]]:
    """Return principal -> [public keys] or raise FetchError."""
    kind, _, ref = source.partition(":")
    try:
        if kind == "file":
            path = Path(ref)
            if not path.exists():
                raise FileNotFoundError(path)
            out: dict[str, list[str]] = {}
            for line in path.read_text().splitlines():
                parts = line.split()
                if len(parts) >= 3 and not line.startswith("#"):
                    out.setdefault(parts[0], []).append(" ".join(parts[1:3]))
            return out
        if kind == "github":
            return _github_signing_keys(ref)
    except (OSError, ValueError, KeyError) as exc:
        raise FetchError(f"could not load signers from {source}: {exc}") from exc
    raise FetchError(f"unknown signer source {source!r}")


def write_allowed_signers(keys: dict[str, list[str]], path: Path) -> Path:
    """Write an OpenSSH allowed_signers file."""
    lines = [f"{p} {k}" for p, ks in keys.items() for k in ks]
    path.write_text("".join(ln + "\n" for ln in lines))
    return path


def verify_commit(repo: Path, sha: str, allowed: Path) -> bool:
    """True when the commit carries a good SSH signature by a listed principal."""
    out = subprocess.run(
        [
            gitx.GIT,
            "-C",
            str(repo),
            "-c",
            f"gpg.ssh.allowedSignersFile={allowed}",
            "verify-commit",
            sha,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return out.returncode == 0
