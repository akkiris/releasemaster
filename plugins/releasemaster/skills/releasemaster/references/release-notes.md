# Release notes, changelog & versioning

## Contents
1. Range selection
2. Collecting changes
3. Classifying & grouping
4. Version proposal
5. Audiences & formats
6. Multi-repo / multi-platform output
7. CHANGELOG.md
8. Release checklist

---

## 1. Range selection

Run `python scripts/collect_changes.py --config <cfg> --suggest` first. It prints, per repo: current branch, HEAD, recorded last release, the 5 most recent tags (with dates and commit counts since), and commits in the last 7/30 days.

Decision table:

| Situation | Default range | Why |
|---|---|---|
| `state.lastNotes.<repo>` / `state.lastRelease.<repo>` recorded | that commit/ref → HEAD | Exactly what was reported/shipped last time |
| previous release-note document, no state | last merge the note covers → HEAD (see below) | Teams often write notes by hand without tags |
| semver tags, nothing recorded | latest tag → HEAD | Tags are the team's release markers |
| user names a version ("since 2.3") | that tag → HEAD (resolve `2.3`, `v2.3`, `v2.3.0`) | |
| user names a date ("since 1 Oct", "this sprint") | `--since-date` | Use the date as given; ask for sprint start if unknown |
| user names a commit/PR/branch | that ref → HEAD | |
| between two versions | `--range repo=v1.2.0..v1.3.0` | Historical notes |
| no tags, no state, nothing said | propose: last 30 days **or** since merge-base with default branch; ask | |

**Mapping a previous note to commits.** Run `collect_changes.py --repo … --timeline <date a few days before the note's end> --format md`: it lists first-parent merges with time, PR number and subject. Match each section of the note to merges (feature names ↔ PR subjects; diff when unclear). The boundary per repo is the last covered merge. Record it in `state.lastNotes` during init (ask: "Found `<note>`; its last covered merges look like backend PR 398, web PR 401 — use these as the starting point?"). Call out uncovered merges from the same day explicitly.

**Feature-branch notes.** Some notes compare a feature branch to `development` before merge ("development → feat/x"). Use `--range name=development..origin/feat/x` (or the merge-base) per repo.

Multi-repo nuance: repos rarely share tags. Product-level release ⇒ use each repo's own last-release boundary; if missing for some, fall back per repo (tag → date of the product's last release → ask). Show the table and let the user adjust any row:

```
Repo     From                 To      Commits
api      v1.4.0 (2026-10-01)  HEAD    37
web      v1.4.0 (2026-10-01)  HEAD    52
mobile   9c8d7e6 (2026-09-28) HEAD    14
```

Branch: default is the current HEAD of each repo. If a repo isn't on its `defaultBranch`, say so — notes for a release usually come from the release/main branch. Use `--to <ref>` to target another ref without checking out.

## 2. Collecting changes

Use the digest; it wraps `collect_changes.py` and already groups by PR, links repos, and extracts the risky fragments:

```
python scripts/digest.py --config .releasemaster/releasemaster.config.json --since-last-release
python scripts/digest.py --repo api --repo web --range api=a1b2c3d..HEAD --range web=e4f5a6b..HEAD --depth standard
```

Range options (shared with `collect_changes.py`): `--since-last-release`, `--since-tag [TAG]`, `--since-date DATE`, `--since-commit SHA`, `--last N`, `--range name=from..to` (repeatable, `*` = all repos), `--to REF`, `--repos a,b`, `--platform x`, `--merges`. Without `--config`, pass `--repo PATH` (repeatable). Depth: `--depth quick|standard|deep`.

Raw data: `collect_changes.py --out changes.json` gives per repo the resolved range, `commits[]` (hash, date, author, subject, body, type, scope, breaking, pr, refs, files), `merges[]`, `directCommits`, `byType`, `stats`, `signals` (file paths for migrations, dependencies, config, api_surface, ci_cd, tests, docs). `digest.py --changes changes.json` reuses it. `--timeline DATE` lists first-parent merges with time and PR number (used to map a previous note to commits).

## 3. Classifying & grouping

Map to sections:

