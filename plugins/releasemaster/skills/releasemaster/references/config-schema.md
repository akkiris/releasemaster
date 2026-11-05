# releasemaster.config.json

JSON (not YAML) so the bundled scripts need no extra packages. Unknown keys are preserved — never drop keys you don't understand when rewriting.

```json
{
  "$schemaVersion": 1,
  "product": {
    "name": "Acme",
    "description": "Fleet management platform",
    "language": "tr",
    "versioning": {
      "scheme": "semver",  // semver | calver | none (no versions: name notes by date/slug)
      "mode": "product",
      "tagPattern": "v{version}"
    }
  },
  "repos": [
    {
      "name": "api",
      "path": "../acme-api",
      "platform": "backend",
      "defaultBranch": "main",
      "tagPattern": "v{version}",
      "include": true
    },
    {
      "name": "web",
      "path": "../acme-web",
      "platform": "frontend",
      "defaultBranch": "main"
    },
    {
      "name": "mobile",
      "path": "D:/dev/acme-mobile",
      "platform": "mobile",
      "defaultBranch": "develop"
    }
  ],
  "docs": {
    "path": "docs",
    "index": "docs/README.md",
    "level": "basic",
    "exists": true
  },
  "changelog": {
    "location": "product",
    "path": "CHANGELOG.md",
    "format": "keepachangelog"
  },
  "releaseNotes": {
    "path": "docs/releases",            // "." = workspace root
    "fileNamePattern": "{version}.md",  // tokens: {version} {date} {slug}; e.g. "SURUM-NOTU-{date}.md"
    "sourceBranch": "development",      // branch notes are built from (defaults to repo defaultBranch)
    "defaultAudience": "mixed",
    "groupBy": "product",
    "includeCommitRefs": "technical-only"
  },
  "approval": "always",
  "state": {
    "lastNotes": {
      "api": { "commit": "9f8e7d6", "pr": "412", "date": "2026-11-04", "note": "SURUM-NOTU-2026-11-04.md" },
      "web": { "commit": "3c4d5e6", "pr": "418", "date": "2026-11-04", "note": "SURUM-NOTU-2026-11-04.md" }
    },
    "lastRelease": {
      "product": { "version": "1.4.0", "date": "2026-10-01" },
      "api":    { "version": "1.4.0", "ref": "v1.4.0", "commit": "a1b2c3d", "date": "2026-10-01" },
      "web":    { "version": "1.4.0", "ref": "v1.4.0", "commit": "e4f5a6b", "date": "2026-10-01" },
      "mobile": { "version": "1.4.0", "commit": "9c8d7e6", "date": "2026-09-28" }
    },
    "history": [
      { "version": "1.4.0", "date": "2026-10-01", "notes": "docs/releases/1.4.0.md" }
    ]
  }
}
```

## Field notes

- `product.language` — `tr`, `en`, … Output language for docs and notes.
- `product.versioning.mode` — `product` (one version for all repos, typical for a single product release) or `per-repo` (each repo versioned independently, e.g. libraries, mobile store builds).
- `repos[].path` — relative to the workspace root (the folder that contains `.releasemaster/`) or absolute. Forward slashes work on Windows.
- `repos[].platform` — free text; common: `backend`, `frontend`, `mobile`, `desktop`, `library`, `infra`, `docs`. Used for tagging entries and for `--platform` filtering, not for splitting docs.
- `repos[].include` — `false` keeps the repo known but excluded from default runs.
- `docs.level` — `compact` | `basic` | `full`.
- `changelog.location` — `product` (one CHANGELOG at docs root) | `per-repo` (each repo root) | `both`.
- `releaseNotes.defaultAudience` — `end-user` | `technical` | `mixed` (user-facing summary + technical appendix).
- `releaseNotes.groupBy` — `product` (default: one story, platform tags) | `platform` (sections per platform).
- `approval` — `always` | `batch` | `auto`.
- The JSON block above shows `//` comments for explanation only — real config files must be plain JSON.
- `state.lastNotes` — last commit included in an accepted release note, per repo. Written after the user accepts a note, or during init when bootstrapping from an existing hand-written note. Range default prefers the newer of `lastNotes` / `lastRelease`.
- `state.lastRelease` — written only after the user confirms a release. `commit` is the authoritative boundary; `ref` (tag) is preferred when it exists.

## User-scope multi-product variant

`~/.releasemaster/releasemaster.config.json`:

```json
{
  "$schemaVersion": 1,
  "products": [
    { "roots": ["D:/dev/acme"], "...": "same shape as a workspace config" }
  ]
}
```

Select the product whose `roots` contains cwd; otherwise ask.
