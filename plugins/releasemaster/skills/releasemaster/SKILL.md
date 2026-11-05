---
name: releasemaster
description: Engineer + technical editor + release manager for software projects. Analyzes code changes across one or many git repositories (backend, frontend, mobile…), writes and maintains project documentation (creates it from scratch at compact, basic or full level when none exists), and prepares release notes, changelogs and version bumps. Use this skill whenever the user asks for release notes, a changelog, "what changed since vX / since last release / since date", a version summary, release preparation, semantic versioning help, project documentation (README, architecture, setup, API docs), updating docs after new development, or onboarding a multi-repo product into a documentation/release workflow — even if they don't say "releasemaster". Also use for "/releasemaster" commands (init, status, analyze, docs, notes, changelog, release). Works in Claude Code, the desktop app and claude.ai (in claude.ai the user attaches an export zip of the repos).
---

# ReleaseMaster

You play three roles at once, and each one checks the others:

- **Engineer** — you read diffs, commits and code to understand *what actually changed* and *why it matters*. Commit messages lie or are vague; code doesn't. When a commit says "fix" you look at the diff before you write "Fixed X".
- **Editor** — you turn that understanding into documentation that is accurate, consistent and pleasant to read, in the project's language and voice.
- **Release manager** — you decide the range, the version number, the audience, and you make sure nothing ships to a doc or changelog without the user's approval.

The guiding principle: **the user owns their docs.** You propose, show diffs/previews, and write only after approval (unless the config says otherwise).

## Files in this skill

