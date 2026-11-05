#!/usr/bin/env python3
"""Inspect repositories: stack, platform guess, docs, versioning, commit conventions.

Examples
  python detect_project.py .                       # one repo
  python detect_project.py ../api ../web           # several
  python detect_project.py --scan D:/dev/product --depth 2   # find git repos under a folder

Output: JSON to stdout. Requires git on PATH, Python 3.8+.
"""
import argparse
import json
import os
import re
import subprocess
import sys

SKIP_DIRS = {".git", "node_modules", "bin", "obj", "dist", "build", ".next", ".venv", "venv", "Pods", ".gradle",
             ".idea", ".vs", "coverage", "target", ".dart_tool", "packages"}

MARKERS = [
    # (glob-ish suffix or name, stack label, platform)
    (".sln", ".NET solution", "backend"),
    (".csproj", ".NET", "backend"),
    ("pubspec.yaml", "Flutter/Dart", "mobile"),
    ("app.json+react-native", "React Native", "mobile"),
    ("AndroidManifest.xml", "Android", "mobile"),
    (".xcodeproj", "iOS", "mobile"),
    ("vite.config.ts", "Vite", "frontend"),
    ("vite.config.js", "Vite", "frontend"),
    ("next.config.js", "Next.js", "frontend"),
    ("next.config.mjs", "Next.js", "frontend"),
    ("next.config.ts", "Next.js", "frontend"),
    ("svelte.config.js", "SvelteKit", "frontend"),
    ("angular.json", "Angular", "frontend"),
    ("nuxt.config.ts", "Nuxt", "frontend"),
    ("package.json", "Node.js", None),
    ("pyproject.toml", "Python", None),
    ("requirements.txt", "Python", None),
    ("go.mod", "Go", "backend"),
    ("Cargo.toml", "Rust", None),
    ("pom.xml", "Java/Maven", "backend"),
    ("build.gradle", "Gradle", None),
    ("Dockerfile", "Docker", None),
    ("docker-compose.yml", "Docker Compose", "infra"),
    ("docker-compose.yaml", "Docker Compose", "infra"),
    ("main.tf", "Terraform", "infra"),
    ("Chart.yaml", "Helm", "infra"),
]

DOC_HINTS = ["README.md", "README", "readme.md", "CHANGELOG.md", "HISTORY.md", "RELEASE_NOTES.md", "CONTRIBUTING.md",
             "docs", "doc", "documentation", "wiki", "adr", "mkdocs.yml", "docusaurus.config.js", ".vitepress",
             "openapi.yaml", "openapi.json", "swagger.json"]

KEY_FILES = re.compile(r"(Program\.cs|Startup\.cs|appsettings.*\.json|launchSettings\.json|\.env\.example|\.env\.sample|"
                       r"package\.json|vite\.config\.\w+|main\.(ts|tsx|js|dart|go|py)|App\.(tsx|jsx|vue)|"
                       r"Dockerfile|docker-compose\.ya?ml|.*\.csproj|pubspec\.yaml|Makefile|azure-pipelines\.ya?ml|"
                       r"openapi\.(ya?ml|json)|swagger\.json)$", re.I)

CC_RE = re.compile(r"^[a-z]+(\([^)]*\))?!?:\s")


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip() if r.returncode == 0 else ""


def walk(root, max_depth=4):
    for dirpath, dirnames, filenames in os.walk(root):
        depth = os.path.relpath(dirpath, root).count(os.sep)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".") or d in (".github",)]
        if depth >= max_depth:
            dirnames[:] = []
        yield dirpath, dirnames, filenames


