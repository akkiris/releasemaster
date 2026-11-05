#!/usr/bin/env python3
"""Collect git changes across one or more repositories for release notes.

Examples
  # Suggest ranges for every repo in the config
  python collect_changes.py --config .releasemaster/releasemaster.config.json --suggest

  # Since recorded last release (falls back to latest tag, then last 30 days)
  python collect_changes.py --config cfg.json --since-last-release --out changes.json

  # Ad hoc, no config
  python collect_changes.py --repo ../api --repo ../web --since-date 2026-10-01
  python collect_changes.py --repo . --since-tag            # latest tag -> HEAD
  python collect_changes.py --repo . --range .=v1.2.0..v1.3.0
  python collect_changes.py --config cfg.json --range api=v1.4.0..HEAD --range mobile=9c8d7e6..develop

Requires: git on PATH, Python 3.8+. No third-party packages.
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys

PR_MERGE_RES = [
    re.compile(r"^Merged PR (\d+)"),                 # Azure DevOps
    re.compile(r"^Merge pull request #(\d+)"),       # GitHub
    re.compile(r"^Merge branch '[^']+' into .*\(!(\d+)\)"),  # GitLab (some setups)
    re.compile(r"See merge request [^!]*!(\d+)"),    # GitLab body
]
CC_RE = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:\s*(?P<desc>.+)$")
REF_RE = re.compile(r"(?:(?<![\w/])#(\d+)\b|\b([A-Z][A-Z0-9]+-\d+)\b|!(\d+)\b)")
SEMVER_TAG_RE = re.compile(r"^[vV]?\d+\.\d+(\.\d+)?([-+].*)?$")
KNOWN_TYPES = {"feat", "fix", "perf", "refactor", "docs", "style", "test", "build", "ci", "chore", "revert", "security", "deps"}

SIGNAL_PATTERNS = {
    "migrations": re.compile(r"(migration|migrations/|\.sql$|schema\.(prisma|graphql)$|flyway|liquibase)", re.I),
    "dependencies": re.compile(r"(package\.json|package-lock\.json|yarn\.lock|pnpm-lock\.yaml|\.csproj$|packages\.config|Directory\.Packages\.props|pubspec\.yaml|build\.gradle(\.kts)?|Podfile|requirements.*\.txt|pyproject\.toml|go\.mod|Cargo\.toml|pom\.xml)$", re.I),
    "config": re.compile(r"(appsettings.*\.json|\.env(\..*)?$|\.env\.example|config/|settings\.(py|json)|\.ya?ml$|web\.config|launchSettings\.json)", re.I),
    "api_surface": re.compile(r"(controllers?/|Controller\.cs$|routes?/|openapi|swagger|\.proto$|graphql|endpoints?/)", re.I),
    "ci_cd": re.compile(r"(\.github/workflows|azure-pipelines|\.gitlab-ci|Jenkinsfile|Dockerfile|docker-compose|helm/|k8s/|\.circleci)", re.I),
    "tests": re.compile(r"(test|spec)s?[/._]", re.I),
    "docs": re.compile(r"(\.md$|docs/)", re.I),
}


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}: {r.stderr.strip()}")
    return r.stdout.strip()


def ref_exists(repo, ref):
    return subprocess.run(["git", "-C", repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}"],
                          capture_output=True).returncode == 0


def resolve_tag(repo, name):
    """Accept 2.3, v2.3, v2.3.0 ... and return an existing tag name."""
    candidates = [name, "v" + name, name.lstrip("vV")]
    if re.fullmatch(r"[vV]?\d+\.\d+", name):
        candidates += [name + ".0", "v" + name.lstrip("vV") + ".0"]
    for c in candidates:
        if ref_exists(repo, c):
            return c
    return None


def list_tags(repo, limit=None):
    out = git(repo, "for-each-ref", "--sort=-creatordate", "--format=%(refname:short)|%(creatordate:short)", "refs/tags", check=False)
    tags = []
    for line in out.splitlines():
        if "|" in line:
            n, d = line.split("|", 1)
            tags.append({"name": n, "date": d, "semver": bool(SEMVER_TAG_RE.match(n))})
    return tags[:limit] if limit else tags


def latest_tag(repo, to_ref="HEAD"):
    t = git(repo, "describe", "--tags", "--abbrev=0", to_ref, check=False)
    return t or None


def count(repo, rng):
    out = git(repo, "rev-list", "--count", "--no-merges", rng, check=False)
    return int(out) if out.isdigit() else None


def load_config(path):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    root = os.path.dirname(os.path.abspath(path))
    if os.path.basename(root) == ".releasemaster":
        root = os.path.dirname(root)
    if "products" in cfg and "repos" not in cfg:
        cwd = os.path.abspath(os.getcwd()).replace("\\", "/").lower()
        match = None
        for p in cfg["products"]:
            for r in p.get("roots", []):
                if cwd.startswith(os.path.abspath(r).replace("\\", "/").lower()):
                    match = p
        if not match:
            if len(cfg["products"]) == 1:
                match = cfg["products"][0]
            else:
                sys.exit("User config has several products and none matches cwd; pass --product NAME")
        cfg = match
        root = match.get("roots", [root])[0]
    return cfg, root


def repo_list(args):
    repos = []
    cfg, root = ({}, os.getcwd())
    if args.config:
        cfg, root = load_config(args.config)
        if args.product and "products" in cfg:
            cfg = next(p for p in cfg["products"] if p.get("product", {}).get("name") == args.product)
        for r in cfg.get("repos", []):
            if r.get("include", True) is False and not args.repos:
                continue
            p = r["path"]
            p = p if os.path.isabs(p) else os.path.normpath(os.path.join(root, p))
            repos.append({**r, "abspath": p})
    for p in args.repo or []:
        repos.append({"name": os.path.basename(os.path.abspath(p)) if p != "." else os.path.basename(os.getcwd()),
                      "path": p, "abspath": os.path.abspath(p), "platform": None})
    if args.repos:
        wanted = set(x.strip() for x in args.repos.split(","))
        repos = [r for r in repos if r["name"] in wanted]
    if args.platform:
        wanted = set(x.strip() for x in args.platform.split(","))
        repos = [r for r in repos if r.get("platform") in wanted]
    if not repos:
        repos.append({"name": os.path.basename(os.getcwd()), "path": ".", "abspath": os.getcwd(), "platform": None})
    return cfg, repos


def last_state(cfg, name):
    """Newer of state.lastNotes[name] and state.lastRelease[name] (by date), tagged with its source."""
    st = cfg.get("state") or {}
    cands = []
    for key in ("lastNotes", "lastRelease"):
        e = (st.get(key) or {}).get(name)
        if e:
            cands.append({**e, "source": key})
    if not cands:
        return None
    return max(cands, key=lambda e: e.get("date") or "")


def suggest(cfg, repos):
    result = []
    for r in repos:
        p = r["abspath"]
        if not os.path.isdir(os.path.join(p, ".git")) and git(p, "rev-parse", "--is-inside-work-tree", check=False) != "true":
            result.append({"repo": r["name"], "error": f"not a git repository: {p}"})
            continue
        head = git(p, "rev-parse", "--short", "HEAD", check=False)
        branch = git(p, "rev-parse", "--abbrev-ref", "HEAD", check=False)
        info = {"repo": r["name"], "platform": r.get("platform"), "path": p, "branch": branch, "head": head,
                "defaultBranch": r.get("defaultBranch"),
                "onDefaultBranch": (r.get("defaultBranch") in (None, branch)),
                "dirty": bool(git(p, "status", "--porcelain", check=False))}
        lr = last_state(cfg, r["name"])
        if lr:
            b = lr.get("ref") if lr.get("ref") and ref_exists(p, lr["ref"]) else lr.get("commit")
            info["lastRelease"] = {**lr, "boundary": b, "commitsSince": count(p, f"{b}..HEAD") if b else None}
        tags = list_tags(p, 5)
        for t in tags:
            t["commitsSince"] = count(p, f"{t['name']}..HEAD")
        info["recentTags"] = tags
        for days in (7, 30):
            out = git(p, "rev-list", "--count", "--no-merges", f"--since={days} days ago", "HEAD", check=False)
            info[f"commitsLast{days}d"] = int(out) if out.isdigit() else None
        info["totalCommits"] = count(p, "HEAD")
        # Recommendation
        if lr and info["lastRelease"].get("boundary"):
            info["recommended"] = {"mode": "since-last-release", "from": info["lastRelease"]["boundary"]}
        elif tags:
            lt = latest_tag(p) or tags[0]["name"]
            info["recommended"] = {"mode": "since-tag", "from": lt}
        else:
            info["recommended"] = {"mode": "ask", "note": "no tags or recorded state: look for a previous release note "
                                   "(detect_project.py releaseNotes) and use --timeline to map it; else ask for a date/commit"}
        result.append(info)
    return result


def resolve_range(args, cfg, r):
    p = r["abspath"]
    to = args.to or "HEAD"
    for spec in args.range or []:
        name, _, rng = spec.partition("=")
        if name in (r["name"], ".", "*") and rng:
            frm, _, t = rng.partition("..")
            if frm and not ref_exists(p, frm):
                frm = resolve_tag(p, frm) or frm
            return {"mode": "explicit", "from": frm or None, "to": t or to, "since": None}
    if args.since_commit:
        return {"mode": "since-commit", "from": args.since_commit, "to": to, "since": None}
    if args.since_tag is not None:
        tag = args.since_tag or latest_tag(p, to)
        if args.since_tag:
            tag = resolve_tag(p, args.since_tag) or args.since_tag
        if not tag:
            return {"mode": "since-tag", "from": None, "to": to, "since": None, "warning": "no tags found; using full history"}
        return {"mode": "since-tag", "from": tag, "to": to, "since": None}
    if args.since_date:
        return {"mode": "since-date", "from": None, "to": to, "since": args.since_date}
    if args.last:
        return {"mode": "last-n", "from": None, "to": to, "since": None, "n": args.last}
    if args.since_last_release:
        lr = last_state(cfg, r["name"])
        if lr:
            b = lr.get("ref") if lr.get("ref") and ref_exists(p, lr["ref"]) else lr.get("commit")
            if b:
                return {"mode": "since-last-release", "from": b, "to": to, "since": None}
            if lr.get("date"):
                return {"mode": "since-last-release-date", "from": None, "to": to, "since": lr["date"]}
        prod = ((cfg.get("state") or {}).get("lastRelease") or {}).get("product")
        lt = latest_tag(p, to)
        if lt:
            return {"mode": "fallback-latest-tag", "from": lt, "to": to, "since": None}
        if prod and prod.get("date"):
            return {"mode": "fallback-product-release-date", "from": None, "to": to, "since": prod["date"]}
        d = (dt.date.today() - dt.timedelta(days=30)).isoformat()
        return {"mode": "fallback-30-days", "from": None, "to": to, "since": d}
    lt = latest_tag(p, to)
    if lt:
        return {"mode": "default-latest-tag", "from": lt, "to": to, "since": None}
    return {"mode": "default-30-days", "from": None, "to": to,
            "since": (dt.date.today() - dt.timedelta(days=30)).isoformat()}


def pr_map(repo, frm, to, since):
    """Map commit hash -> PR number using first-parent merge commits (Azure DevOps / GitHub / GitLab)."""
    args = ["log", "--first-parent", "--merges", "--format=%H%x1f%s%x1f%b%x1e"]
    if since:
        args.append(f"--since={since}")
    args.append(f"{frm}..{to}" if frm else to)
    out = git(repo, *args, check=False)
    mapping, merges = {}, []
    for rec in out.split("\x1e"):
        rec = rec.strip()
        if not rec:
            continue
        h, subj, body = (rec.split("\x1f") + ["", ""])[:3]
        pr = None
        for rx in PR_MERGE_RES:
            m = rx.search(subj) or rx.search(body)
            if m:
                pr = m.group(1)
                break
        merges.append({"hash": h[:7], "pr": pr, "subject": subj})
        if pr:
            for c in git(repo, "rev-list", "--no-merges", f"{h}^1..{h}", check=False).split():
                mapping.setdefault(c, pr)
    return mapping, merges


def classify(subject, body):
    m = CC_RE.match(subject)
    breaking = "BREAKING CHANGE" in body or "BREAKING-CHANGE" in body
    if m:
        t = m.group("type").lower()
        return {"type": t if t in KNOWN_TYPES else "other", "rawType": t, "scope": m.group("scope"),
                "breaking": breaking or bool(m.group("bang")), "description": m.group("desc"), "conventional": True}
    low = subject.lower()
    guess = "other"
    if re.match(r"^(merge|merged)\b", low):
        guess = "merge"
    elif re.match(r"^revert\b", low):
        guess = "revert"
    elif re.search(r"\b(fix|fixed|bug|hotfix|düzelt|hata)\b", low):
        guess = "fix?"
    elif re.search(r"\b(add|added|new|implement|ekle|eklendi|yeni)\b", low):
        guess = "feat?"
    return {"type": "other", "guess": guess, "scope": None, "breaking": breaking, "description": subject, "conventional": False}


def collect(args, cfg, r):
    p = r["abspath"]
    rng = resolve_range(args, cfg, r)
    log_args = ["log", "--date=short", "--numstat", "--format=%x1e%H%x1f%h%x1f%ad%x1f%an%x1f%ae%x1f%s%x1f%b%x1f%P"]
    if not args.merges:
        log_args.append("--no-merges")
    if rng.get("since"):
        log_args.append(f"--since={rng['since']}")
    if rng.get("n"):
        log_args.append(f"-n{rng['n']}")
    target = f"{rng['from']}..{rng['to']}" if rng.get("from") else rng["to"]
    log_args.append(target)
    if args.path_filter:
        log_args += ["--", *args.path_filter]
    out = git(p, *log_args)
    commits = []
    dir_stats = {}
    signals = {k: set() for k in SIGNAL_PATTERNS}
    ins_total = del_total = 0
    for rec in out.split("\x1e"):
        if not rec.strip():
            continue
        parts = rec.split("\x1f")
        if len(parts) < 8:
            continue
        full, short, date, author, email, subject, body = parts[:7]
        rest = parts[7].split("\n", 1)
        parents = rest[0].split()
        stat_block = rest[1] if len(rest) > 1 else ""
        files = []
        for line in stat_block.strip().splitlines():
            cols = line.split("\t")
            if len(cols) != 3:
                continue
            a, d, f = cols
            a = int(a) if a.isdigit() else 0
            d = int(d) if d.isdigit() else 0
            if "=>" in f:
                f = re.sub(r"\{[^}]*=> ([^}]*)\}", r"\1", f).split(" => ")[-1]
            files.append(f)
            ins_total += a
            del_total += d
            top = f.split("/")[0] if "/" in f else "(root)"
            s = dir_stats.setdefault(top, {"files": set(), "insertions": 0, "deletions": 0})
            s["files"].add(f)
            s["insertions"] += a
            s["deletions"] += d
            for k, pat in SIGNAL_PATTERNS.items():
                if pat.search(f):
                    signals[k].add(f)
        body = body.strip()
        c = classify(subject.strip(), body)
        refs = sorted({x for g in REF_RE.findall(subject + "\n" + body) for x in g if x})
        commits.append({"hash": short, "fullHash": full, "date": date, "author": author, "subject": subject.strip(),
                        "body": body[:2000], "merge": len(parents) > 1, "refs": refs,
                        "filesChanged": len(files), "files": files[:50], **c})
    prs, merges = pr_map(p, rng.get("from"), rng["to"], rng.get("since"))
    for c in commits:
        c["pr"] = prs.get(c["fullHash"])
        if c["pr"] and c["pr"] not in c["refs"]:
            c["refs"].append("PR " + c["pr"])
    # "no PR" only means something in a repo that merges through PRs; a PR-less history has no such signal.
    # An all-direct range has no merges at all, so look at the repo's wider first-parent history too.
    uses_prs = bool(merges) or bool(git(p, "log", "--first-parent", "--merges", "-n1", "--format=%H", rng["to"], check=False).strip())
    direct = [c["hash"] for c in commits if not c["pr"]] if uses_prs else []
    by_type = {}
    for c in commits:
        key = c["type"] if c["type"] != "other" else f"other:{c.get('guess', 'other')}"
        by_type[key] = by_type.get(key, 0) + 1
    conv = sum(1 for c in commits if c["conventional"])
    return {
        "repo": r["name"], "platform": r.get("platform"), "path": p,
        "branch": git(p, "rev-parse", "--abbrev-ref", "HEAD", check=False),
        "range": {**rng, "toCommit": git(p, "rev-parse", "--short", rng["to"], check=False),
                  "fromCommit": git(p, "rev-parse", "--short", rng["from"], check=False) if rng.get("from") else None},
        "commitCount": len(commits),
        "conventionalRatio": round(conv / len(commits), 2) if commits else None,
        "byType": by_type,
        "breaking": [c["hash"] for c in commits if c["breaking"]],
        "authors": sorted({c["author"] for c in commits}),
        "stats": {"insertions": ins_total, "deletions": del_total,
                  "byTopDir": {k: {"files": len(v["files"]), "insertions": v["insertions"], "deletions": v["deletions"]}
                               for k, v in sorted(dir_stats.items(), key=lambda kv: -(kv[1]["insertions"] + kv[1]["deletions"]))}},
        "signals": {k: sorted(v)[:40] for k, v in signals.items() if v},
        "merges": merges,
        "directCommits": direct,
        "commits": commits,
    }


def to_markdown(data):
    lines = [f"# Changes ({data['generatedAt']})", ""]
    lines.append("| Repo | Platform | From | To | Mode | Commits |")
    lines.append("|---|---|---|---|---|---|")
    for r in data["repos"]:
        if "error" in r:
            lines.append(f"| {r['repo']} | | | | ERROR: {r['error']} | |")
            continue
        g = r["range"]
        frm = g.get("from") or (f"since {g['since']}" if g.get("since") else "(start)")
        lines.append(f"| {r['repo']} | {r.get('platform') or ''} | {frm} | {g['to']} ({g['toCommit']}) | {g['mode']} | {r['commitCount']} |")
    for r in data["repos"]:
        if "error" in r:
            continue
        lines += ["", f"## {r['repo']}", "", f"byType: {r['byType']}  ", f"breaking: {r['breaking'] or 'none'}  ",
                  f"merges/PRs: {', '.join(m['pr'] or m['hash'] for m in r['merges']) or 'none'}  ",
                  f"direct commits (no PR): {', '.join(r['directCommits']) or 'none'}", "", "signals:"]
        for k, v in r["signals"].items():
            if k == "tests":
                lines.append(f"- {k}: {len(v)} files")
            else:
                lines.append(f"- {k}: " + ", ".join(f"`{x}`" for x in v[:10]) + (" …" if len(v) > 10 else ""))
        lines.append("")
        for c in r["commits"]:
            flag = " ⚠️BREAKING" if c["breaking"] else ""
            other = [x for x in c["refs"] if not x.startswith("PR ")]
            refs = f" [{', '.join(other)}]" if other else ""
            pr = f" (PR {c['pr']})" if c.get("pr") else ""
            lines.append(f"- `{c['hash']}` {c['date']} **{c['type']}**{flag} {c['subject']}{pr}{refs}")
    return "\n".join(lines) + "\n"


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", help="path to releasemaster.config.json")
    ap.add_argument("--product", help="product name (user-scope multi-product config)")
    ap.add_argument("--repo", action="append", help="repo path (repeatable; used with or without --config)")
    ap.add_argument("--repos", help="comma-separated repo names to include")
    ap.add_argument("--platform", help="comma-separated platforms to include")
    ap.add_argument("--suggest", action="store_true", help="print range suggestions and exit")
    ap.add_argument("--timeline", metavar="SINCE", help="list first-parent merges/commits (time, PR, subject) since DATE "
                    "on each repo's target branch; use it to map a previous release note to its last covered merge")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--since-last-release", action="store_true")
    g.add_argument("--since-tag", nargs="?", const="", default=None, metavar="TAG", help="latest tag when TAG omitted")
    g.add_argument("--since-date", metavar="DATE", help="'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM' (local time, inclusive). "
                   "Day granularity is coarse: prefer --since-commit when a previous note ends mid-day")
    g.add_argument("--since-commit", metavar="SHA")
    g.add_argument("--last", type=int, metavar="N", help="last N commits")
    ap.add_argument("--range", action="append", metavar="NAME=FROM..TO", help="per-repo explicit range; NAME may be '*'")
    ap.add_argument("--to", help="end ref (default HEAD)")
    ap.add_argument("--merges", action="store_true", help="include merge commits")
    ap.add_argument("--path-filter", nargs="+", help="only commits touching these paths")
    ap.add_argument("--format", choices=["json", "md"], default="json")
    ap.add_argument("--out", help="write to file instead of stdout")
    return ap


def main():
    args = build_parser().parse_args()

    cfg, repos = repo_list(args)
    if args.timeline:
        data = {"timeline": []}
        for r in repos:
            out = git(r["abspath"], "log", "--first-parent", f"--since={args.timeline}", "--date=format:%Y-%m-%d %H:%M",
                      "--format=%h%x1f%ad%x1f%s", args.to or "HEAD", check=False)
            rows = []
            for line in out.splitlines():
                h, d, subj = (line.split("\x1f") + ["", ""])[:3]
                pr = next((m.group(1) for rx in PR_MERGE_RES for m in [rx.search(subj)] if m), None)
                rows.append({"hash": h, "time": d, "pr": pr, "subject": subj})
            data["timeline"].append({"repo": r["name"], "entries": rows})
        if args.format == "md":
            lines = []
            for t in data["timeline"]:
                lines += [f"## {t['repo']}", "", "| Time | Commit | PR | Subject |", "|---|---|---|---|"]
                lines += [f"| {e['time']} | `{e['hash']}` | {e['pr'] or '—'} | {e['subject']} |" for e in t["entries"]]
                lines.append("")
            print("\n".join(lines))
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    if args.suggest:
        data = {"generatedAt": dt.datetime.now().isoformat(timespec="seconds"), "suggestions": suggest(cfg, repos)}
        text = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        out = []
        for r in repos:
            try:
                out.append(collect(args, cfg, r))
            except Exception as e:  # keep going for other repos
                out.append({"repo": r["name"], "error": str(e)})
        data = {"generatedAt": dt.datetime.now().isoformat(timespec="seconds"),
                "product": (cfg.get("product") or {}).get("name"), "repos": out}
        text = to_markdown(data) if args.format == "md" else json.dumps(data, indent=2, ensure_ascii=False)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"wrote {args.out}")
    else:
        sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
        print(text)


if __name__ == "__main__":
    main()
