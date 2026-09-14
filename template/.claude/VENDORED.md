# Vendored skills

Copied whole, never edited locally. To change one, change it at the source and re-vendor; update the digest (`python -m delivery.vendored_check --digest .claude/skills/<name>` computes it).

| skill | source | copied | sha256 of the directory |
|---|---|---|---|
| deslop | /mnt/skills/user/deslop (the team's skill) | 2026-09-13 | 43a1e34e66c95030e859b2cf1d087668214b1363668560b3fcb6dd1ca4bba5d8 |

The deslop reference (`references/ai-writing-tells.md`) carries a review date; the weekly audit checks it and opens an issue when it is past due.
