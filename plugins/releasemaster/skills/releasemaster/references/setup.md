# Setup & init flow

## 1. Installing the skill

A skill is just this folder. Where you put it decides who sees it.

| Scope | Location | Use when |
|---|---|---|
| **User** (personal, every project) | `~/.claude/skills/releasemaster/` — Windows: `%USERPROFILE%\.claude\skills\releasemaster\` | You use it across many projects |
| **Workspace / project** (shared with team via git) | `<repo-or-workspace-root>/.claude/skills/releasemaster/` | The team should get the same skill and config in the repo |
| **Other agents** (Codex, Cursor, OpenCode, Kimi Code) | `~/.agents/skills/releasemaster/` (user) or `<project>/.agents/skills/releasemaster/` (team) — all four read this path | Same skill in a non-Claude agent |
| **claude.ai / desktop app** | Settings → Capabilities → Skills → upload the packaged `.skill` / zip | Using Claude outside Claude Code |

Install commands (Claude Code):

```bash
# user scope (macOS/Linux)
mkdir -p ~/.claude/skills && cp -r releasemaster ~/.claude/skills/
# user scope (Windows PowerShell)
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item -Recurse releasemaster "$env:USERPROFILE\.claude\skills\"
# workspace scope
mkdir -p .claude/skills && cp -r /path/to/releasemaster .claude/skills/
```

Restart / start a new Claude Code session; the skill is then available automatically and as `/releasemaster`.

Requirements: `git` on PATH, Python 3.8+ (`python` or `python3`).

## 2. Config scope (separate from install scope)

The **config** holds product data (repos, docs path, release state). It can live:

- **Workspace**: `<workspace>/.releasemaster/releasemaster.config.json` — recommended. Commit it so the team shares repos/docs/release state.
- **User**: `~/.releasemaster/releasemaster.config.json` — for personal use or when the workspace shouldn't contain it. Can hold several products under `products`; pick by `cwd` match (`products[].roots`) or ask.

Paths inside the config are relative to the config file's workspace root when possible (portable for teammates); absolute paths are allowed for repos outside the workspace.

## 3. The init conversation

Goal: a usable config in ≤ 2 rounds of questions. Detect first, ask second — every question should come with a pre-filled default from detection.

**Detect (silently, before asking):**
1. `python scripts/detect_project.py --scan <workspace-root> --depth 2` → git repos under the workspace, existing release notes/changelogs (`releaseNotes`), and folders declared in `*.code-workspace` files (`codeWorkspaceFolders` — a declared folder that is missing or not a git repo is worth mentioning). Also check sibling folders if cwd itself is a repo.
2. For each repo: stack, platform guess (backend / frontend / mobile / library / infra), default branch, tags & versioning scheme, existing docs (README, `docs/`, `CHANGELOG.md`, wiki folders, `*.md` count), commit convention (Conventional Commits ratio).

**Ask (use multiple-choice where the tool is available):**
1. *Config scope* — workspace (recommended) / user.
2. *Repos* — "I found these repos: … Which belong to this product?" + "Any other repo paths?" Let them set a short `name` and `platform` per repo.
3. *Existing documentation* — "Is there existing documentation? Found: `<paths>`." Options: use found path / another path / none yet. If one exists, record `docs.path` and `docs.index`.
4. *Previous release notes* — if `releaseNotes` found any: "Use `<file>` as the last release note? I'll map it to commits so the next note starts right after it." On yes, follow `release-notes.md` § Mapping a previous note and write `state.lastNotes`. Also copy its naming/location into `releaseNotes.path` / `fileNamePattern`.
5. *What do you want first?* — release notes only / create documentation / both. If docs needed and none exist → level: compact / basic / full (recommend by size: 1 repo & small → compact; 2–3 repos → basic; larger or regulated → full).
6. *Language* of docs & notes (default: language of existing docs, else user's language).
7. *Versioning* (`none` is fine — notes get named by date) — semver (default if semver tags seen) / calver / custom; per-repo or product-wide version.
8. *Approval mode* — always (default) / batch / auto.

**Write** the config (schema in `config-schema.md`), show it, and print the available commands with one-line explanations, tailored: e.g. if no tags exist, say `notes` will default to date/commit ranges.

Add `.releasemaster/cache/` to `.gitignore` if you create a cache folder.

## 4. Re-running init / changing config

`/releasemaster config` — show current config; supported edits: add/remove repo, change docs path, language, level, approval, versioning. Always show the diff of the config before saving.
