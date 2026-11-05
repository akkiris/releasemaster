# ReleaseMaster

**English** · [Türkçe](README.tr.md)

A Claude skill (also a Claude Code plugin, and usable in Codex, Cursor, OpenCode and Kimi Code) that reads your git history across one or many repositories and turns it into release notes, changelogs and project documentation, with an engineer's eye for what really changed.

- **Engineer**: reads diffs, not just commit messages: migrations, new config keys, routes, dependency changes, breaking changes, commits that bypassed review.
- **Editor**: writes it up in your project's own format, language and tone. If you already have release notes, it follows them.
- **Release manager**: picks the range (since last note / tag / date / commit), proposes a version, keeps a changelog, tracks what was last released, and never writes a file without your approval.

One product often means several repositories (backend, web, mobile). ReleaseMaster treats them as one product: one document, platform tags on entries, per-platform notes only when you ask.

## Install

**Claude Code (plugin, recommended)**

```
/plugin marketplace add akkiris/releasemaster
/plugin install releasemaster@releasemaster
```

Restart the session; typing `/releasemaster:` lists every command with its description, so there is nothing to memorise.

**Other agents: Codex, Cursor, OpenCode, Kimi Code**

They all read the open Agent Skills format (a folder with `SKILL.md`) from `.agents/skills/`, so one copy serves all four. No Python needed for the install, just copy the folder:

```powershell
# Windows PowerShell
git clone https://github.com/akkiris/releasemaster.git
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
Copy-Item -Recurse -Force releasemaster\plugins\releasemaster\skills\releasemaster "$HOME\.agents\skills\releasemaster"
```

```bash
# macOS / Linux
git clone https://github.com/akkiris/releasemaster.git
mkdir -p ~/.agents/skills
cp -r releasemaster/plugins/releasemaster/skills/releasemaster ~/.agents/skills/releasemaster
```

For one project only (shared with the team through git), copy to `<project>/.agents/skills/releasemaster` instead. Restart the agent afterwards.

OpenCode only, optional: custom commands `/releasemaster-notes`, `/releasemaster-init`, …

```powershell
New-Item -ItemType Directory -Force "$HOME\.config\opencode\commands" | Out-Null
Copy-Item releasemaster\adapters\opencode\commands\*.md "$HOME\.config\opencode\commands\"
```

Prefer a script? `python tools/install.py --for codex cursor opencode kimi` does the same (`--scope project`, `--dry-run` and `--uninstall` exist). It is optional; nothing else depends on it.

If you use Claude Code **and** Cursor/OpenCode: install the Claude plugin as above and the copy to `.agents/skills`. Do not also put the skill in `.claude/skills`, because Cursor and OpenCode read that folder too and would list the skill twice.

**claude.ai / desktop app (skill upload)**

```
python tools/build_skill_zip.py        # writes dist/releasemaster-skill.zip
```

