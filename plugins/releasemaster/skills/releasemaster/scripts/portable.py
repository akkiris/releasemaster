#!/usr/bin/env python3
"""Move a workspace's git history into an environment that cannot see your disk (claude.ai, a fresh sandbox).

ReleaseMaster reads git history. Claude Code and the desktop app with a linked folder see your repos directly -
nothing to do. In claude.ai the skill runs in a sandbox with no access to your machine: pack what it needs into
one zip on your machine, attach it to the chat, and the skill unpacks it.

  # on YOUR machine (needs git + Python 3.8+), from the workspace root:
  python portable.py export                                   # uses .releasemaster/releasemaster.config.json
  python portable.py export --repo ../api --repo ../web       # no config yet (init will run in the sandbox)
  -> releasemaster-upload.zip: one git bundle per repo (all branches/tags), the config, existing release
     notes / CHANGELOG / docs. Uncommitted changes are NOT included - only commits.

  # in the sandbox (the skill does this):
  python portable.py import releasemaster-upload.zip --dest ./rm-workspace
  -> repos restored under ./rm-workspace/<name>, config rewritten to those paths, files restored at their
     relative locations. Work as usual with --config ./rm-workspace/.releasemaster/releasemaster.config.json.
     When finished: python portable.py finish --dest ./rm-workspace --out <outputs-dir> writes the updated config
     (state.lastNotes ...) with the user's own paths; hand it and the new files back to the user.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect_changes as cc  # noqa: E402
import detect_project as dp  # noqa: E402

MAX_DOC_BYTES = 5 * 1024 * 1024


def run(cwd, *a):
    r = subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError(f"git {' '.join(a)} failed in {cwd}: {r.stderr.strip()}")
    return r.stdout.strip()


def export(args):
    cfg_path = args.config or (".releasemaster/releasemaster.config.json" if os.path.exists(".releasemaster/releasemaster.config.json") else None)
    cfg, root = ({}, os.getcwd())
    repos = []
    if cfg_path:
        cfg, root = cc.load_config(cfg_path)
        ns = argparse.Namespace(config=cfg_path, product=None, repo=None, repos=None, platform=None)
        _, repos = cc.repo_list(ns)
        if args.repo:  # only the named repos, keeping the config's name/platform when the path matches
            known = {os.path.abspath(r["abspath"]): r for r in repos}
            repos = [known.get(os.path.abspath(p), {"name": os.path.basename(os.path.abspath(p)), "abspath": os.path.abspath(p), "platform": None}) for p in args.repo]
    else:
        for p in args.repo or []:
            repos.append({"name": os.path.basename(os.path.abspath(p)), "abspath": os.path.abspath(p), "platform": None})
    if not repos:
        sys.exit("no repos: run from a workspace with .releasemaster/releasemaster.config.json or pass --repo PATH")
    out = os.path.abspath(args.out)
    files = {}  # zip path -> disk path
    for g in args.include or []:
        import glob
        for f in glob.glob(os.path.join(root, g), recursive=True):
            if os.path.isfile(f):
                files[os.path.relpath(f, root).replace("\\", "/")] = f
    docs = (cfg.get("docs") or {})
    if docs.get("exists") and docs.get("path"):
        d = os.path.join(root, docs["path"])
        if os.path.isdir(d):
            for dp_, _, fs in os.walk(d):
                for f in fs:
                    if f.lower().endswith((".md", ".mdx", ".txt")):
                        files[os.path.relpath(os.path.join(dp_, f), root).replace("\\", "/")] = os.path.join(dp_, f)
    for h in dp.find_release_notes(root):
        files[h["path"]] = os.path.join(root, h["path"])
    for extra in ("CHANGELOG.md", "README.md"):
        if os.path.isfile(os.path.join(root, extra)):
            files[extra] = os.path.join(root, extra)
    total = sum(os.path.getsize(p) for p in files.values())
    if total > MAX_DOC_BYTES:
        print(f"warning: {total // 1024} KB of docs/notes; consider --include only what the task needs", file=sys.stderr)
    manifest = {"version": 1, "repos": [], "files": sorted(files), "configRoot": os.path.basename(root)}
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for r in repos:
            name = r["name"]
            b = os.path.join(tmp, name + ".bundle")
            try:
                run(r["abspath"], "bundle", "create", b, "--all")
                branch = run(r["abspath"], "rev-parse", "--abbrev-ref", "HEAD")
                head = run(r["abspath"], "rev-parse", "--short", "HEAD")
                dirty = bool(run(r["abspath"], "status", "--porcelain"))
            except RuntimeError as e:
                sys.exit(str(e))
            z.write(b, f"repos/{name}.bundle")
            manifest["repos"].append({"name": name, "branch": branch, "head": head, "platform": r.get("platform"),
                                      "uncommittedChanges": dirty, "sizeKB": os.path.getsize(b) // 1024})
        if cfg_path:
            z.write(cfg_path, "config/releasemaster.config.json")
        for arc, p in files.items():
            z.write(p, "files/" + arc)
        z.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"wrote {out} ({os.path.getsize(out) // 1024} KB)")
    if os.path.getsize(out) > 25 * 1024 * 1024:
        print("warning: over 25 MB - chat upload limits may refuse it; export fewer repos or use --repo for the ones you need", file=sys.stderr)
    for r in manifest["repos"]:
        print(f"  {r['name']}: branch {r['branch']} @ {r['head']}, bundle {r['sizeKB']} KB" + ("  [uncommitted changes NOT included]" if r["uncommittedChanges"] else ""))
    print(f"  {len(files)} document file(s), config {'included' if cfg_path else 'not found (init will run)'}")
    print("Attach this zip to the chat and ask for the release notes / summary.")


def import_(args):
    dest = os.path.abspath(args.dest)
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(args.zip) as z:
        names = z.namelist()
        if any(n.startswith("/") or ".." in n.split("/") for n in names):
            sys.exit("unsafe path in zip")
        man = json.loads(z.read("manifest.json"))
        with tempfile.TemporaryDirectory() as tmp:
            z.extractall(tmp)
            for r in man["repos"]:
                rd = os.path.join(dest, r["name"])
                if os.path.isdir(os.path.join(rd, ".git")):
                    shutil.rmtree(rd)
                os.makedirs(rd, exist_ok=True)
                b = os.path.join(tmp, "repos", r["name"] + ".bundle")
                run(rd, "init", "-q")
                run(rd, "fetch", "-q", b, "+refs/heads/*:refs/heads/*", "+refs/tags/*:refs/tags/*", "+refs/remotes/*:refs/remotes/*")
                run(rd, "symbolic-ref", "HEAD", f"refs/heads/{r['branch']}") if r["branch"] != "HEAD" else None
                run(rd, "checkout", "-q", "-f", r["branch"] if r["branch"] != "HEAD" else run(rd, "rev-parse", "HEAD"))
            for arc in man["files"]:
                src = os.path.join(tmp, "files", arc)
                if os.path.isfile(src):
                    tgt = os.path.join(dest, arc)
                    os.makedirs(os.path.dirname(tgt), exist_ok=True)
                    shutil.copy2(src, tgt)
            cfg_dir = os.path.join(dest, ".releasemaster")
            cfg_file = os.path.join(cfg_dir, "releasemaster.config.json")
            if os.path.exists(os.path.join(tmp, "config", "releasemaster.config.json")):
                cfg = json.load(open(os.path.join(tmp, "config", "releasemaster.config.json"), encoding="utf-8"))
                if "repos" in cfg:
                    for r in cfg["repos"]:
                        r["originalPath"] = r.get("path")
                        r["path"] = r["name"]
                os.makedirs(cfg_dir, exist_ok=True)
                json.dump(cfg, open(cfg_file, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"restored into {dest}")
    for r in man["repos"]:
        print(f"  {r['name']}: {r['branch']} @ {r['head']}" + ("  (uncommitted changes on the user's disk are not part of this)" if r.get("uncommittedChanges") else ""))
    print(f"  {len(man['files'])} file(s) restored" + (f"; config: {cfg_file}" if os.path.exists(cfg_file) else "; no config - run init"))


def finish(args):
    """Write the config back in the user's own paths (undo the sandbox path rewrite) so it keeps working on their machine."""
    cfg_file = os.path.join(args.dest, ".releasemaster", "releasemaster.config.json")
    cfg = json.load(open(cfg_file, encoding="utf-8"))
    for r in cfg.get("repos", []):
        if "originalPath" in r:
            r["path"] = r.pop("originalPath")
    out = os.path.join(args.out, ".releasemaster", "releasemaster.config.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(cfg, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"wrote {out} - hand this file back to the user (state.lastNotes / lastRelease live in it)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    e = sp.add_parser("export", help="pack repos + config + docs into one zip (run on your machine)")
    e.add_argument("--config")
    e.add_argument("--repo", action="append", help="repo path (repeatable); adds to / replaces the config's repos when there is no config")
    e.add_argument("--include", action="append", help="extra files to pack, glob relative to the workspace root (repeatable)")
    e.add_argument("--out", default="releasemaster-upload.zip")
    i = sp.add_parser("import", help="unpack an export (run in the sandbox)")
    i.add_argument("zip")
    i.add_argument("--dest", default="rm-workspace")
    f = sp.add_parser("finish", help="write the updated config back with the user's original paths (run in the sandbox when done)")
    f.add_argument("--dest", default="rm-workspace")
    f.add_argument("--out", default="outputs")
    args = ap.parse_args()
    {"export": export, "import": import_, "finish": finish}[args.cmd](args)


if __name__ == "__main__":
    main()
