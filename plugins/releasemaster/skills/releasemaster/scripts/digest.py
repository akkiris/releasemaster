#!/usr/bin/env python3
"""Compact, review-ready digest of changes across repos: the cheap path for summaries and release notes.

collect_changes.py returns raw commits. This script goes one step further so the reader does not need
dozens of `git show` calls:
  * groups commits by PR (direct commits stay on their own)
  * links backend/frontend pieces of the same feature (candidates - confirm them)
  * extracts only the risky diff fragments: migrations, config keys, dependency lines, routes, CI
  * prints a release checklist (migrations, config, routes, dependencies, direct commits, untested groups)
  * lists what is still worth reading by hand ("inspect")

Takes every collect_changes.py option (--config, --repo, --since-last-release, --range name=a..b, ...).

Examples
  python digest.py --config .releasemaster/releasemaster.config.json --since-last-release
  python digest.py --repo ../api --repo ../web --since-date 2026-11-01 --depth quick
  python digest.py --changes changes.json --format json --out digest.json

--format skeleton  draft release note: entries per PR/link with TODO prose slots, plus the technical tables
                    already filled from the diffs (migrations, config keys, routes, dependencies, direct commits).
                    --like NOTE.md lists that note's headings so the draft can follow the team's format.
--depth quick     groups, links and the checklist (incl. config keys and routes); no diff fragments printed
--depth standard  + risky diff fragments (migrations/config/dependencies/CI) and route extraction  [default]
--depth deep      + API-surface diffs shown, larger fragment limits
"""
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect_changes as cc  # noqa: E402

