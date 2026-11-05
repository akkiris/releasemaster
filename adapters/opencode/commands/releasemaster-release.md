---
description: Uçtan uca sürüm hazırlığı / End-to-end release prep
---

Load the `releasemaster` skill with the skill tool and follow its SKILL.md for this one command only. Load just the reference file SKILL.md names for it. Decide from the config and detection instead of asking; if a question is unavoidable, ask once with defaults pre-filled.

Command: `release`. Arguments from the user: $ARGUMENTS (expected: [versiyon / version] [aralık / range])

Run the full release flow (references/release-notes.md section 8). Never tag or push without being asked; record state.lastRelease only after confirmation.
