# Documentation: create & maintain

## Contents
1. Principles
2. Levels: compact / basic / full
3. Creating docs from scratch
4. Updating existing docs
5. Multi-repo products

---

## 1. Principles

- **Truth from code.** Every command, port, env var, endpoint and path must come from the repo (scripts, config files, Dockerfiles, launchSettings, `.env.example`, CI). If you can't verify, write `<!-- TODO: verify: ... -->`.
- **Reader-first structure.** Organise by what the reader is trying to do (Diátaxis: tutorials, how-to guides, reference, explanation) — but don't over-engineer small projects.
- **One product, one doc set.** Users and new developers think in features, not repos.
- **Small, linked pages** over a single giant file once beyond compact level. Every page reachable from the index.
- **Docs-as-code.** Markdown in git, relative links, diagrams as Mermaid so they stay editable.

## 2. Levels

### compact — one strong README (+ CHANGELOG)
Sections: title & one-paragraph purpose · features · tech stack · quick start (prerequisites, install, run, test) · configuration (env table) · project structure (short tree) · deployment (brief) · contributing & license.
Fits: single repo, small team, prototypes. Template: `templates/README.compact.md`.

### basic — README + `docs/`
```
README.md                  # overview + quick start + links
CHANGELOG.md
docs/
  README.md                # index
  getting-started.md       # full local setup for the whole system
  architecture.md          # components, data flow, Mermaid diagram, key decisions
  configuration.md         # env vars / settings per component
  deployment.md            # environments, pipelines, release process
  development.md           # conventions, branching, commit style, testing
  components/<name>.md     # only where a component needs specifics
  releases/                # release notes per version
```
Fits: 2–4 repos, teams. Templates: `templates/docs-basic/`.

### full — basic + depth
Adds: `api/` (reference — link/generate from OpenAPI where present), `adr/` (architecture decision records, `NNNN-title.md`), `runbooks/` (operations, incidents), `troubleshooting.md`, `glossary.md` (domain terms — valuable for business analysts), `security.md`, `testing.md`, `onboarding.md`.
Fits: larger products, regulated domains, many contributors.

Recommend a level from detection; let the user choose. Mention you can grow compact → basic → full later without rewriting.

## 3. Creating docs from scratch

1. `python scripts/detect_project.py <repo>` for each repo → stack, entry points, scripts, env files, docker, CI, test setup.
2. Read the key files the detector points at (don't guess from filenames alone).
3. Propose the outline (file tree + section headings per file) → approval.
4. Write files one by one (or as batch per `approval`). Big docs: outline, then section by section.
5. Architecture: include a Mermaid diagram of components and how they talk (HTTP/gRPC/queues/DB).
6. Finish with a list of TODO: verify markers so the user knows what to check.
7. Record `docs.path`, `docs.level`, `docs.exists: true` in config.

## 4. Updating existing docs (`docs update`)

1. Read the docs index and skim structure, language, tone, heading style. Match them.
2. Collect changes for the range (same as release notes).
3. Map changes → affected pages using signals:
   - new/changed env vars or config files → configuration page
   - new endpoints/controllers/routes, OpenAPI diff → API reference
   - new scripts, Dockerfile, CI changes → getting-started / deployment
   - new module/service/repo → architecture + components
   - new domain concepts → glossary
   - new feature → feature/user guide section, README features list
4. Output an **impact table** (change → page → proposed edit type: add / modify / remove) and get approval.
5. Apply minimal, surgical edits; show diffs. Don't reformat untouched parts.
6. Also flag stale content you noticed (references to removed files, old commands), but only fix with approval.

## 5. Multi-repo products

- Docs live in one place: a dedicated docs repo, a folder in the "main" repo, or the workspace root — whatever `docs.path` says.
- `getting-started.md` brings up the whole system in order (DB → backend → frontend → mobile) with the real commands from each repo.
- `architecture.md` is the product map: each repo = a box; arrows = protocols.
- Per-component specifics go to `components/<name>.md`, linked from architecture.
- Each repo's own README stays short and links to the central docs.