STOP = set("""a an the and or of for to in on with from by add adds added adding enhance enhances enhanced implement implemented
feature features update updates updated support new use using improve improved fix fixes fixed feat refactor chore docs test tests
page pages component components handle handling make ensure retrieve into when more also than that this""".split())
CODE_EXT = (".cs", ".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".dart", ".kt", ".java", ".swift", ".vue", ".svelte", ".rb", ".php")
TEST_RE = re.compile(r"(^|/)(tests?|__tests__|specs?)/|\.(test|spec)\.[jt]sx?$|Tests?\.cs$|_test\.(go|py)$", re.I)
LOCK_RE = re.compile(r"(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|\.lock$)")
ROUTE_RES = [
    (re.compile(r"Map(Get|Post|Put|Delete|Patch)\(\s*\"([^\"]*)\""), lambda m: (m.group(1).upper(), m.group(2))),
    (re.compile(r"\[Http(Get|Post|Put|Delete|Patch)(?:\(\"([^\"]*)\"\))?\]"), lambda m: (m.group(1).upper(), m.group(2) or "")),
    (re.compile(r"\b(?:app|router)\.(get|post|put|delete|patch)\(\s*['\"]([^'\"]+)"), lambda m: (m.group(1).upper(), m.group(2))),
    (re.compile(r"@(Get|Post|Put|Delete|Patch)Mapping(?:\(\"([^\"]*)\"\))?"), lambda m: (m.group(1).upper(), m.group(2) or "")),
    (re.compile(r"MapGroup\(\s*\"([^\"]*)\""), lambda m: ("GROUP", m.group(1))),
]
KEY_RE = re.compile(r"^[+]\s*\"?([A-Za-z_][\w:.\-]*)\"?\s*[:=]")
GENERIC_SUBJECT = re.compile(r"^(update|updates|fix|fixes|wip|changes?|misc|stuff|minor|tweak|cleanup|refactor)\b.{0,15}$", re.I)


def stem(t):
    for suf in ("ing", "ed", "es", "s"):
        if t.endswith(suf) and len(t) - len(suf) >= 4:
            return t[: -len(suf)]
    return t


def tokens(text):
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return {stem(t) for t in re.findall(r"[a-zA-Z]{4,}", text.lower()) if t not in STOP}


def file_tokens(files):
    out = set()
    for f in files:
        base = os.path.splitext(os.path.basename(f))[0]
        out |= tokens(base)
    return out


def is_test(f):
    return bool(TEST_RE.search(f))


def top_dirs(files, n=3):
    c = {}
    for f in files:
        parts = f.split("/")
        k = "/".join(parts[:3]) if len(parts) > 4 else ("/".join(parts[:-1]) or "(root)")
        c[k] = c.get(k, 0) + 1
    return sorted(c.items(), key=lambda kv: -kv[1])[:n]


def load(args):
    if args.changes:
        with open(args.changes, encoding="utf-8") as f:
            return json.load(f)
    cfg, repos = cc.repo_list(args)
    out = []
    for r in repos:
        try:
            out.append(cc.collect(args, cfg, r))
        except Exception as e:
            out.append({"repo": r["name"], "error": str(e)})
    return {"generatedAt": dt.datetime.now().isoformat(timespec="seconds"),
            "product": (cfg.get("product") or {}).get("name"), "repos": out}


def build_groups(repo):
    merges = {m["pr"]: m for m in repo.get("merges", []) if m.get("pr")}
    groups = {}
    for c in repo["commits"]:
        key = c.get("pr") or "direct:" + c["hash"]
        g = groups.setdefault(key, {"repo": repo["repo"], "platform": repo.get("platform"), "pr": c.get("pr"),
                                    "commits": [], "files": []})
        g["commits"].append(c)
        for f in c["files"]:
            if f not in g["files"]:
                g["files"].append(f)
    out = []
    for g in groups.values():
        cm = g["commits"]
        title = None
        if g["pr"] and g["pr"] in merges:
            title = re.sub(r"^Merged PR \d+:\s*", "", merges[g["pr"]]["subject"]).strip()
            if title.lower().startswith("merge"):
                title = None
        title = title or cm[0]["subject"]
        m = cc.CC_RE.match(title)
        if m:
            dominant = m.group("type").lower()
        else:
            types = [c["type"] for c in cm]
            dominant = next((t for t in ("feat", "fix", "perf", "refactor", "docs", "build", "ci", "chore", "test") if t in types), "other")
        files = g["files"]
        src = [f for f in files if f.endswith(CODE_EXT) and not is_test(f)]
        tests = [f for f in files if is_test(f)]
        g.update({
            "title": title, "type": dominant,
            "breaking": any(c["breaking"] for c in cm) or cc.classify(title, "")["breaking"],
            "date": max(c["date"] for c in cm), "hashes": [c["hash"] for c in cm],
            "srcFiles": len(src), "testFiles": len(tests), "untested": bool(src) and not tests,
            "topDirs": top_dirs(files), "tokTitle": tokens(re.sub(r"^\w+(\([^)]*\))?!?:", "", title)),
            "tokFiles": file_tokens(src), "risky": {}, "routes": [], "configKeys": [], "inspect": [],
        })
        for c in cm:
            if (not c.get("conventional") and (c.get("guess") in (None, "other"))) or GENERIC_SUBJECT.match(c["subject"]):
                if not g["pr"] or len(cm) == 1:
                    g["inspect"].append((c["hash"], "vague subject"))
        if g["breaking"]:
            g["inspect"].append((g["hashes"][0], "marked breaking"))
        out.append(g)
    return out


def categorize(files):
    cats = {"migrations": [], "config": [], "dependencies": [], "ci_cd": [], "api_surface": []}
    for f in files:
        if LOCK_RE.search(f):
            continue
        for k in cats:
            if cc.SIGNAL_PATTERNS[k].search(f) and not (k == "config" and f.endswith((".md", ".tsx", ".ts", ".cs")) and "config" not in f.lower()):
                cats[k].append(f)
    return cats


def file_diffs(repo, h, files):
    out = cc.git(repo, "show", "--format=", "-U0", "--no-color", h, "--", *files, check=False)
    cur, res = None, {}
    for line in out.splitlines():
        if line.startswith("diff --git"):
            m = re.search(r" b/(.+)$", line)
            cur = m.group(1) if m else None
            res.setdefault(cur, [])
        elif cur and line[:1] in "+-" and not line.startswith(("+++", "---")) and line[1:].strip():
            res[cur].append(line.rstrip())
    return res


def enrich(repo_path, g, depth, limit):
    cats = categorize(g["files"])
    g["cats"] = {k: v for k, v in cats.items() if v}
    want = cats["migrations"] + cats["config"] + cats["dependencies"] + cats["ci_cd"] + cats["api_surface"]
    if not want:
        return
    for c in reversed(g["commits"]):
        mine = [f for f in c["files"] if f in want]
        if not mine:
            continue
        for f, lines in file_diffs(repo_path, c["fullHash"], mine).items():
            if f in cats["api_surface"]:
                for ln in lines:
                    if ln.startswith("+"):
                        for rx, fn in ROUTE_RES:
                            m = rx.search(ln)
                            if m:
                                meth, path = fn(m)
                                item = f"{meth} {path or '(root of group)'}  [{os.path.basename(f)}]"
                                if item not in g["routes"]:
                                    g["routes"].append(item)
                if depth != "deep":
                    continue
            if f in cats["config"]:
                for ln in lines:
                    m = KEY_RE.match(ln)
                    if m and m.group(1) not in g["configKeys"]:
                        g["configKeys"].append(m.group(1))
            if f in cats["dependencies"]:
                lines = [ln for ln in lines if re.search(r'"[@\w/.\-]+"\s*:\s*"[^"]+"|PackageReference|<Version>', ln)]
            if f in cats["migrations"]:
                lines = [ln for ln in lines if ln.startswith("+") and not re.match(r"\+\s*(using |namespace |//|\{|\}|$)", ln)]
            if not lines:
                continue
            cur = g["risky"].setdefault(f, [])
            for ln in lines:
                if ln not in cur:
                    cur.append(ln)
    for f in list(g["risky"]):
        ls = g["risky"][f]
        if len(ls) > limit:
            g["risky"][f] = ls[:limit] + [f"… (+{len(ls) - limit} more lines)"]


def link_groups(groups):
    links = []
    for i, a in enumerate(groups):
        for b in groups[i + 1:]:
            if a["repo"] == b["repo"]:
                continue
            tt = a["tokTitle"] & b["tokTitle"]
            ft = a["tokFiles"] & b["tokFiles"]
            try:
                close = abs((dt.date.fromisoformat(a["date"]) - dt.date.fromisoformat(b["date"])).days) <= 1
            except ValueError:
                close = False
            if len(tt) >= 2 or (tt and (ft or close)) or (len(ft) >= 2 and close):
                links.append({"a": a, "b": b, "shared": sorted(tt | ft), "score": 2 * len(tt) + len(ft) + (1 if close else 0)})
    links.sort(key=lambda l: -l["score"])
    used, out = set(), []
    for l in links:  # greedy one-to-one so a PR is not linked five times
        ka, kb = id(l["a"]), id(l["b"])
        if ka in used or kb in used:
            continue
        used |= {ka, kb}
        out.append(l)
    return out


def ref(g):
    return f"{g['repo']} " + (f"PR {g['pr']}" if g["pr"] else f"direct {g['hashes'][0]}")


def render_md(data, groups_by_repo, links, depth):
    L = [f"# Digest — {data.get('product') or 'changes'} ({data['generatedAt']}, depth: {depth})", ""]
    L += ["## Ranges", "", "| Repo | From | To | Commits | PRs | Direct |", "|---|---|---|---|---|---|"]
    for r in data["repos"]:
        if "error" in r:
            L.append(f"| {r['repo']} | ERROR: {r['error']} | | | | |")
            continue
        g = r["range"]
        frm = g.get("from") or (f"since {g['since']}" if g.get("since") else "(start)")
        L.append(f"| {r['repo']} | {frm} | {g['to']} ({g['toCommit']}) | {r['commitCount']} | {len([m for m in r['merges'] if m['pr']])} | {len(r['directCommits'])} |")
    allg = [g for gs in groups_by_repo.values() for g in gs]
    L += ["", "## Release checklist (from the diffs)", ""]
    mig = [(g, f) for g in allg for f in g.get("cats", {}).get("migrations", [])]
    L.append("- **Migrations:** " + ("; ".join(f"`{f}` ({ref(g)})" for g, f in mig) if mig else "none"))
    cfg = [(g, f) for g in allg for f in g.get("cats", {}).get("config", [])]
    keys = sorted({k for g in allg for k in g["configKeys"]})
    L.append("- **Config files touched:** " + ("; ".join(f"`{f}` ({ref(g)})" for g, f in cfg) if cfg else "none")
             + (f" — keys added/changed: {', '.join('`' + k + '`' for k in keys)}" if keys else ""))
    routes = [(g, rt) for g in allg for rt in g["routes"]]
    L.append("- **Routes added/changed:** " + ("; ".join(f"`{rt}` ({ref(g)})" for g, rt in routes) if routes else "none detected"
                                                 ))
    dep = [(g, f) for g in allg for f in g.get("cats", {}).get("dependencies", [])]
    L.append("- **Dependency manifests touched:** " + ("; ".join(f"`{f}` ({ref(g)})" for g, f in dep) if dep else "none"))
    ci = [(g, f) for g in allg for f in g.get("cats", {}).get("ci_cd", [])]
    L.append("- **CI/CD & container files:** " + ("; ".join(f"`{f}` ({ref(g)})" for g, f in ci) if ci else "none"))
    brk = [g for g in allg if g["breaking"]]
    L.append("- **Breaking:** " + (", ".join(ref(g) for g in brk) if brk else "none marked"))
    for r in data["repos"]:
        if "error" not in r and r["directCommits"]:
            L.append(f"- **Direct commits (no PR) in {r['repo']}:** " + ", ".join(
                f"`{h}`" for h in r["directCommits"]))
    ut = [g for g in allg if g["untested"] and g["type"] in ("feat", "fix", "perf", "refactor", "other")]
    L.append("- **Source changes without test changes:** " + (", ".join(ref(g) for g in ut) if ut else "none"))
    if links:
        L += ["", "## Cross-repo links (candidates — confirm before merging entries)", ""]
        for i, l in enumerate(links, 1):
            L.append(f"- L{i}: {ref(l['a'])} ↔ {ref(l['b'])} — shared: {', '.join(l['shared'])}")
            l["a"]["link"] = l["b"]["link"] = f"L{i}"
    insp = [(g, h, why) for g in allg for h, why in g["inspect"]]
    L += ["", "## Worth reading by hand (inspect)", ""]
    L += [f"- `{h}` {ref(g)} — {why}: `git -C <repo> show {h}`" for g, h, why in insp] or ["- nothing flagged; titles are descriptive"]
    L += ["", "## Groups (newest first)"]
    for r in data["repos"]:
        if "error" in r:
            continue
        for g in sorted(groups_by_repo[r["repo"]], key=lambda x: x["date"], reverse=True):
            tag = f" ↔ {g['link']}" if g.get("link") else ""
            L += ["", f"### [{g['repo']}] {('PR ' + g['pr']) if g['pr'] else 'direct'} · {g['type']}{' · BREAKING' if g['breaking'] else ''} · {g['date']}{tag}",
                  g["title"],
                  f"files {len(g['files'])} (src {g['srcFiles']}, tests {g['testFiles']}) · commits " + ", ".join(f"`{h}`" for h in g["hashes"])
                  + " · " + ", ".join(f"{d} ({n})" for d, n in g["topDirs"])]
            if depth != "quick":  # quick keeps the checklist (keys, routes) but not the fragments
                for f, ls in g["risky"].items():
                    L += [f"`{f}`", "```diff"] + ls + ["```"]
    return "\n".join(L) + "\n"


SECTION_OF = {"feat": "New features", "fix": "Fixes", "perf": "Improvements", "docs": "Documentation"}
INTERNAL = ("refactor", "chore", "ci", "build", "test", "style")


def plain_title(t):
    return re.sub(r"^\w+(\([^)]*\))?!?:\s*", "", t).strip()


def render_skeleton(data, groups_by_repo, links, like):
    allg = [g for gs in groups_by_repo.values() for g in gs]
    linked = {id(l["a"]): l for l in links}
    linked.update({id(l["b"]): l for l in links})
    seen, units = set(), []
    for g in sorted(allg, key=lambda x: x["date"], reverse=True):
        if id(g) in seen:
            continue
        l = linked.get(id(g))
        members = [l["a"], l["b"]] if l else [g]
        seen |= {id(m) for m in members}
        units.append(members)
    sections = {}
    for ms in units:
        t = next((m["type"] for m in ms if m["type"] in SECTION_OF), ms[0]["type"])
        if any(m["breaking"] for m in ms):
            sec = "Breaking changes"
        elif t in SECTION_OF:
            sec = SECTION_OF[t]
        elif t in INTERNAL:
            sec = "Internal"
        else:
            sec = "Other (classify by reading)"
        plats = ", ".join(dict.fromkeys(m["repo"] for m in ms))
        refs = ", ".join((f"PR {m['pr']}" if m["pr"] else f"`{m['hashes'][0]}`") for m in ms)
        title = plain_title(ms[0]["title"])
        mark = " (cross-repo link candidate: confirm or split)" if len(ms) > 1 else ""
        sections.setdefault(sec, []).append(f"- **{title}** — TODO: what the user can now do / what changed. _({plats})_ [{refs}]{mark}")
    L = [f"# {data.get('product') or 'Product'} — release note DRAFT ({data['generatedAt']})", "",
         "<!-- Skeleton generated from the diffs. Replace every TODO with prose after checking the diff; delete empty sections. -->"]
    if like:
        try:
            with open(like, encoding="utf-8") as f:
                heads = [ln.rstrip() for ln in f if ln.startswith("#")]
            L += ["", "<!-- Existing note format to follow (headings of " + os.path.basename(like) + "): -->"] + ["<!-- " + h + " -->" for h in heads[:30]]
        except OSError as e:
            L += ["", f"<!-- --like unreadable: {e} -->"]
    order = ["Breaking changes", "New features", "Improvements", "Fixes", "Documentation", "Other (classify by reading)", "Internal"]
    for sec in order:
        if sec in sections:
            L += ["", f"## {sec}", ""] + sections[sec]
    L += ["", "---", "", "## Technical details", ""]
    mig = [(g, f) for g in allg for f in g.get("cats", {}).get("migrations", []) if "Snapshot" not in f]
    L += ["### Migrations & deployment steps", ""]
    L += [f"- [ ] `{f}` — {g['repo']} ({ref(g)}): TODO what it does to existing data" for g, f in mig] or ["- No migrations in this range."]
    L += ["", "### Configuration changes", "", "| Setting / file | Component | Why / what to do |", "|---|---|---|"]
    rows = 0
    for g in allg:
        keys = g["configKeys"]
        for f in g.get("cats", {}).get("config", []):
            L.append(f"| `{f}`" + (f" (keys: {', '.join('`' + k + '`' for k in keys)})" if keys else "") + f" | {g['repo']} | TODO |")
            rows += 1
    if not rows:
        L.append("| — | — | none |")
    routes = [(g, rt) for g in allg for rt in g["routes"]]
    L += ["", "### API changes", "", "| Method | Endpoint | Change |", "|---|---|---|"]
    L += [f"| {rt.split(' ', 1)[0]} | `{rt.split(' ', 1)[1].split('  [')[0]}` | TODO ({ref(g)}) |" for g, rt in routes] or ["| — | — | none detected |"]
    dep = [(g, f) for g in allg for f in g.get("cats", {}).get("dependencies", [])]
    if dep:
        L += ["", "### Dependencies", ""] + [f"- `{f}` — {ref(g)}: TODO what changed" for g, f in dep]
    ci = [(g, f) for g in allg for f in g.get("cats", {}).get("ci_cd", [])]
    if ci:
        L += ["", "### CI/CD & container", ""] + [f"- `{f}` — {ref(g)}: TODO why" for g, f in ci]
    L += ["", "### Deploy order & compatibility", "", "- TODO: which side ships first; what breaks otherwise (say so explicitly if nothing does)."]
    for r in data["repos"]:
        if "error" not in r and r["directCommits"]:
            L += ["", f"### Direct commits without PR ({r['repo']})", ""] + [f"- `{h}`" for h in r["directCommits"]]
    L += ["", "### Components", "", "| Repo | From | To | Commits |", "|---|---|---|---|"]
    for r in data["repos"]:
        if "error" in r:
            continue
        g = r["range"]
        frm = g.get("from") or (f"since {g['since']}" if g.get("since") else "(start)")
        L.append(f"| {r['repo']} | {frm} | {g['to']} ({g['toCommit']}) | {r['commitCount']} |")
    return "\n".join(L) + "\n"


def main():
    ap = cc.build_parser()
    ap.description = __doc__
    ap.add_argument("--changes", help="reuse a changes.json produced by collect_changes.py")
    ap.add_argument("--depth", choices=["quick", "standard", "deep"], default="standard")
    ap.add_argument("--diff-lines", type=int, help="max diff lines kept per risky file (default 25 / 80 for deep)")
    ap.add_argument("--like", help="with --format skeleton: existing release note whose headings the draft should follow")
    for a in ap._actions:
        if a.dest == "format":
            a.choices = ["json", "md", "skeleton"]
    ap.set_defaults(format="md")
    args = ap.parse_args()
    data = load(args)
    limit = args.diff_lines or (80 if args.depth == "deep" else 25)
    groups_by_repo = {}
    for r in data["repos"]:
        if "error" in r:
            continue
        gs = build_groups(r)
        for g in gs:
            enrich(r["path"], g, args.depth, limit)
        groups_by_repo[r["repo"]] = gs
    links = link_groups([g for gs in groups_by_repo.values() for g in gs])
    if args.format == "json":
        def clean(g):
            return {k: (sorted(v) if isinstance(v, set) else v) for k, v in g.items()
                    if k not in ("tokTitle", "tokFiles", "commits", "files")}
        text = json.dumps({"generatedAt": data["generatedAt"], "product": data.get("product"),
                           "groups": {k: [clean(g) for g in v] for k, v in groups_by_repo.items()},
                           "links": [{"a": ref(l["a"]), "b": ref(l["b"]), "shared": l["shared"]} for l in links]},
                          indent=2, ensure_ascii=False)
    elif args.format == "skeleton":
        text = render_skeleton(data, groups_by_repo, links, args.like)
    else:
        text = render_md(data, groups_by_repo, links, args.depth)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"wrote {args.out}")
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(text)


if __name__ == "__main__":
    main()