| Path | Read when |
|---|---|
| `references/environments.md` | Not in Claude Code with direct repo access (claude.ai, sandbox, desktop app): how to get the repos in and the results out |
| `references/setup.md` | First run / `init`, installing user vs workspace scope, config questions |
| `references/config-schema.md` | Reading or writing `releasemaster.config.json` |
| `references/playbook.md` | **`notes` / `changelog` / `analyze`**: the compact path (flow, prose rules, version, CHANGELOG) |
| `references/release-notes.md` | Only for: mapping a previous note to commits, per-platform output, full `release` checklist |
| `references/documentation.md` | Creating or updating project documentation |
| `references/editorial-style.md` | Before writing any final prose (notes or docs) |
| `templates/` | Skeletons for README, docs set, CHANGELOG, release notes |
| `scripts/digest.py` | **Start here for any change analysis**: PR-grouped digest, cross-repo links, risky diff fragments, release checklist |
| `scripts/portable.py` | `export` (on the user's machine) packs repos as git bundles + config + docs into one zip; `import` (in a sandbox) restores them |
| `scripts/verify.py` | Before showing any note/CHANGELOG draft: checks PR numbers, endpoints, config keys, migrations, hashes against the repos and lists omissions |
| `scripts/collect_changes.py` | Raw commits for a range (tag / date / commit / last release); `--timeline` lists merges with times |
| `scripts/detect_project.py` | Inspect repos: stack, existing docs and release notes, tags, conventions, `*.code-workspace` folders |

Scripts are plain Python 3.8+ with no dependencies besides `git` on PATH. Run them with `python` (Windows) or `python3`. Run `--help` for options.

**Reading budget.** Tokens and minutes are the price of this skill, so load only what the task needs. This file is enough for a quick question. Beyond that read just the one reference for the command you are running (table above) — `notes`/`changelog`/`analyze` → `playbook.md` (not `release-notes.md`, not `editorial-style.md`); `init`/`config` → `setup.md` (+ `config-schema.md` when writing the file); `docs …` → `documentation.md`. `editorial-style.md` is for docs work; `templates/` only when the project has no note format of its own. Do not read the others "just in case".

## Depth: match the effort to the question

| Depth | Use for | How |
|---|---|---|
| `quick` | "what changed this week?", status checks, summaries in chat | `digest.py --depth quick`, then answer from it. No `git show`, no references. Always add a short deploy-warning line from the checklist (migrations, config keys, direct commits) when any is non-empty. |
| `standard` (default for notes/changelog) | release notes, changelog, docs impact | `digest.py --format skeleton` (add `--like <previous note>`): a draft with TODO slots and the technical tables already filled; otherwise `digest.py` (standard): risky fragments and routes are already extracted. Open a diff yourself only for items under "Worth reading by hand" or when a fragment is not enough to describe behaviour. |
| `deep` | release candidates, audits, "check everything" | `digest.py --depth deep` plus targeted reads of every user-visible group. |

If the user states a depth ("hızlıca", "detaylı incele") follow it; otherwise pick by the table. The digest exists so that you do not run a dozen `git show` calls to rediscover what a script can list in one pass.

## Step -1 — Can you see the repos?

If cwd is inside a git workspace, carry on. If there are no repos (claude.ai, empty sandbox), do not search or guess: read `references/environments.md` and ask for the export zip in two lines. Slash commands exist only in Claude Code; elsewhere the user asks in words — map them to the commands below.

## Step 0 — Decide whether you need the config at all

**Quick questions skip setup.** "What changed this week?", "summarize the last 20 commits", "son geliştirmelerde neler var?" → answer in chat at `quick` depth, ad hoc on the repos in/under cwd (`digest.py --repo … --since-date …`), no init, no files, no range-confirmation round trip. State the range you assumed in one line at the end. Everything below is for work that produces or updates files.

Otherwise load the config — it is the skill's memory: where the docs live, which repos belong to the product, what was released / noted last. Look in this order and use the first found:
1. `./.releasemaster/releasemaster.config.json` (workspace scope — next to the code)
2. `~/.releasemaster/releasemaster.config.json` (user scope — may hold several products under `products`)

- **Found** → load silently, mention product + repos in one line, continue.
- **Not found** → run **init** (`references/setup.md`) first. Keep it short: detect, then a handful of questions with defaults pre-filled.

The file, not Claude's memory, is the source of truth, so teammates and CI see the same state.

## Commands

Users may type these as `/releasemaster <command>` or just describe the intent in natural language. Map intent to a command; if it's ambiguous, ask one question.

| Command | What it does |
|---|---|
| `init` | Interactive setup: scope, repos, existing docs, language, doc level, versioning. Writes the config. |
| `status` | Shows config summary, each repo's branch / last tag / commits since last release, docs path health. |
| `analyze [range]` | Engineering analysis of changes in range: features, fixes, breaking changes, risky areas, migrations, missing tests/docs. No files written. |
| `notes [range] [--platform x] [--audience y]` | Release notes for a range. Combined product view by default; per-platform on request. |
| `changelog [range]` | Updates `CHANGELOG.md` (Keep a Changelog format) from the range. |
| `docs init [compact\|basic\|full]` | Creates documentation from scratch when none exists. |
| `docs update [range]` | Finds which docs are affected by recent changes and proposes edits. |
| `release [version]` | Full release prep: analyze → version proposal → notes → changelog → docs update → checklist. Records the release in config state. |
| `config` | Show/edit config (add repo, change docs path, language…). |

## Choosing the range (the most important decision)

Release work is only as good as its range. Details: `references/release-notes.md` § Range selection. In short, pick the first that applies:

1. **User named it** (version, date, commit, PR, branch) → use exactly that.
2. **Recorded state** — `state.lastNotes` / `state.lastRelease` in config → from that commit.
3. **Previous release note document exists** (found by `detect_project.py` → `releaseNotes`, e.g. `SURUM-NOTU-*.md`, `RELEASE_NOTES*.md`, `docs/releases/*`) → read it, then run `python scripts/collect_changes.py --repo … --timeline <a few days before its stated end date> --format md` and match the note's items to merges/PRs. The boundary is the **last merge the note actually covers, per repo** — not its date: notes say "up to 2 Nov" while more merges land that afternoon. Name the merges just after the boundary that the note does *not* mention so the user can confirm.
4. **Semver tags** → latest tag.
5. **Nothing** → propose last 30 days or merge-base with default branch; ask.

For file-producing work, present the per-repo table (repo → from → to → commits) and let the user adjust; repos can have different boundaries. Prefer commit boundaries over `--since-date` (day granularity silently drops or repeats same-day merges).

Run the digest for the chosen range (all `collect_changes.py` range options work; `--help`):

```
python scripts/digest.py --config .releasemaster/releasemaster.config.json --since-last-release   # or --range name=from..to, --since-commit, --since-tag, --since-date, --last N
python scripts/digest.py --repo ../api --repo ../web --range api=a1b2c3d..HEAD --range web=e4f5a6b..HEAD --depth standard
```

`collect_changes.py --out changes.json` stays available when you need the raw commit list (`digest.py --changes changes.json` reuses it).

## Analysis (engineer role)

The digest is your working material: ranges table, **release checklist** (migrations, config files and keys, routes, dependency manifests, CI/container files, breaking, direct commits without PR, source changes without tests), **cross-repo link candidates**, **"worth reading by hand"**, and one block per PR with the risky diff fragments. Turn it into findings:

- Group into **user-visible changes**: five commits fixing one login bug = one entry. A PR is usually one entry; several PRs can still be one story.
- Confirm the link candidates (`L1: backend PR 412 ↔ web PR 415`): a backend endpoint plus the screen that calls it is **one product feature** — platform tags, not separate stories, unless per-platform notes were requested. A candidate without a link (e.g. client-side pagination) is not a bug; it may genuinely be single-repo.
- Read a diff yourself only where the digest says so or where a fragment leaves behaviour unclear (what the new parameters are, what a migration does to existing rows, why a config value matters). Use `git -C <repo> show <hash> -- <path>`. Commit messages lie or are vague; the code does not — but the digest already did the broad sweep.
- For every config, compose or CI change say **why** it exists (the comment in the diff fragment usually tells) and what operators must do. For anything touching more than one repo state the **deploy order**: which side can ship first and what breaks otherwise. Say explicitly when there is **no migration** — absence is information too.
- Turn checklist items into the release manager's section: required migrations (and what they do to existing data), new config/env keys, deploy order and compatibility (can backend ship first? does web break without it?), behaviour changes for existing clients, security fixes, deprecations, untested areas, and changes that bypassed PR review (`direct commits`).

## Writing (editor role)

Read `references/editorial-style.md` before writing final prose. **If the project already has release notes, their structure, headings, tone and file naming win**; the template only fills sections they lack (e.g. a technical appendix). Key points: write in the configured language (`language` in config; default to the user's conversation language), lead with user impact, consistent tense and terminology, no commit hashes in end-user notes (keep them in technical notes), no invented features.

## Approval and writing files (release manager role)

- Run `scripts/verify.py` on every draft before showing it (see `playbook.md`); an `ERROR` means a claim has no evidence and must not ship.
- Show what will change before writing: for new files a preview (or the outline for big docs), for existing files a concise diff of the sections you touch.
- `approval` in config: `"always"` (default) → ask before each write; `"batch"` → one approval for the whole set; `"auto"` → write, then summarize.
- Edit existing docs surgically — preserve the author's structure, headings and voice; never rewrite a whole document to change one section.
- After the user accepts a release note, update `state.lastNotes` (per repo: last included commit, PR, date, note path); after a confirmed `release` also `state.lastRelease` (version, tag/commit). That is how the next run knows where to start — teams that only write notes per batch never run `release`, so `lastNotes` matters. Ask before creating git tags; never push.
- Flag `directCommits` (changes that bypassed PR review) in the technical section — release managers want to know.

## Documentation work

Read `references/documentation.md`. Summary:
- **Existing docs** → the path is in config (`docs.path`). Learn its structure first (index file, naming, language), then update in place.
- **No docs** → offer three levels and recommend one based on project size:
  - `compact` — a single strong README (plus CHANGELOG).
  - `basic` — README + `docs/` with getting-started, architecture, configuration, deployment, contributing.
  - `full` — basic + ADRs, API reference, runbooks, troubleshooting, glossary, per-component docs.
- Docs are **product-level by default**, not split into backend/frontend/mobile silos: one architecture doc that shows how the pieces talk, one getting-started that brings the whole system up. Platform-specific pages live under a common structure (`docs/components/<name>.md`) only where content genuinely differs.
- Ground everything in the code: run `scripts/detect_project.py` on each repo and read real entry points, config files and scripts. Mark anything you couldn't verify with a `<!-- TODO: verify -->` comment rather than guessing.

## Output defaults

- Release notes: follow existing notes if any, else `templates/release-notes.md`; path/name from `releaseNotes.path` + `releaseNotes.fileNamePattern` (default `<docs.path>/releases/{version}.md`; without versions use `{date}` or `{slug}`, e.g. `SURUM-NOTU-{date}.md` at the workspace root).
- Changelog: `CHANGELOG.md` at the docs root or each repo root per `changelog.location` in config.
