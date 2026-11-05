# Playbook — notes, changelog, analyze (the compact path)

Read this instead of `release-notes.md` + `editorial-style.md` for routine work. Open `release-notes.md` only for: mapping a previous note to commits, per-platform output, the full `release` checklist.

## Flow
1. Range: user's words → `state.lastNotes`/`lastRelease` → previous note mapped to merges → tag → ask. Show the per-repo table (from → to → commits); commit boundaries, not dates.
2. `python scripts/digest.py --config … --since-last-release --format skeleton [--like <previous note>]` → draft with entries, technical tables and the Components table already filled. (Use `--format md` when you only need to read, e.g. `analyze`.)
3. Turn each `TODO` into prose. Open a diff only for items in the digest's "worth reading by hand" or when a fragment cannot explain behaviour. Confirm or split each "link candidate". Delete empty sections.
4. **Verify before showing**: `python scripts/verify.py --note <draft> [--section X.Y.Z] <same range options as the digest>` (no LLM, <1 s). Fix every `ERROR` (PR, endpoint, config key, migration or commit not found anywhere — remove or correct it). Read each `WARN`/`CHECK` once: out-of-range PRs are fine as boundary references; a migration, config key or direct commit the note never mentions, or a "no migration" claim next to a real migration, must be fixed. It checks facts (numbers, paths, keys, names), not whether a sentence describes behaviour correctly — that is still your reading of the diff.
5. Show preview/diff, write after approval, update `state.lastNotes`.

## What the prose must do
- One user-visible change = one entry; backend + web pieces of a feature are one entry with platform tags. Lead with what the reader can now do; then how.
- Follow the team's existing note (headings, tone, language, file name) — `--like` shows its headings. Templates only fill missing sections.
- Breaking entries: what breaks · who is affected · what to do.
- Technical details: for each migration say what it does to existing rows; for each config/compose change say why and what operators do; state deploy order (which side ships first, what breaks otherwise); say "no migration" when there is none; list direct commits (no PR).
- Copy names, paths, keys, endpoints exactly in `code`. Never describe what the diff does not show; mark doubt with `<!-- TODO: verify -->` or "unclear from the diff".
- Dates ISO. Same term for the same thing throughout. Language: config `product.language`, else the existing notes, else the user's.

## Version (only if the project versions)
Breaking → major (pre-1.0 minor) · any feat → minor · fixes only → patch. Propose, user decides. No versions (`scheme: none`) → name by date/slug per `releaseNotes.fileNamePattern`.

## CHANGELOG.md
Keep a Changelog. Insert the new section under `[Unreleased]`; existing sections stay byte-identical; only the footer links change. Only six categories: Added, Changed, Deprecated, Removed, Fixed, Security (deploy/config remarks go under Changed or in the release note). Respect a different existing format. No file → `templates/CHANGELOG.md`.

## Quick questions
Chat answer from `--depth quick`: 3–8 bullets by theme, platform tags, one deploy-warning line if migrations/config keys/direct commits exist. No files, no init.
