# Editorial style

Write like a careful technical editor who also understands the code.

## Voice
- Language: `product.language` from config; otherwise match existing docs; otherwise the user's language. Turkish: use the established technical terms the team already uses (e.g. "endpoint", "deploy" often stay in English) — copy their vocabulary from existing docs and commits rather than forcing translations.
- Active voice, present tense for docs ("The API validates…"), past tense or noun phrases for release notes ("Added…", "Araç bakım hatırlatıcıları eklendi").
- Lead with impact: what the reader can now do / what changed for them, then how.
- One idea per bullet. Bullets start with a capital/strong verb, consistent grammatical form within a list.

## Accuracy
- Never describe a feature you didn't see in code or commits. If a commit message promises more than the diff delivers, describe the diff.
- Numbers, names, paths, env vars, endpoints: copy exactly, in `code` formatting.
- Keep uncertainty visible: `<!-- TODO: verify -->` in files; "unclear from the diff" in chat.

## Consistency
- Same term for the same thing everywhere (pick "vehicle" or "araç" and stick to it; maintain `glossary.md` at full level).
- Same heading levels and section order across release notes versions.
- Dates ISO `YYYY-MM-DD`. Versions with or without `v` — follow the project.

## Release-note entries
Good: `**Bulk vehicle import** — Upload up to 5,000 vehicles from an Excel file; validation errors are shown per row. _(web, api)_`
Bad: `feat(vehicle): add import endpoint + ui (#412)`

Breaking change entries always say **what breaks, who is affected, what to do**:
`⚠️ **GET /api/vehicles now paginates** — responses return \`{ items, total }\` instead of an array. Clients must read \`items\`. Mobile ≥ 1.5 already supports this.`

## Formatting
- Markdown, ATX headings, fenced code blocks with language, tables for config/env, Mermaid for diagrams.
- Keep lines un-wrapped (no hard wraps) unless the project hard-wraps.
- Emoji section markers in release notes are optional — follow existing notes; default to none for technical audiences.