| Conventional type | Section |
|---|---|
| `feat` | ✨ New features / Added |
| `fix` | 🐛 Fixes / Fixed |
| `perf` | ⚡ Performance / Changed |
| `refactor`, `style`, `build`, `ci`, `chore`, `test` | Internal (technical notes only; omit for end users unless impactful) |
| `docs` | Documentation |
| `revert` | Note what was reverted; cancel out the reverted entry if inside range |
| `!` / `BREAKING CHANGE:` | ⚠️ Breaking changes (always at top) |
| `security`, CVE refs, auth/crypto fixes | 🔒 Security |
| deprecation wording | Deprecated |
| non-conventional message | Classify by reading the diff; `type: "other"` from the script means "you decide" |

Grouping rules:
- One user-visible change = one entry, even if it spans many commits or repos.
- Merge cross-repo pieces into one entry and tag platforms: `**Vehicle maintenance reminders** — … _(api, web, mobile)_`.
- Drop noise: merge commits, version bumps, lint, "wip", reverted-then-reapplied pairs.
- Keep refs (issue/PR numbers) on entries in technical notes; in end-user notes only if the project links issues publicly.

## 4. Version proposal (semver)

- Any breaking change → **major** (pre-1.0: minor).
- Any `feat` → **minor**.
- Only fixes/perf/internal → **patch**.
- Pre-release: `-rc.1`, `-beta.2` if the user is preparing a candidate.

Present: "Proposed **1.5.0** (minor — 6 features, no breaking changes)". The user decides. Calver: `YYYY.MM.N`. Mobile apps may also need build numbers — ask, don't invent.

## 5. Audiences & formats

- **end-user** — what they can now do, what got better, what they must do. Plain language, no internals, no hashes.
- **technical** — for devs/ops/QA: breaking changes with migration steps, API changes (endpoint/method/payload), DB migrations, new env vars/config, dependency upgrades, deprecations, commit/PR refs, known issues.
- **mixed** (default) — end-user summary first, then a "Technical details" section.

A **quick summary** request ("son geliştirmelerde neler var?") → answer in chat: 3–8 bullets grouped by theme, platform tags, then a short "deploy öncesi dikkat" block (migrations, config, behaviour changes) only if there is something. No files, no init, no confirmation round trip.

Use `templates/release-notes.md` for file output.

## 6. Multi-repo / multi-platform output

Default (`groupBy: product`): one document, platform tags on entries, a "Components" table at the end listing each repo's range and version.

On request (`--platform` or `groupBy: platform`): either
- separate files per platform (`releases/1.5.0-mobile.md`) — useful for store release notes; or
- one file with per-platform sections.

Ask which when the user requests per-platform notes and it's unclear. Store release notes (App Store / Play) have length limits (~4000 chars, but users read ~3 lines) — keep them very short and end-user only.

## 7. CHANGELOG.md

Format: [Keep a Changelog](https://keepachangelog.com) — `## [Unreleased]`, then `## [x.y.z] - YYYY-MM-DD` with `### Added / Changed / Deprecated / Removed / Fixed / Security`. Newest on top. Comparison links at the bottom if the repo has a remote URL.

Use only the six standard categories (Added, Changed, Deprecated, Removed, Fixed, Security). Deploy, migration and config remarks do not get a category of their own: config or behaviour changes go under **Changed**, and the deploy checklist belongs in the release note. Existing sections stay byte-identical; only the footer links change.

Updating: insert the new version section under `[Unreleased]` (move matching items out of Unreleased), never rewrite older sections. If no CHANGELOG exists, create from `templates/CHANGELOG.md`. Respect an existing different format (e.g. no categories) rather than converting it.

## 8. Release checklist (`release` command)

Produce and walk through:
1. Range confirmed per repo
2. Analysis reviewed: breaking changes, migrations, config/env, security
3. Version decided
4. Release notes written & approved
5. CHANGELOG updated & approved
6. Affected docs updated & approved (`docs update`)
7. Version bumps in manifests (`package.json`, `*.csproj` `<Version>`, `pubspec.yaml`, `build.gradle`, `Info.plist`…) — propose, edit only with approval
8. Tag suggestions (`git tag -a v1.5.0 -m ...`) — print commands; run only if asked; never push
9. `state.lastRelease` updated in config