Upload the zip under Settings → Capabilities → Skills. See [claude.ai](#using-it-in-claudeai) for how to give it your repositories.

Requirements on the machine where the scripts run: `git` and Python 3.8+, no packages.

## Commands

| Command | What it does | Writes files |
|---|---|---|
| `/releasemaster:init` | Detects repos, existing docs and previous release notes; writes the config | config only |
| `/releasemaster:status` | Repos, last note/release, commits since | no |
| `/releasemaster:analyze [range]` | Engineering analysis: breaking changes, migrations, config, risks | no |
| `/releasemaster:notes [range]` | Release notes (follows your existing format) | yes, with approval |
| `/releasemaster:changelog [range]` | Updates `CHANGELOG.md` (Keep a Changelog), older sections untouched | yes, with approval |
| `/releasemaster:docs-init [compact\|basic\|full]` | Creates documentation from scratch | yes, with approval |
| `/releasemaster:docs-update [range]` | Finds docs affected by recent changes and edits them surgically | yes, with approval |
| `/releasemaster:release [version]` | Whole release prep with checklist | yes, with approval |
| `/releasemaster:config` | Show / edit settings | config only |

How you call it depends on the agent:

| Agent | Call it with |
|---|---|
| Claude Code | `/releasemaster:notes` (plugin commands, autocompleted) |
| Codex | `$releasemaster notes` |
| Cursor | `/releasemaster notes` |
| OpenCode | `/releasemaster-notes` (after copying the optional commands) or ask in words |
| Kimi Code | `/skill:releasemaster notes` |

In every agent you can also just describe what you want; the skill maps it to the right command.

No command needed for quick questions: "what changed in the last week?" answers in chat from a compact digest and writes nothing.

Ranges: `since the last release`, `since v1.4.0`, `since 1 Oct`, `since commit a1b2c3d`, or per repo `api=v1.4.0..HEAD web=9c8d7e6..develop`. If you give none it suggests one and asks.

## Step by step

<!-- screenshots: docs/images/ -->

1. **Set up once**: `/releasemaster:init`. It finds your repositories (including folders declared in `*.code-workspace`), asks whether documentation exists, and, if you already keep release notes, offers to map the last one to commits so the next note starts exactly after it. Result: `.releasemaster/releasemaster.config.json`, the skill's memory (commit it to share with your team).
2. **Look around**: `/releasemaster:status` shows, per repo, branch, last note/release and how many commits came after.
3. **Ask a quick question**: "what changed this week in backend and web?" gives 3–8 bullets by theme and one deploy-warning line (migrations, new config keys, commits without PR). No files, no setup.
4. **Write release notes**: `/releasemaster:notes`. Behind the scenes: a digest groups commits by PR, links the backend and frontend pieces of one feature and extracts the risky diff fragments; a draft skeleton fills the technical tables; the model writes the prose; a checker then verifies every PR number, endpoint, config key, migration and commit hash against the repositories. You see a preview and approve before anything is written.
5. **Update the changelog**: `/releasemaster:changelog`. A new section goes under `[Unreleased]`; existing sections stay byte-identical.
6. **Documentation**: `/releasemaster:docs-init` when there is none (compact: one strong README; basic: README + `docs/`; full: plus ADRs, API reference, runbooks) or `/releasemaster:docs-update` after new development.

## What it does under the hood

| Script | Role |
|---|---|
| `scripts/collect_changes.py` | Raw commits for a range (tag / date / commit / last release / previous note), PR mapping from merge commits, signals |
| `scripts/digest.py` | PR-grouped digest, cross-repo link candidates, risky diff fragments, release checklist; `--format skeleton` for a draft note |
| `scripts/verify.py` | Fact check of a note against the repos: invented PR, endpoint, config key, migration or hash is an error; omissions are flagged |
| `scripts/detect_project.py` | Stack, existing docs and release notes, tags, conventions |
| `scripts/portable.py` | Packs repos as git bundles for sandboxes without disk access (claude.ai) |

The model reads a compact digest instead of dozens of `git show` outputs, and checks its own claims with a script that needs no model.

## Using it in claude.ai

In claude.ai the skill runs in a sandbox that cannot see your disk. Pack your history once:

```
python plugins/releasemaster/skills/releasemaster/scripts/portable.py export
# no config yet: ... export --repo ../api --repo ../web
```

Attach the resulting `releasemaster-upload.zip` and ask in words ("write release notes since the last note"). The zip carries commits only (all branches and tags), not uncommitted work. When finished you get the new files and the updated config back; commit them, and attach the config with the next export so the skill knows where it stopped. Slash commands depend on the agent (see Commands); claude.ai has none, so ask in words.

## Multi-repository config

```json
{
  "product": { "name": "Acme", "language": "en", "versioning": { "scheme": "semver" } },
  "repos": [
    { "name": "api", "path": "../acme-api", "platform": "backend", "defaultBranch": "main" },
    { "name": "web", "path": "../acme-web", "platform": "frontend", "defaultBranch": "main" }
  ],
  "docs": { "path": "docs", "exists": true },
  "releaseNotes": { "path": "docs/releases", "fileNamePattern": "{version}.md" },
  "approval": "always"
}
```

Full schema: [`config-schema.md`](plugins/releasemaster/skills/releasemaster/references/config-schema.md).

## How well does it work?

Tested on one real product (a .NET backend and a React frontend, Azure DevOps style "Merged PR" history) with five scenarios, 2–3 runs each, against the same model without the skill:

- First-time boundary detection from an existing hand-written note: 91–100 % of checks passed with the skill vs 64 % without.
- Quick weekly summary: 96 % vs 62 % at about the same time and tokens.
- Routine tasks (second round of notes, changelog update): same quality as without the skill, but roughly 15–40 % slower and 7–10 % more tokens.
- No invented endpoints or PR numbers were seen in 30 graded runs; `verify.py` exists as insurance and catches injected faults in its test cases.

These are small samples from one project, measured with Claude only. The skill follows the open Agent Skills format and the install paths come from each agent's documentation, but it has not been run in Codex, Cursor, OpenCode or Kimi Code yet. Treat all of this as a signal, not a guarantee.

## Repository layout

```
.claude-plugin/marketplace.json            marketplace manifest (Claude Code)
plugins/releasemaster/
  .claude-plugin/plugin.json               plugin manifest
  commands/                                /releasemaster:<command> files
  skills/releasemaster/                    the skill: SKILL.md, references/, templates/, scripts/
adapters/opencode/commands/                optional OpenCode custom commands
tools/install.py                           optional installer for the other agents
tools/build_skill_zip.py                   zip for claude.ai upload
```

## Safety

Every write is shown as a preview or diff and needs your approval (`approval` in the config can relax this). Nothing is tagged, committed or pushed unless you ask. Existing documents are edited surgically, never rewritten.