def inspect(repo):
    repo = os.path.abspath(repo)
    info = {"path": repo, "name": os.path.basename(repo), "isGit": bool(git(repo, "rev-parse", "--git-dir"))}
    stacks, platforms, key_files, doc_found, md_count = set(), [], [], [], 0
    pkg_deps = {}
    for dirpath, dirnames, filenames in walk(repo):
        rel = os.path.relpath(dirpath, repo)
        for d in dirnames:
            if d.lower() in {h.lower() for h in DOC_HINTS} and rel.count(os.sep) < 2:
                doc_found.append(os.path.join(rel, d).replace("\\", "/").lstrip("./"))
            if d.endswith(".xcodeproj"):
                stacks.add("iOS"); platforms.append("mobile")
        for f in filenames:
            relf = os.path.join(rel, f).replace("\\", "/")
            relf = relf[2:] if relf.startswith("./") else relf
            if f.lower().endswith(".md"):
                md_count += 1
            if f in DOC_HINTS and rel.count(os.sep) < 2:
                doc_found.append(relf)
            for marker, stack, plat in MARKERS:
                if (marker.startswith(".") and f.endswith(marker)) or f == marker:
                    stacks.add(stack)
                    if plat:
                        platforms.append(plat)
            if KEY_FILES.search(f) and len(key_files) < 60:
                key_files.append(relf)
            if f == "package.json" and rel.count(os.sep) < 2:
                try:
                    with open(os.path.join(dirpath, f), encoding="utf-8") as fh:
                        pj = json.load(fh)
                    deps = {**pj.get("dependencies", {}), **pj.get("devDependencies", {})}
                    pkg_deps[relf] = {"name": pj.get("name"), "version": pj.get("version"),
                                      "scripts": pj.get("scripts", {}),
                                      "notable": sorted(k for k in deps if k in {"react", "react-native", "expo", "vue", "@angular/core",
                                                                                  "next", "vite", "typescript", "express", "nestjs",
                                                                                  "@nestjs/core", "electron", "tailwindcss", "jest", "vitest"})}
                    if "react-native" in deps or "expo" in deps:
                        stacks.add("React Native"); platforms.append("mobile")
                    elif any(k in deps for k in ("react", "vue", "@angular/core", "svelte")):
                        platforms.append("frontend")
                    elif any(k in deps for k in ("express", "@nestjs/core", "fastify", "koa")):
                        platforms.append("backend")
                except Exception:
                    pass
    # infra markers (Dockerfile/compose) exist in most app repos; only use them when nothing else matched
    app_plats = [p for p in platforms if p != "infra"]
    pool = app_plats or platforms
    plat = max(set(pool), key=pool.count) if pool else "unknown"
    info.update({"stack": sorted(stacks), "platformGuess": plat, "keyFiles": key_files,
                 "docs": {"found": sorted(set(doc_found)), "markdownFiles": md_count,
                          "hasReadme": any(d.lower().startswith("readme") for d in doc_found),
                          "hasChangelog": any("changelog" in d.lower() for d in doc_found),
                          "hasDocsDir": any(d.split("/")[-1].lower() in ("docs", "doc", "documentation") for d in doc_found)},
                 "packageJson": pkg_deps})
    if info["isGit"]:
        branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        remote_head = git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
        tags = git(repo, "for-each-ref", "--sort=-creatordate", "--count=10", "--format=%(refname:short)|%(creatordate:short)", "refs/tags")
        tag_list = [dict(zip(("name", "date"), t.split("|", 1))) for t in tags.splitlines() if "|" in t]
        semver = [t for t in tag_list if re.match(r"^[vV]?\d+\.\d+(\.\d+)?", t["name"])]
        subjects = git(repo, "log", "-n", "200", "--no-merges", "--format=%s").splitlines()
        cc = sum(1 for s in subjects if CC_RE.match(s))
        info["git"] = {
            "branch": branch,
            "defaultBranch": remote_head.split("/", 1)[1] if "/" in remote_head else None,
            "remote": git(repo, "remote", "get-url", "origin") or None,
            "totalCommits": int(git(repo, "rev-list", "--count", "HEAD") or 0) if git(repo, "rev-parse", "HEAD") else 0,
            "firstCommitDate": (git(repo, "log", "--reverse", "--format=%ad", "--date=short").splitlines() or [None])[0],
            "lastCommitDate": git(repo, "log", "-1", "--format=%ad", "--date=short") or None,
            "tags": tag_list,
            "versioning": "semver" if semver else ("calver" if any(re.match(r"^\d{4}\.", t["name"]) for t in tag_list) else "none"),
            "tagPrefixV": bool(semver) and semver[0]["name"].lower().startswith("v"),
            "conventionalCommitRatio": round(cc / len(subjects), 2) if subjects else None,
            "contributors": len(set(git(repo, "log", "--format=%ae").splitlines())),
        }
    return info


NOTE_RE = re.compile(r"^(CHANGELOG|HISTORY|RELEASE[-_ ]?NOTES?|S[UÜ]R[UÜ]M[-_ ]?NOT(U|LARI)?|RELEASES?)([-_ .].*)?\.md$", re.I)


def find_release_notes(root, depth=2):
    """Existing release notes / changelogs near the workspace root (not inside node_modules etc.)."""
    hits = []
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in walk(root, depth):
        rel = os.path.relpath(dirpath, root)
        if os.path.basename(dirpath).lower() in ("releases", "release-notes", "surum-notlari"):
            hits += [os.path.join(rel, f).replace("\\", "/") for f in filenames if f.endswith(".md")]
        hits += [os.path.join(rel, f).replace("\\", "/") for f in filenames if NOTE_RE.match(f)]
    out = []
    for h in sorted(set(hits)):
        p = os.path.join(root, h)
        out.append({"path": h[2:] if h.startswith("./") else h, "size": os.path.getsize(p),
                    "modified": __import__("datetime").datetime.fromtimestamp(os.path.getmtime(p)).isoformat(timespec="minutes")})
    return out


def read_code_workspace(root):
    """Folders declared in *.code-workspace files (VS Code multi-root), with existence check."""
    res = []
    for f in os.listdir(root):
        if f.endswith(".code-workspace"):
            try:
                txt = open(os.path.join(root, f), encoding="utf-8").read()
                txt = re.sub(r"//.*", "", txt)
                txt = re.sub(r",\s*([}\]])", r"\1", txt)
                for fo in json.loads(txt).get("folders", []):
                    p = os.path.normpath(os.path.join(root, fo.get("path", "")))
                    res.append({"file": f, "path": fo.get("path"), "exists": os.path.isdir(p),
                                "isGit": os.path.exists(os.path.join(p, ".git"))})
            except Exception as e:
                res.append({"file": f, "error": str(e)})
    return res


def scan(root, depth):
    found = []
    root = os.path.abspath(root)
    for dirpath, dirnames, _ in os.walk(root):
        d = os.path.relpath(dirpath, root).count(os.sep) + (0 if dirpath == root else 1)
        if os.path.isdir(os.path.join(dirpath, ".git")) or os.path.isfile(os.path.join(dirpath, ".git")):
            found.append(dirpath)
            dirnames[:] = []
            continue
        dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS and not x.startswith(".")]
        if d >= depth:
            dirnames[:] = []
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", default=["."])
    ap.add_argument("--scan", help="find git repos under this folder and inspect each")
    ap.add_argument("--depth", type=int, default=2)
    args = ap.parse_args()
    paths = scan(args.scan, args.depth) if args.scan else args.paths
    result = {"repos": [inspect(p) for p in paths]}
    root = args.scan or (os.path.dirname(os.path.abspath(paths[0])) if len(paths) > 1 else os.path.abspath(paths[0]))
    if args.scan:
        result["scannedRoot"] = os.path.abspath(args.scan)
    result["releaseNotes"] = find_release_notes(root)
    result["codeWorkspaceFolders"] = read_code_workspace(root)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
