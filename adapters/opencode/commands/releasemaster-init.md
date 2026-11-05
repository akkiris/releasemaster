---
description: Kurulum: repoları, dokümanı ve önceki sürüm notunu tespit edip config yazar / Detect repos, docs and previous notes; write the config
---

Load the `releasemaster` skill with the skill tool and follow its SKILL.md for this one command only. Load just the reference file SKILL.md names for it. Decide from the config and detection instead of asking; if a question is unavoidable, ask once with defaults pre-filled.

Command: `init`. Arguments from the user: $ARGUMENTS (expected: [workspace yolu])

Run the init flow (references/setup.md). Detect first, ask only what detection cannot answer, write .releasemaster/releasemaster.config.json after showing it.
