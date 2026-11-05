#!/usr/bin/env python3
"""Check the factual claims of a release note / CHANGELOG section against the repos. No LLM, <1 s.

Extracts from NOTE: PR numbers, HTTP endpoints, config keys, migration names, commit hashes - and checks each
against git history and the diffs of the range. Then lists what the digest found that NOTE never mentions
(migrations, config keys, direct commits) and flags a "no migration" claim when migrations exist.

Takes every digest.py range option (--config, --repo, --since-last-release, --range name=a..b, ...).

  python verify.py --note SURUM-NOTU-2026-11-05.md --config .releasemaster/releasemaster.config.json --since-last-release
  python verify.py --note CHANGELOG.md --section 1.5.0 --repo ../api --repo ../web --range api=a1b2c3d..HEAD

Exit code 1 when an ERROR was found (claim without any evidence). WARN/CHECK need a human look, not necessarily a fix.
  ERROR  claim with no evidence anywhere (unknown PR, endpoint/key/migration/hash not in the repos)
  WARN   claim is real but outside the range (e.g. a PR already covered by an older note) or not touched in the range
  CHECK  something in the range the note never mentions, or a contradiction with the diffs
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect_changes as cc  # noqa: E402
import digest as dg  # noqa: E402

PR_RE = re.compile(r"\bPR\s*#?\s*(\d{3,6})\b|(?<![\w/])#(\d{3,6})\b", re.I)
EP_RE = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+`?(/[^\s`|)\]>,;]*)")
TICK_RE = re.compile(r"`([^`\n]{2,80})`")
KEYLIKE = re.compile(r"^[A-Za-z_][\w]*(__[\w]+)+$|^[A-Z][A-Z0-9]*(_[A-Z0-9]+)+$|^[A-Za-z][\w-]*(\.[A-Za-z][\w-]*){2,}$|^[A-Za-z][\w]*(:[A-Za-z][\w]*)+$")
MIG_RE = re.compile(r"\b(\d{8,14}_[A-Za-z0-9_]+)")
HASH_RE = re.compile(r"^[0-9a-f]{7,12}$")
NO_MIG = re.compile(r"(migration|veritaban\w*|şema|schema)(?:(?!test|için)[^.\n]){0,40}\b(yok|gerekmiyor|bulunmuyor|eklenmedi|değişmedi|not required|none)\b|\b(no|yok)\s+(database\s+)?(migrations?|veritaban\w*|schema)", re.I)


def section(text, name):
    """Return the CHANGELOG section for `name` (## [name] ... up to the next ## [)."""
    m = re.search(r"^##\s*\[?" + re.escape(name) + r"\]?.*$", text, re.M)
    if not m:
        return None
    n = re.search(r"^##\s*\[", text[m.end():], re.M)
    return text[m.start(): m.end() + (n.start() if n else len(text) - m.end())]


def hist_prs(path):
    out = cc.git(path, "log", "--all", "--format=%s%n%b", check=False)
    return set(re.findall(r"PR\s*#?\s*(\d{3,6})", out, re.I)) | set(re.findall(r"\(#(\d{3,6})\)", out))


def head_grep(path, needle):
    r = cc.git(path, "grep", "-I", "-l", "-F", "-e", needle, "HEAD", check=False)
    return bool(r.strip())


def route_grep(path, seg):
    """Is `seg` used in a route registration (MapGet(...), [HttpPost("...")], app.get('...')) at HEAD?"""
    rx = r"(Map(Get|Post|Put|Delete|Patch|Group)|Http(Get|Post|Put|Delete|Patch)|(app|router)\.(get|post|put|delete|patch)|Mapping)[^\n]*" + re.escape(seg)
    return bool(cc.git(path, "grep", "-I", "-l", "-E", "-e", rx, "HEAD", check=False).strip())


def segs(p):
    return [s for s in re.split(r"[/?]", p.split("?")[0]) if s and not s.startswith("{") and not s.startswith(":")]


def main():
    ap = cc.build_parser()
    ap.description = __doc__
    ap.formatter_class = __import__("argparse").RawDescriptionHelpFormatter
    ap.add_argument("--note", required=True, help="release note or CHANGELOG file to check")
    ap.add_argument("--section", help="CHANGELOG version section to check (e.g. 1.5.0); default: whole file")
    ap.set_defaults(format="md", changes=None)
    args = ap.parse_args()
    text = open(args.note, encoding="utf-8").read()
    if args.section:
        text = section(text, args.section)
        if text is None:
            sys.exit(f"section {args.section} not found in {args.note}")
    data = dg.load(args)
    repos = [r for r in data["repos"] if "error" not in r]
    groups = []
    for r in repos:
        for g in dg.build_groups(r):
            dg.enrich(r["path"], g, "standard", 25)
            groups.append(g)
    paths = [r["path"] for r in repos]
    range_prs = {g["pr"] for g in groups if g["pr"]}
    all_prs = set().union(*(hist_prs(p) for p in paths)) if paths else set()
    changed = [f for r in repos for c in r["commits"] for f in c["files"]]
    changed_stems = {os.path.splitext(os.path.basename(f))[0] for f in changed}
    routes = [rt for g in groups for rt in g["routes"]]
    route_segs = set()
    for rt in routes:
        route_segs |= set(segs(rt.split(" ", 1)[1].split("  [")[0]))
    cfg_keys = {k for g in groups for k in g["configKeys"]}
    cfg_files = [f for g in groups for f in g.get("cats", {}).get("config", [])]
    migs = sorted({f for g in groups for f in g.get("cats", {}).get("migrations", []) if "Snapshot" not in f})
    direct = [(r["repo"], h) for r in repos for h in r["directCommits"]]
    findings = []  # (level, message)
    ok = []

    def add(level, msg):
        findings.append((level, msg))

    # PRs
    outside = []
    for n in sorted({a or b for a, b in PR_RE.findall(text)}):
        if n in range_prs:
            ok.append(f"PR {n}")
        elif n in all_prs:
            outside.append(n)
        else:
            add("ERROR", f"PR {n} does not exist in any repo history (invented or mistyped)")
    if outside:
        add("WARN", "PRs cited that are outside the range: " + ", ".join(outside) + " — fine as boundary/context references; a mistake if the note presents them as new")
    # endpoints
    for meth, p in sorted(set(EP_RE.findall(text))):
        p = p.rstrip(".")
        s = segs(p)
        static = [x for x in s if x.lower() not in ("api", "v1", "v2")]
        if not static:
            continue
        if all(x in route_segs for x in static):
            ok.append(f"{meth} {p}")
        elif any(route_grep(pp, static[-1]) for pp in paths):
            add("WARN", f"{meth} {p}: no matching route was added in this range, but a route with `{static[-1]}` exists at HEAD — fine only if the note describes a changed behaviour of an existing endpoint")
        else:
            add("ERROR", f"{meth} {p}: nothing like it in any repo (invented endpoint?)")
    # config keys, migrations, hashes (backticked tokens)
    ticks = {t.strip() for t in TICK_RE.findall(text)}
    for t in sorted(ticks):
        if KEYLIKE.match(t) and "/" not in t:
            if t in cfg_keys:
                ok.append(f"key {t}")
            elif any(head_grep(pp, t) for pp in paths):
                add("WARN", f"config key `{t}` exists at HEAD but was not added/changed in the range")
            else:
                add("ERROR", f"config key `{t}` is not found in any repo (invented or mistyped)")
        elif HASH_RE.match(t) and re.search(r"\d", t):
            hit = [pp for pp in paths if cc.git(pp, "cat-file", "-t", t, check=False).strip() == "commit"]
            if hit:
                ok.append(f"commit {t}")
            else:
                add("ERROR", f"commit `{t}` does not exist in any repo")
    for m in sorted(set(MIG_RE.findall(text))):
        if m in changed_stems:
            ok.append(f"migration {m}")
        else:
            add("ERROR", f"migration {m} is not among the files changed in the range")
    # omissions and contradictions
    for f in migs:
        stem = os.path.splitext(os.path.basename(f))[0]
        core = re.sub(r"^\d+_", "", stem)
        if stem not in text and core not in text:
            add("CHECK", f"migration `{stem}` is in the range but the note never names it")
    if migs and NO_MIG.search(text):
        add("CHECK", f"the note says there is no migration, but the range contains {len(migs)}: " + ", ".join(os.path.basename(f) for f in migs))
    for k in sorted(cfg_keys):
        if k not in text:
            add("CHECK", f"config key `{k}` changed in the range but the note never mentions it")
    is_changelog = os.path.basename(args.note).upper().startswith("CHANGELOG")
    for repo, h in ([] if is_changelog else direct):  # a CHANGELOG lists changes, not hashes
        if h not in text and not any(h.startswith(x) or x.startswith(h) for x in ticks if HASH_RE.match(x)):
            add("CHECK", f"direct commit `{h}` ({repo}, no PR) is not mentioned — release managers want these listed")
    unrep = sorted(n for n in range_prs if n not in text)
    if unrep:
        add("CHECK", "PRs in the range never mentioned: " + ", ".join(unrep) + " (fine if they are internal/noise)")

    order = {"ERROR": 0, "WARN": 1, "CHECK": 2}
    findings.sort(key=lambda x: order[x[0]])
    errs = sum(1 for l, _ in findings if l == "ERROR")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"# verify {os.path.basename(args.note)}" + (f" §{args.section}" if args.section else "")
          + f" — {len(ok)} claims verified, {errs} errors, {len(findings) - errs} to check")
    for l, m in findings:
        print(f"- {l}: {m}")
    if not findings:
        print("- nothing to flag")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
