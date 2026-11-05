#!/usr/bin/env python3
"""Install the ReleaseMaster skill into the agents you use.

  python tools/install.py --for codex cursor opencode kimi            # user scope, all four share ~/.agents/skills
  python tools/install.py --for claude                                # ~/.claude/skills (prefer the plugin in Claude Code)
  python tools/install.py --for opencode --scope project --project-dir D:\\work\\myapp
  python tools/install.py --for codex --uninstall
  python tools/install.py --for cursor --dry-run

Where each agent reads skills (checked against their docs, Nov 2026):
  Codex      <project>/.agents/skills, ~/.agents/skills
  Cursor     <project>/.agents/skills or .cursor/skills, ~/.agents/skills or ~/.cursor/skills (also reads .claude/skills)
  OpenCode   <project>/.opencode/skills, ~/.config/opencode/skills, and .agents/skills, .claude/skills
  Kimi Code  <project>/.kimi-code/skills or .agents/skills, ~/.kimi-code/skills or ~/.agents/skills
  Claude     <project>/.claude/skills, ~/.claude/skills

So one copy in .agents/skills serves Codex, Cursor, OpenCode and Kimi Code. OpenCode also gets /releasemaster-<command>
files (its custom commands). Cursor and OpenCode also read .claude/skills: installing into both .claude and .agents makes
the skill appear twice there, so the script warns.
"""
import argparse
import os
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SKILL = os.path.join(ROOT, "plugins", "releasemaster", "skills", "releasemaster")
OC_CMDS = os.path.join(ROOT, "adapters", "opencode", "commands")
HOME = os.path.expanduser("~")
HOWTO = {
    "codex": "Codex: `$releasemaster notes` or just ask in words",
    "cursor": "Cursor: `/releasemaster notes` (or @releasemaster)",
    "opencode": "OpenCode: `/releasemaster-notes`, `/releasemaster-init` ... or ask in words",
    "kimi": "Kimi Code: `/skill:releasemaster notes`",
    "claude": "Claude Code: `/releasemaster notes` (for `/releasemaster:notes` install the plugin instead)",
}


def dest_skills(tool, scope, proj):
    base = HOME if scope == "user" else proj
    if tool == "claude":
        return os.path.join(base, ".claude", "skills")
    return os.path.join(base, ".agents", "skills")


def dest_commands(scope, proj):
    return os.path.join(HOME, ".config", "opencode", "commands") if scope == "user" else os.path.join(proj, ".opencode", "commands")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--for", dest="tools", nargs="+", required=True, choices=["codex", "cursor", "opencode", "kimi", "claude"])
    ap.add_argument("--scope", choices=["user", "project"], default="user")
    ap.add_argument("--project-dir", default=os.getcwd())
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not os.path.isfile(os.path.join(SKILL, "SKILL.md")):
        sys.exit(f"skill not found at {SKILL}")
    proj = os.path.abspath(a.project_dir)
    targets = {}
    for t in a.tools:
        targets.setdefault(dest_skills(t, a.scope, proj), []).append(t)
    if any(".claude" in d for d in targets) and any(".agents" in d for d in targets) and {"cursor", "opencode"} & set(a.tools):
        print("warning: Cursor and OpenCode also read .claude/skills, so the skill would be listed twice there. "
              "In Claude Code prefer the plugin (it is not read from .claude/skills) and install only --for codex cursor opencode kimi here.")
    acts = []
    for d, ts in targets.items():
        acts.append(("skill", os.path.join(d, "releasemaster"), ts))
    if "opencode" in a.tools:
        cd = dest_commands(a.scope, proj)
        for f in sorted(os.listdir(OC_CMDS)):
            acts.append(("command", os.path.join(cd, f), ["opencode"], os.path.join(OC_CMDS, f)))
    for act in acts:
        kind, dst = act[0], act[1]
        if a.uninstall:
            print(("would remove " if a.dry_run else "removing ") + dst)
            if not a.dry_run and os.path.exists(dst):
                shutil.rmtree(dst) if os.path.isdir(dst) else os.remove(dst)
            continue
        print(("would copy " if a.dry_run else "copying ") + f"{kind} -> {dst}   (for {', '.join(act[2])})")
        if a.dry_run:
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if kind == "skill":
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(SKILL, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(act[3], dst)
    if not a.uninstall and not a.dry_run:
        print("\nRestart the agent (or start a new session). Then:")
        for t in a.tools:
            print("  - " + HOWTO[t])
        print("Needs git and Python 3.8+ on this machine for the scripts.")


if __name__ == "__main__":
    main()
