# Environments: Claude Code, desktop app, claude.ai

The skill is the same everywhere; what differs is whether it can see the user's repos and where results go. Decide in the first minute, silently.

| Situation | How to tell | Repos | Config | Deliver |
|---|---|---|---|---|
| **Claude Code** (terminal / IDE) | cwd is inside the workspace; `git rev-parse` works | read directly | `./.releasemaster/…` or `~/.releasemaster/…` | write into the repo after approval |
| **Desktop app, folder linked** | `mcp__remote-devices__` file tools present | there is no shell on the user's machine, so git history cannot be read in place: ask the user to run `portable.py export` once and attach the zip (or stage it through the bridge) | the config file via the bridge | commit files through the bridge into the connected folder |
| **claude.ai / sandbox, no access** | cwd is an empty sandbox; no repos | user attaches `releasemaster-upload.zip` | inside that zip | hand the files back (SendUserFile / artifact); say plainly the user must commit them |

## Sandbox flow (no access to the user's disk)

1. No repos and no zip? Say in two lines what is needed, then stop asking:
   *"On your machine, in the workspace root: `python scripts/portable.py export` (add `--repo ../api --repo ../web` before the first init). Attach the resulting `releasemaster-upload.zip` here."* Python and git are the only requirements; the user may need the script from the skill folder (it ships in `scripts/`).
2. With the zip: `python scripts/portable.py import <zip> --dest rm-workspace`, then use `--config rm-workspace/.releasemaster/releasemaster.config.json` (or `--repo rm-workspace/<name>` when there is no config) for everything else. Nothing else changes: digest, skeleton, verify, init.
3. The zip holds only **commits**. If the manifest says `uncommittedChanges: true`, tell the user that work in progress is not part of the notes.
4. When done run `python scripts/portable.py finish --dest rm-workspace --out <outputs>`; it writes `.releasemaster/releasemaster.config.json` with the user's original paths. Return that file (it carries `state.lastNotes`) and the new release note / CHANGELOG / docs files at their relative paths. Without that file the next session starts from scratch — say so in one line. In claude.ai the user can keep the config in the repo and attach it with the next export.

## Differences to handle

- **Slash commands exist only in Claude Code** (plugin `/releasemaster:…`). Elsewhere the same work is requested in words ("release notes since the last note", "what changed this week", "status"). Map the words to the commands in SKILL.md.
- **Questions**: use the multiple-choice question tool when present; otherwise ask in plain text, one message, defaults pre-filled.
- **Network**: the sandbox usually cannot reach private hosts (Azure DevOps, internal Git). Never try to clone; use the export zip.
- **Paths**: the user's Windows paths (`D:\dev\…`) mean nothing in the sandbox. Config paths are rewritten by `import` and restored by `finish`; never hand back the sandbox copy of the config directly.
- **Approval** still applies. In a sandbox, "write" means "produce the file and show a preview"; the user commits it.
