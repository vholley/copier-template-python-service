# copier-template-python-service

A copier template for Python projects. Generates a project with uv-managed dependencies, ruff and pyright in strict mode, pre-commit hooks, and GitHub Actions CI. Optionally adds GCP deployment scaffolding (Cloud Run, Secret Manager, Cloud Logging), Docker, and Terraform.

## Prerequisites

- macOS, Linux, or Windows (WSL 2 recommended for shell scripts on Windows)
- **uv** installed — manages Python and dependencies

  macOS / Linux:

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

  Windows (PowerShell):

  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

- **copier** installed: `uv tool install copier` (or `brew install copier` on macOS/Linux with Homebrew)

## GitHub authentication

Cloning the template (and pushing generated projects) requires Git access to GitHub. SSH is the recommended method.

### Set up an SSH key (one-time)

If you don't already have an SSH key, generate one:

```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
```

Press Enter to accept the default file location. Set a passphrase or leave empty.

Add the key to the SSH agent by creating or editing `~/.ssh/config`:

```ssh-config
Host github.com
  AddKeysToAgent yes
  UseKeychain yes
  IdentityFile ~/.ssh/id_ed25519
```

`UseKeychain yes` is macOS-only — omit that line on Linux and Windows.

Copy the public key to your clipboard:

```bash
# macOS
pbcopy < ~/.ssh/id_ed25519.pub

# Linux
xclip -selection clipboard < ~/.ssh/id_ed25519.pub
# or: cat ~/.ssh/id_ed25519.pub  (then copy manually)
```

```powershell
# Windows (PowerShell)
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" | Set-Clipboard
```

In GitHub: **Settings → SSH and GPG keys → New SSH key**. Paste, save.

Verify:

```bash
ssh -T git@github.com
```

GitHub responds with `Hi <username>! You've successfully authenticated, but GitHub does not provide shell access.` That's the success message.

### Alternative: GitHub CLI for HTTPS

To use HTTPS instead, install the GitHub CLI and let it manage credentials:

```bash
# macOS / Linux with Homebrew
brew install gh

# or: https://cli.github.com/manual/installation
gh auth login
```

Choose GitHub.com → HTTPS → authenticate via browser. After this, both HTTPS URLs and copier's `gh:` shorthand work.

## Generate a new project

```sh
copier copy --trust git@github.com:your-org/copier-template-python-service.git <new-project-name>
```

If you set up the GitHub CLI for HTTPS instead of SSH, the `gh:` shorthand also works:

```sh
copier copy --trust gh:your-org/copier-template-python-service <new-project-name>
```

The `--trust` flag is required because the template uses copier's `_tasks` feature to run `git init` and print next-step instructions after generation. Copier requires explicit opt-in for any template that runs commands during generation. The task is a list, not a shell string, so no shell is involved and it behaves the same on macOS, Linux and Windows.

copier asks the following questions:

| Question | Default | Notes |
|---|---|---|
| `project_name` | (required) | Kebab-case, e.g. `my-python-service` |
| `python_version` | `3.14` | `3.13` is the fallback choice |
| `app_framework` | `minimal` | `minimal` or `fastapi` |
| `use_gcp` | `false` | Adds Cloud Run deployment, Secret Manager, Cloud Logging |
| `gcp_project_dev` | (required if `use_gcp`) | E.g. `my-project-dev` |
| `gcp_project_prod` | (required if `use_gcp`) | E.g. `my-project-prod` |
| `include_docker` | `false` | Adds Dockerfile and container build targets |
| `include_terraform` | `false` | Adds `infra/terraform/` scaffolding; Terraform CI workflows require `use_gcp` |
| `enable_delivery` | `true` | Installs the delivery system: `working/`, the `.claude/` process, delivery checks and workflows |
| `owner_group` | (empty) | GitHub handle auto-requested for review on protected paths, e.g. `@org/platform`. Empty means no CODEOWNERS |
| `high_risk_paths` | `["**/auth/**", "**/migrations/**"]` | Globs that require a second reviewer |
| `trivial_paths` | `["docs/**", "*.md", ...]` | Globs eligible for a trivial change with no work item |

After generation, `cd` into the new project and run `uv run python scripts/task.py bootstrap` to install tooling and verify the environment. On macOS and Linux the same tasks are available as `make` targets; on Windows use `scripts/task.py` directly.

## The delivery system

`enable_delivery` defaults to `true`. It installs a process for building software with an
AI coding agent, on top of the base toolchain:

- `working/`: the living spec, architecture constraints, standards and budgets. Tracked, and
  owned by the project after first generation — `copier update` never rewrites it.
- `.claude/`: 26 commands, 14 skills, 4 read-only review agents, path-scoped rules, and the
  session hooks that enforce the stages.
- `scripts/delivery/`: the checks — constraints, budgets, spec coverage, the test ratchet, the
  PR contract, the deployable surface.
- Five CI workflows: delivery checks, review agents, spec drafting, post-merge and an entropy
  audit.

Answer `enable_delivery: false` for the base template on its own: uv workspace, ruff, pyright,
pytest, pre-commit and CI, with none of the process. That is what earlier versions of this
template produced.

`docs/design.md` is the design document the implementation refers to by decision number
(D1-D42); `docs/system-overview.md` is the shorter argument for the approach.

## GCP deployment

The template can add Google Cloud Platform scaffolding on top of the base toolchain. Answer the copier questions like this:

- `use_gcp`: `true`
- `gcp_project_dev`: your dev GCP project ID (e.g. `my-project-dev`)
- `gcp_project_prod`: your prod GCP project ID (e.g. `my-project-prod`)

(`include_docker` defaults to `true` when `use_gcp` is `true`.)

You get the full GCP stack on top of the base toolchain: Cloud Run deploy workflow, `gcp.py` (Secret Manager client), Cloud Logging integration, `Dockerfile`, and optionally `infra/terraform/` with Workload Identity Federation setup.

## Update an existing project from the template

```sh
copier update --trust
```

Run this from the root of a project generated by the template. `--trust` is required for the same reason as `copier copy`. copier shows a diff before applying changes; conflicts that need manual resolution are surfaced inline.

## Restore missing files after cloning

After `git clone`ing a project generated by this template, some files listed in `.gitignore` will not be present — most notably `docs/`, which the template generates but does not track. `copier update` deliberately will not recreate these files: it treats a missing file as an intentional delete.

To restore them, run from the project root:

```sh
uv run python scripts/task.py restore
```

The script re-renders the template into a throwaway git worktree, previews which files would be added, asks for confirmation, then copies in only files that don't already exist. Files tracked in your repo are never overwritten.

Pass `--yes` to skip the confirmation prompt (useful in CI):

```sh
uv run python scripts/task.py restore --yes
```

## Contributing to the template

Changes to the template affect every project that runs `copier update`. Test changes locally before merging:

```sh
copier copy --trust . /tmp/test-project
cd /tmp/test-project && uv run python scripts/task.py bootstrap && make ci
```

The `docs/RATIONALE.md` inside generated projects documents what each tool and pattern is and why it fits the project. Update it alongside any structural change.
