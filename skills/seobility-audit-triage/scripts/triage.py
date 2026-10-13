#!/usr/bin/env python3
"""Turn a Seobility Site Audit into a fix plan.

Two subcommands:

  rank     Score every issue report by Seobility's own severity divided by our effort
           estimate, and flag the rows that are not defect counts at all.

  cluster  Group a report's affected URLs by path pattern, so a fix that looks like
           N page edits can be recognised as one template change.

Both read JSON exactly as the MCP returned it (the full tool result, or its `data`
member - either works). Pass `-` instead of a path to read it from stdin.

    python triage.py rank problems.json --indexed 1444
    python triage.py cluster report-rows.json --label heading-h1-problems --indexed 1444
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from urllib.parse import parse_qsl

MATRIX = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "references", "impact-effort.md")

# Reports whose rows are text blocks or pairs, not pages. Verified: the `columns` of
# pages-with-duplicate-text-content are `text` + `pages`, and on a live project its
# count was more than three times the project's whole indexable set.
NOT_PAGE_COUNTS = {"pages-with-duplicate-text-content"}

# Reports whose missing value is written per instance, however many pages carry it.
# High reach does not make these a template fix: an alt text or an anchor is decided
# by a person on every site. Together with every `editorial` report in the matrix,
# these are exempt from the reach promotion in `cluster`.
WRITTEN_PER_INSTANCE = {
    "image-alt-attribute-problems",
    "link-anchor-text-problems",
    "link-anchor-text-duplicates-for-different-pages",
}

# Reports that must be planned first whatever they score, because every other finding
# is measured on pages these ones say are broken.
BLOCKING = {
    "pages-broken",
    "redirect-target-problems",
    "internal-link-targets-on-redirect-loops",
    "canonical-link-target-problems",
    "error-output-problems",
}

# Measurements of one crawl, not properties of the site. Verified on a wiki project
# (24.09.2026): 90 of 98 slow responses arrived with the latest crawl, on a site whose
# average response was 0.37 s. A spike like that is a busy server during one crawl as
# often as a slow site, and it scored first in the plan. When at least half the count
# is new, the report leaves the ranking and goes to RE-MEASURE FIRST.
# The two reports are judged as a PAIR: they measure the same server in the same crawl.
# Judged one by one on that wiki, slow (90 of 98 new) went to re-measure while medium
# (100 of 239 new) stayed in the plan as a server job - the same server, twice.
RE_MEASURE = {
    "pages-with-slow-server-response-times",
    "pages-with-medium-server-response-times",
}
# A spike of one or two pages is no evidence of a busy server ("1 of 1 new" fired it).
RE_MEASURE_MIN = 5

# A report with no Seobility weight whose rows are still real: it is never a coverage
# row, whatever its count. Its `filters` decide (get_report with limit 1).
NEEDS_FILTERS = {"schema-validation"}

# Reports whose rows are link TARGETS, not affected pages. `internal-link-targets-on-
# redirects` returns one row per redirecting URL with the pages linking to it, so its
# count set against indexed_pages is two different units. Reach says nothing here; the
# path pattern of the targets does: 375 targets on one wiki were two patterns (the
# home link with a trailing slash, and an old image path), i.e. two changes.
TARGET_ROWS = {"internal-link-targets-on-redirects"}

# Weight 50 puts a few findings near the top, and the anchor text decides the fix: a
# generic listing label ("show more") is one template change, a content anchor is a
# decision per link, a fixed credit line can wait.
READ_THE_ANCHORS = {"link-anchor-text-duplicates-for-different-pages"}

COST = {
    "config": lambda n: 1.0,
    "template": lambda n: 1.0,
    "bulk": lambda n: 1.0 + n / 50.0,
    "page": lambda n: n * 0.1,
    "editorial": lambda n: n * 0.5,
}

# Two classes carry no cost model on purpose, so they never enter the ordering.
#
#   `inspect` - the cost cannot be known from the API. One sample page decides whether
#               the fix is a template change or a rewrite per page, and those differ by
#               two orders of magnitude. Scoring either guess would be a lie.
#   `none`    - a true finding with no sensible fix on most sites. A low score still
#               leaves it in the backlog, and a backlog entry nobody should ever do is
#               worse than no entry.
UNSCORED = {"inspect", "none"}

# Reports whose findings split into sub-types with genuinely different fixes, so one
# class for the whole report always over- or under-costs part of it. The matrix gives
# these the most expensive of their sub-type classes, so an unsplit plan errs towards
# too much effort rather than too little.
SUBTYPED = {
    "canonical-link-target-problems",   # four sub-types, three different fixes
    "title-problems",                   # too long / too short / repeated word
    "heading-h1-problems",              # missing / too short / one word / too many
    "meta-description-problems",
}

# Reports whose effort genuinely depends on the site, not on the fix mechanism. The
# matrix gives each of these a decision rule and a conservative default; the class in
# the table is the expensive branch, so an unresolved plan over-costs rather than
# under-costs. Resolve them from the clustering or the affected ratio before planning.
CONDITIONAL = {
    "pages-with-high-page-depth",     # archives = no fix; buried products = a project
    "pages-with-large-file-size",     # a few pages, or the page builder
    "title-duplicates",               # pagination = one setting; distinct pages = N edits
    "description-duplicates",
    "heading-h1-problems",            # template or per page
    "url-dynamic-parameters",         # cost is per parameter, never per URL
    "internal-link-targets-on-redirects",  # one pattern = one change; mixed = repoints
}

# Reports where the report's count is not what drives the effort. Saying both numbers
# is the difference between "480,000 URLs" and "nine parameters to decide about".
COST_DRIVER = {
    "url-dynamic-parameters": "distinct parameters, not URLs",
    "title-duplicates": "duplicate groups (pagination.total), not pages",
    "description-duplicates": "duplicate groups (pagination.total), not pages",
    "image-alt-attribute-problems": "images, which is more than pages",
    "pages-with-duplicate-text-content": "pages, which this report does not give you",
}


# The part of the plan a reader acts on this week. A swing below it moves nothing they see.
PLAN_CUT = 10

# Reports whose bold words are repetitions, not missing words.
BOLD_IS_REPEAT = {"title-problems"}

# Keys the MCP puts next to `data`. get_report returns {data, pagination, crawl_id}; a check on
# `len(payload) <= 2` never unwrapped it, so `cluster` saw no rows and blamed the data.
ENVELOPE = {"data", "pagination", "crawl_id", "filters", "columns", "success", "message"}


def unwrap(payload):
    """Accept the raw tool result, its `data` member, or a saved content-block list."""
    # Some hosts save a result as [{"type": "text", "text": "<the JSON>"}].
    while isinstance(payload, list) and payload and isinstance(payload[0], dict) \
            and payload[0].get("type") == "text" and "text" in payload[0]:
        payload = json.loads(payload[0]["text"])
    while isinstance(payload, dict) and "data" in payload and set(payload) <= ENVELOPE:
        payload = payload["data"]
    return payload


def read_json(path):
    """A saved payload, or `-` for stdin (a result that arrived inline)."""
    if path == "-":
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8")
        return json.load(sys.stdin)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_matrix(path=MATRIX):
    """Parse the effort class and fix shape out of the reference file's tables."""
    rows = {}
    if not os.path.exists(path):
        return rows
    cell = re.compile(r"^\|\s*`([a-z0-9-]+)`\s*\|(.*?)\|\s*`([a-z]+)`\s*\|(.*?)\|\s*$")
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = cell.match(line.rstrip())
            if m:
                rows[m.group(1)] = {
                    "class": m.group(3),
                    "row_is": m.group(2).strip(),
                    "fix": m.group(4).strip().rstrip("."),
                }
    return rows


def parse_assumptions(pairs):
    """--assume report=class, repeatable. The user's site beats the table."""
    out = {}
    for pair in pairs or []:
        report, _, klass = pair.partition("=")
        report, klass = report.strip(), klass.strip()
        if not report:
            raise SystemExit(f"--assume '{pair}' names no report. Use REPORT=CLASS.")
        if not klass or (klass not in COST and klass not in UNSCORED):
            raise SystemExit(f"Unknown effort class '{klass}'. "
                             f"Use one of: {', '.join(sorted(set(COST) | UNSCORED))}")
        out[report] = klass
    return out


# The one question worth resolving about each class, and the answer that would
# change it. These are questions to ANSWER from evidence, not to put to the user:
# almost nobody knows off the top of their head whether their H1s come out of a
# template. `cluster` answers most of them from data already in hand.
PLAUSIBLE_ALT = {
    "page": ("template", "is this generated, rather than written per page?"),
    "editorial": ("template", "is this one shared block, rather than real copy per page?"),
    "bulk": ("page", "is the correct new value knowable, or decided case by case?"),
    "template": ("page", "is it really one change, or does each page need its own?"),
    "config": ("page", "is it really one setting, or does each page need its own?"),
}

# The conditional reports carry their own decision rule in the matrix, so their
# alternative is the other branch of that rule, not the generic one for the class.
# The matrix class is always the expensive branch; this is the cheap one.
RULE_ALT = {
    "title-duplicates": ("config", "are the duplicates paginated or filtered variants of one listing?"),
    "description-duplicates": ("config", "are the duplicates paginated or filtered variants of one listing?"),
    "pages-with-high-page-depth": ("none", "are the deep pages archives, tag pages or pagination?"),
    "pages-with-large-file-size": ("template", "is most of the crawled set affected?"),
    "heading-h1-problems": ("template", "do the affected URLs cluster on one page type?"),
    "internal-link-targets-on-redirects": ("template", "do the redirect targets share one "
                                           "pattern (a trailing slash, an old asset path)?"),
}


def swing(rows, limit):
    """Which effort assumptions, if wrong, would actually change the plan?

    Every class is a default for a typical site, not a fact about this one - so
    in principle the user should check all of them. In practice nobody checks
    forty-five rows, and a report that asks them to has told them nothing.

    Two filters, and both are needed. First, only rows whose class is genuinely
    in question: the ones the matrix marks conditional or sub-typed, plus any
    large per-page job, because "is this generated?" is a live question on any
    site whenever the count is high. Second, only alternatives a human would
    actually propose - one per class. Then keep what moves the plan.
    """
    base = sorted(rows, key=lambda r: (not r["blocking"], -r["score"], -r["impact"]))
    base_rank = {r["report"]: i + 1 for i, r in enumerate(base)}
    # A rank swing on a report worth a twentieth of the largest one is still a
    # swing, and still not worth a question: both branches are an afternoon at
    # most. Scale-free, so it behaves the same on a 500-page site and a shop.
    floor = 0.05 * max((r["impact"] for r in rows), default=0)
    findings = []
    for r in rows:
        klass = r["class"]
        if klass in UNSCORED or klass not in PLAUSIBLE_ALT or r["impact"] < floor:
            continue
        contested = (r["report"] in CONDITIONAL
                     or r["report"] in SUBTYPED
                     or (r["count"] >= 100 and klass in {"page", "editorial"}))
        if not contested:
            continue
        if r["report"] in RULE_ALT and not r["assumed"]:
            alt_class, question = RULE_ALT[r["report"]]
        else:
            alt_class, question = PLAUSIBLE_ALT[klass]
        here = base_rank[r["report"]]
        if alt_class in UNSCORED:
            # The other branch takes the report out of the plan altogether, which
            # always changes the plan.
            findings.append((r, alt_class, question, here, None))
            continue
        else:
            cost = COST[alt_class](r["count"])
            alt_score = r["impact"] / cost if cost else 0.0
            ahead = sum(1 for x in rows
                        if x["report"] != r["report"]
                        and (x["blocking"], x["score"]) > (r["blocking"], alt_score))
            there = ahead + 1
        # Only what changes the plan the reader sees: crossing the cut, or a real reorder
        # inside it. Swings below the cut filled the block with 11 questions on a 2,700-page
        # site, where the SKILL promises "usually one or two".
        cut = min(limit, PLAN_CUT)
        crosses = (here <= cut) != (there <= cut)
        reorders = here <= cut and there <= cut and abs(there - here) >= 3
        if crosses or reorders:
            findings.append((r, alt_class, question, here, there))
    return findings


def rank(args):
    payload = unwrap(read_json(args.problems))
    if not isinstance(payload, list) and "problems" not in payload:
        raise SystemExit("No `problems` in this payload - pass the get_site_audit_problems "
                         "result, not the overview or a report.")
    problems = payload if isinstance(payload, list) else payload["problems"]
    assumed = parse_assumptions(args.assume)
    matrix = load_matrix()
    if not matrix:
        problem = ("has no rows in the expected table format" if os.path.exists(MATRIX)
                   else "not found")
        print(f"WARNING: references/impact-effort.md {problem} - effort defaults to `page`.\n",
              file=sys.stderr)

    scored, excluded, unweighted, inspect, ignored, blocks, remeasure = \
        [], [], [], [], [], [], []
    spike = not args.no_baseline and any(
        p.get("analysis") in RE_MEASURE and (p.get("count") or 0) >= RE_MEASURE_MIN
        and (p.get("delta") or 0) * 2 >= p["count"] for p in problems)
    for p in problems:
        if p.get("type") != "analysis":
            continue                      # minicheck and hint rows are measurements
        count = p.get("count") or 0
        if not count:
            continue
        slug = p.get("analysis") or p.get("translation_variable", "?")
        impact = p.get("total_impact") or 0
        weight = round(impact / count, 1) if count else 0

        flags = []
        if impact == 0:
            flags.append("no-weight")
        # A coverage row needs BOTH signals. Equality alone also matches a real defect
        # on every page - compression switched off fires on 100% of the site, and is
        # the first job in the audit, not an excluded row.
        if args.indexed and count == args.indexed and impact == 0 \
                and slug not in NEEDS_FILTERS:
            flags.append("coverage")
        if slug in NOT_PAGE_COUNTS:
            flags.append("not-pages")
        # A count above indexed_pages is a hint, not a verdict: broken URLs, redirects
        # and slow responses are counted on non-indexable pages too. Keep the row in
        # the plan and make the reader check `columns` before trusting the count.
        elif args.indexed and count > args.indexed:
            flags.append("check-columns")

        entry = matrix.get(slug, {})
        klass = assumed.get(slug, entry.get("class", "page"))
        cost = 0.0 if klass in UNSCORED else COST.get(klass, COST["page"])(count)
        score = impact / cost if cost else 0.0

        row = {
            "report": slug,
            "count": count,
            "delta": p.get("delta"),
            "weight": weight,
            "impact": impact,
            "class": klass,
            "cost": round(cost, 1),
            "score": round(score),
            "blocking": slug in BLOCKING,
            # Everything in the report arrived with this crawl. For a blocking report that
            # is as likely a crawl that timed out as a site that broke overnight.
            "new": slug in BLOCKING and p.get("delta") == count and not args.no_baseline,
            "flags": sorted(set(flags)),
            "fix": entry.get("fix", ""),
            "assumed": slug in assumed,
        }
        # A coverage row counts pages checked, not pages broken, and leaves the plan.
        # A not-pages row counts text blocks, so its count cannot be costed - but the
        # finding is real, and on a live blog it held the most valuable content job in
        # the audit (a whole article series sharing its paragraphs). It goes to its own
        # list, to be read, never to the bin.
        #
        # A zero weight on its own is NOT the same thing. Verified on a third project:
        # `sitemaps-issues` and `sitemaps-pages-only-found-in-sitemaps` carry
        # total_impact 0 and are real defects. They cannot be scored, so they go in
        # their own list rather than into the order or the bin.
        if "coverage" in row["flags"]:
            excluded.append(row)
        elif slug in RE_MEASURE and spike:
            remeasure.append(row)
        elif "not-pages" in row["flags"]:
            blocks.append(row)
        elif klass == "inspect":
            inspect.append(row)
        elif klass == "none":
            ignored.append(row)
        elif impact == 0:
            unweighted.append(row)
        else:
            scored.append(row)

    scored.sort(key=lambda r: (not r["blocking"], -r["score"], -r["impact"]))
    limit = args.limit or len(scored)

    if remeasure:
        print("RE-MEASURE FIRST - at least half of one response-time report arrived with the latest")
        print("crawl, so both are held back: they measure the same server in the same crawl.")
        print("A response-time spike is a busy server during one crawl as often as a slow")
        print("site. Pull the rows (which pages, how slow against the site average) and")
        print("plan a new crawl as the first step; plan the fix only if the new crawl")
        print("confirms it. Not ranked:\n")
        for r in remeasure:
            print(f"   {r['report'][:52]:52} {r['count']:>7}  ({r['delta'] or 0} new)")
        print()

    if inspect:
        print("CHECK THESE FIRST - ten minutes each, and the answer changes the plan:\n")
        for r in sorted(inspect, key=lambda r: -r["impact"]):
            print(f"   {r['report'][:52]:52} {r['count']:>7} pages")
        print("   Open one affected page (Details in the app). The cost of these is one")
        print("   template change or an edit per page, and nothing in the API says which.")
        print("   external-link-target-problems: re-request every flagged URL with a browser")
        print("   user agent first; only a live 404/410 or a DNS failure is dead.\n")

    if blocks:
        print("READ THE ROWS - real findings counted in text blocks, not pages. The count")
        print("cannot be costed. Pull the rows and sort the repeated texts into what they")
        print("are: long teasers on overview pages (shorten the excerpt, one setting), the")
        print("same paragraphs across several articles (a rewrite per article), author bios")
        print("and credit lines (low priority). The first two go in the plan:\n")
        for r in blocks:
            print(f"   {r['report'][:52]:52} {r['count']:>7} findings, not pages")
        print()

    print("SCORE = Seobility total_impact / our effort estimate. Order is the plan order.")
    print("The `class` column is an ASSUMPTION about this site, not a fact. Everything")
    print("below the table says which assumptions are worth the user's time to check.\n")
    hdr = f"{'':2} {'report':52} {'pages':>6} {'wt':>5} {'impact':>7} {'class':10} {'cost':>7} {'score':>7}"
    print(hdr)
    print("-" * len(hdr))
    for r in scored[:limit]:
        mark = "!!" if r["blocking"] else "  "
        tag = ("NEW " if r["new"] else "") + \
              ("=" if r["assumed"] else "") + \
              ("~" if r["report"] in CONDITIONAL else "") + \
              ("*" if r["report"] in SUBTYPED else "")
        label = r["report"] + (" " + tag if tag else "")
        print(f"{mark} {label[:52]:52} {r['count']:>6} {r['weight']:>5} "
              f"{r['impact']:>7} {r['class']:10} {r['cost']:>7} {r['score']:>7}")

    if len(scored) > limit:
        print(f"\n... {len(scored) - limit} further reports below the cut.")

    oversized = [r for r in scored + unweighted if "check-columns" in r["flags"]]
    if oversized:
        print("\nCOUNT ABOVE THE INDEXABLE SET - check get_report_meta.columns before")
        print("planning these. If the first column is `page`, the count includes")
        print("non-indexable URLs and the row stands. If it is `text` or `item`, the rows")
        print("are not pages - move the report to EXCLUDED:\n")
        for r in oversized:
            print(f"   {r['report'][:52]:52} {r['count']:>7} > {args.indexed}")

    movers = swing(scored, limit)
    if movers:
        print("\nRESOLVE THESE YOURSELF - open questions that actually move the plan:\n")
        for r, klass, question, here, there in sorted(movers,
                                                      key=lambda m: min(m[3], m[4] or m[3])):
            print(f"   #{here} {r['report']}  - assumed {r['class']}")
            print(f"        Q: {question}")
            if klass in UNSCORED:
                print(f"        If yes ({klass}): leaves the plan."
                      f"  --assume {r['report']}={klass}")
            else:
                direction = "up to" if there < here else "down to"
                print(f"        If yes ({klass}): moves {direction} #{there}."
                      f"  --assume {r['report']}={klass}")
            print(f"        Check: cluster this report with --indexed, then look at two")
            print(f"        affected pages and one unaffected page of the same type.\n")
        print("   Do not put these to the user - most people do not know whether their")
        print("   H1s come out of a template, and asking makes it their problem. Answer")
        print("   them from the crawl and from the pages themselves. Where you cannot,")
        print("   keep the assumption, plan on it, and say so in one line so the user can")
        print("   correct you if they do happen to know.")
        print("   Every other class in the plan can be wrong without changing the order.")

    if unweighted:
        print("\nUNWEIGHTED - real findings Seobility gives no severity to, so they cannot be")
        print("scored. Judge these yourself; a small count here is often worth the fix:\n")
        for r in sorted(unweighted, key=lambda r: -r["count"]):
            mark = "!!" if r["blocking"] else "  "
            print(f"{mark} {r['report'][:52]:52} {r['count']:>7}   ({r['class']})")
        if any(r["report"] in NEEDS_FILTERS for r in unweighted):
            print("   schema-validation has no weight but its rows are real (`critical` or `tip`).")
            print("   get_report(analysis=\"schema-validation\", limit=1) and read `filters`: only")
            print("   `schema_recommended_missing` keys means tips (--assume schema-validation=none).")

    if ignored:
        print("\nNO SENSIBLE FIX on this site - resolved to `none`. Never drop them: say what")
        print("Seobility flags and why it does not apply here. Check any row marked ~")
        print("against this site first:\n")
        for r in sorted(ignored, key=lambda r: -r["count"]):
            tag = " ~" if r["report"] in CONDITIONAL else ""
            print(f"   {(r['report'] + tag)[:52]:52} {r['count']:>7}")

    if excluded:
        print("\nEXCLUDED - these count pages checked, not pages with a problem:\n")
        for r in excluded:
            why = ", ".join(r["flags"]) or "no weight"
            print(f"   {r['report'][:52]:52} {r['count']:>7}   ({why})")

    print("\n!! = blocking. Plan these first whatever they score: every other finding is "
          "measured\n   on pages these reports say are broken.")
    if any(r["new"] for r in scored + unweighted):
        print("NEW = every finding in this blocking report arrived with the latest crawl\n"
              "     (delta == count). Pull the rows and the report history first: rows with\n"
              "     statuscode null that were 0 in earlier crawls are a crawl that got no\n"
              "     answer, and the plan starts with a new crawl, not a fix.")
    if any(r["report"] in READ_THE_ANCHORS for r in scored[:limit]):
        print("Anchor duplicates: read the anchor texts before planning. A generic label\n"
              "     (\"show more\") is one template fix; a descriptive keyword whose target\n"
              "     depends on the section is by design; only credit lines can wait.")
    shown = scored[:limit] + ignored + inspect
    if any(r["report"] in CONDITIONAL for r in shown):
        print(" ~ = the class depends on this site, not on the fix. Resolve it from the\n"
              "     clustering or the affected ratio - the rule is in impact-effort.md,\n"
              "     and the class shown is the expensive branch.")
    if any(r["report"] in SUBTYPED for r in shown):
        print(" * = several different fixes in one report. Pull its sub-type split before\n"
              "     planning it - the class shown is the most expensive of them.")
    drivers = [(r["report"], COST_DRIVER[r["report"]])
               for r in shown if r["report"] in COST_DRIVER]
    if drivers:
        print("\nThe count is not the cost driver for these - report both numbers:")
        for report, driver in drivers:
            print(f"   {report[:44]:44} cost scales with {driver}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"scored": scored, "remeasure": remeasure,
                       "inspect": inspect, "blocks": blocks,
                       "unweighted": unweighted, "ignored": ignored,
                       "excluded": excluded}, fh, indent=1)
        print(f"\nWrote {args.json}")


PLACEHOLDERS = [
    # A language prefix is not a pattern. Without this, one template on a three-language
    # site splits into three clusters and never crosses the promotion threshold - which
    # is exactly what happened on the first live run of this script.
    (re.compile(r"^/(?:[a-z]{2})(?:-[a-z]{2})?(?=/)", re.I), "/{lang}"),
    (re.compile(r"/page/\d+/?"), "/page/{n}/"),
    (re.compile(r"/\d{4}/\d{2}(/\d{2})?/"), "/{date}/"),
    (re.compile(r"/\d+(?=/|$)"), "/{n}"),
]


def value_of(row):
    """The offending value a report row carries, whatever shape it comes in.

    This is the strongest template signal in the whole skill and it costs no
    extra call: if 284 pages are flagged for a short H1 and the H1s are 284
    different words, someone wrote them. If they are four values repeated, a
    template is filling them in.
    """
    for item in row.get("items") or []:
        if isinstance(item.get("formatted_text"), dict):
            return item["formatted_text"].get("raw")
        for key in ("text", "page", "count", "page_level", "number_of_directories"):
            if key in item and not isinstance(item[key], (dict, list)):
                return item[key]
    return None


def shape_of(value):
    """Generalise a text value so near-identical variants collapse together.

    A template usually leaves a constant frame around a variable slot -
    "<term> - Brand" - so replacing the words that differ reveals whether
    the frame is shared.
    """
    if not isinstance(value, str):
        return value
    shape = re.sub(r"\d+", "#", value)
    shape = re.sub(r"[^\W\d_]{2,}", "w", shape, flags=re.UNICODE)
    return re.sub(r"\s+", " ", shape).strip()


def pattern_of(url, depth):
    """A path pattern: the first `depth` segments, with numbers generalised."""
    path = re.sub(r"^https?://[^/]+", "", url).split("#", 1)[0].split("?", 1)[0]
    for rx, repl in PLACEHOLDERS:
        path = rx.sub(repl, path)
    parts = [p for p in path.split("/") if p]
    if not parts:
        return "/"
    return "/" + "/".join(parts[:depth]) + ("/..." if len(parts) > depth else "")


def cluster(args):
    raw = read_json(args.report)
    # `pagination` is a sibling of `data`, so read it before unwrapping.
    pagination = (raw.get("pagination") if isinstance(raw, dict) else None) or {}
    payload = unwrap(raw)
    if isinstance(payload, dict) and payload.get("pagination"):
        pagination = payload["pagination"]
    rows = payload if isinstance(payload, list) else payload.get("rows", payload.get("data", []))
    urls = [r["page"] for r in rows if isinstance(r, dict) and r.get("page")]
    # Group reports (title-duplicates, description-duplicates) have no `page` on a row:
    # a row is one shared value plus the `pages` carrying it, and those pages are the
    # clustering evidence. `pagination.total` then counts groups, not pages.
    groups = None
    if not urls:
        groups = [r for r in rows if isinstance(r, dict) and isinstance(r.get("pages"), list)]
        urls = [u for r in groups for u in r["pages"] if isinstance(u, str) and u]
    if not urls:
        print("No `page` field in these rows - this report's rows are not pages. "
              "Check its `columns` before planning it as a page fix.")
        return

    label = args.label or "report"
    if groups:
        groups_total = pagination.get("total") or len(groups)
        total = len(urls)
        print(f"{label}: {len(urls)} pages in {len(groups)} groups fetched of {groups_total} groups"
              f"{'  (the rest were not fetched - page with limit/offset)' if groups_total > len(groups) else ''}\n")
    else:
        total = pagination.get("total") or len(urls)
        print(f"{label}: {len(urls)} rows fetched of {total} total"
              f"{'  (the rest were not fetched - page with limit/offset)' if total > len(urls) else ''}\n")
    counts = Counter(pattern_of(u, args.depth) for u in urls)
    top = counts.most_common(max(args.limit, 1))
    for pat, n in top:
        share = 100.0 * n / len(urls)
        print(f"{n:>5}  {share:>5.1f}%  {pat}")

    head_share = 100.0 * top[0][1] / len(urls) if top else 0

    # One bucket holding almost everything says only that the whole site lives under
    # one prefix. Verified on a wiki: 99% under /{lang}/wiki/... hid that 97% of the
    # redirect targets were /{lang}/wiki/images/... - the actual fix. Go one segment
    # deeper while a single pattern still holds the threshold share.
    # The deeper pattern only has to keep most of its parent, not 90% of all rows: on a wiki,
    # /wiki/... held 93% and /wiki/images/... 89%, and a fixed 90% bar stopped one level short
    # of the real fix.
    depth = args.depth
    go_deeper = head_share >= 90
    while go_deeper and top and top[0][0].endswith("/..."):
        deeper = Counter(pattern_of(u, depth + 1) for u in urls).most_common(max(args.limit, 1))
        deeper_share = 100.0 * deeper[0][1] / len(urls)
        if deeper_share < max(args.threshold, 0.85 * head_share):
            break
        depth, top, head_share = depth + 1, deeper, deeper_share
        print(f"\nOne segment deeper (depth {depth}):")
        for pat, n in top:
            print(f"{n:>5}  {100.0 * n / len(urls):>5.1f}%  {pat}")

    # The other direction: at depth 2, `/services/{slug}` is seven one-row patterns and
    # the section they share is invisible. Show one segment shallower when that reveals it
    # (display only: the verdict below still rests on the depth asked for).
    if head_share < args.threshold and depth > 1:
        shallow = Counter(pattern_of(u, depth - 1) for u in urls).most_common(max(args.limit, 1))
        shallow_share = 100.0 * shallow[0][1] / len(urls)
        if shallow_share >= args.threshold:
            print(f"\nOne segment shallower (depth {depth - 1}):")
            for pat, n in shallow:
                print(f"{n:>5}  {100.0 * n / len(urls):>5.1f}%  {pat}")

    # Query strings are not part of the path pattern above. A `?page=N` family is a
    # crawler trap, not a page type (27,513 "medium response" pages on one site).
    queries = Counter()
    for u in urls:
        if "?" in u:
            qs = u.split("?", 1)[1].split("#", 1)[0].replace("&amp;", "&")
            keys = sorted({k for k, _ in parse_qsl(qs, keep_blank_values=True)})
            queries["?" + "&".join(k + "=" for k in keys)] += 1
    if queries:
        with_query = sum(queries.values())
        print(f"\nQuery parameters: {with_query} of {len(urls)} URLs carry a query string")
        for pat, n in queries.most_common(3):
            print(f"{n:>5}  {100.0 * n / len(urls):>5.1f}%  {pat}")
        if 100.0 * with_query / len(urls) >= args.threshold:
            print("QUERY-STRING PATTERN: most of these URLs differ only by parameters. A")
            print("            crawler trap (?page=N, filters) is not a page type. Open a few")
            print("            of the URLs before planning anything on this report.")

    # Sub-types, when the report carries them. Each key is a different edit.
    # `filters` sits next to `data` in get_report, so read it from the raw result as well.
    filters = ((payload.get("filters") if isinstance(payload, dict) else None)
               or (raw.get("filters") if isinstance(raw, dict) else None))
    if isinstance(filters, dict) and any(filters.values()):
        print("\nSub-types - each of these is a different edit:")
        for key, n in sorted(filters.items(), key=lambda kv: -kv[1]):
            if n:
                print(f"{n:>5}  {key}")

    # Signal 2: the flagged value itself.
    #
    # Careful here. Distinct values are NOT evidence of hand-writing: a template
    # with a variable slot produces a different value on every page. Verified on a
    # live glossary section, where most of the indexable set was flagged for a short
    # H1 and every H1 was a different term - all of them generated from one field.
    # What distinct values rule out is only the narrowest case, a single constant
    # string.
    # Strings only. A numeric row value is a measurement - a click depth, a
    # paragraph count - and three distinct depths across thirty rows says nothing
    # about templates. Before this filter, `pages-with-high-page-depth` reported
    # "one string" because its values were 6, 5 and 4.
    # URLs too: any two URLs on one host share the shape `w://w.w/w/w`, so a report whose
    # value is a link target (canonical-link-target-problems) read as "one string".
    values = [v for v in (value_of(r) for r in rows)
              if isinstance(v, str) and v.strip() and not re.match(r"https?://", v)]
    shape_share = 0.0
    if values:
        shapes = Counter(shape_of(v) for v in values)
        distinct = len(set(map(str, values)))
        shape_share = 100.0 * shapes.most_common(1)[0][1] / len(values)
        print(f"\nFlagged values: {distinct} distinct across {len(values)} rows, "
              f"{len(shapes)} shapes, largest {shape_share:.0f}%")
        for v in list(dict.fromkeys(map(str, values)))[:3]:
            print(f"   e.g. {str(v)[:70]}")

        # An HTML entity in a value the reader sees - a title showing "&amp;" in the
        # search result. Found by eye in 11 of 100 titles on a wiki, inside a report
        # about something else entirely; nothing in the audit flags it.
        entity = [v for v in values if re.search(r"&(amp|quot|lt|gt|#\d+);", v)]
        if entity:
            print(f"\nVISIBLE HTML ENTITY in {len(entity)} of {len(values)} values - shown as")
            print("   code in the search result. A quick fix of its own, plan it:")
            for v in entity[:3]:
                print(f"   e.g. {v[:70]}")

    # The words a keyword-match report marks as missing come back in **bold** in
    # `formatted`. Count them: on a wiki, 159 "title words not in the text" were
    # almost all title frame words ("Definition", "explained", "Best Practices"),
    # which the Help Center says usually need no change.
    missing = Counter()
    for r in rows:
        for item in r.get("items") or []:
            ft = item.get("formatted_text")
            if isinstance(ft, dict) and "**" in (ft.get("formatted") or ""):
                missing.update(w.lower() for w in re.findall(r"\*\*(.+?)\*\*", ft["formatted"])
                               if w.lower() not in {"amp", "quot", "lt", "gt"})
    if missing and label in BOLD_IS_REPEAT:
        print("\nWords repeated in the title (bold in the report) - read these before planning:")
        for w, n in missing.most_common(8):
            print(f"{n:>5}  {w}")
        print("   The same word in many titles is usually the template (brand, section name):")
        print("   one template edit, not one edit per page.")
    elif missing:
        print("\nWords marked as missing (bold in the report) - read these before planning:")
        for w, n in missing.most_common(8):
            print(f"{n:>5}  {w}")
        print("   Frame words the title adds to every page (definition, explained, tips)")
        print("   usually need nothing. Topic words missing from the text are the real edits.")

    # Rows that are link targets have no reach: their count is targets, not pages.
    if label in TARGET_ROWS:
        print()
        if head_share >= args.threshold:
            print(f"ONE RULE: {head_share:.0f}% of the fetched targets share one path pattern.")
            print("            The links are built by one template or one setting - fix it")
            print("            there, once, instead of repointing link by link. Check the")
            print("            second pattern too: each distinct pattern is one change.")
        else:
            print("MIXED TARGETS: no pattern dominates. Plan it as repoints, one pair per")
            print("            target (bulk). Name the two or three largest patterns anyway.")
        return

    # Signal 3, and the decisive one: how much of the indexable set is affected?
    # A defect on most of the site is not a defect on those pages, it is what the
    # page type does - and that is fixed once, wherever the page type is defined.
    ratio = None
    if args.indexed:
        ratio = 100.0 * total / args.indexed
        print(f"\nReach: {total} of {args.indexed} indexable pages ({ratio:.0f}%)")

    # Reach only promotes a report whose defect can live in a template. Where the
    # missing value is written by a person - an alt text, an anchor, a paragraph -
    # eighty percent of the site affected is eighty percent of the site to write.
    written = (label in WRITTEN_PER_INSTANCE
               or load_matrix().get(label, {}).get("class") == "editorial")

    print()
    if ratio is not None and ratio > 100:
        print(f"COUNT NOT ON THE INDEXABLE SET: {total} findings against {args.indexed} indexable")
        print(f"            pages ({ratio:.0f}%). The report counts URLs that are not indexable")
        print("            (crawler traps, parameter URLs). That is no template verdict: read")
        print("            the URLs and the query parameters above, and pull pages-non-indexable.")
    elif ratio is not None and ratio >= 50 and written:
        print(f"SITE-WIDE, BUT WRITTEN: {ratio:.0f}% of the indexable set is affected, and")
        print("            the fix is a value someone writes per instance. Reach does not")
        print("            make this one change. Plan it per page - unless the flagged")
        print("            element repeats on every page (a logo, an icon, a footer link),")
        print("            which is one template edit. Check two affected pages to tell.")
    elif ratio is not None and ratio >= 50:
        print(f"SYSTEMATIC: {ratio:.0f}% of the indexable set is affected. This is not a")
        print("            defect on these pages, it is what this page type does. Fix it")
        print("            where the page type is defined - one change, whatever the")
        print("            individual values look like.")
    elif shape_share >= args.threshold and len(values) >= 5:
        print("ONE STRING: the flagged values share a constant frame. Whatever emits it")
        print("            is a single template expression.")
    elif head_share >= args.threshold:
        print(f"SCOPED TEMPLATE: {head_share:.0f}% of the fetched rows sit under one path")
        print("            pattern. One change to that section's template covers them.")
    elif ratio is not None and ratio <= 10 and len(set(values)) > 2:
        print("PER PAGE: a small share of the site, and the values vary. No single change")
        print("          covers these - plan them as individual edits.")
    else:
        print("UNCLEAR from the crawl data. Open two or three of the affected pages and")
        print("         one unaffected page of the same type and compare the markup. If")
        print("         that is not possible, assume the per-page cost, plan it that way,")
        print("         and tell the user the plan rests on that assumption.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("rank", help="score the issue reports into a plan order")
    r.add_argument("problems", help="saved get_site_audit_problems payload, or - for stdin")
    r.add_argument("--no-baseline", action="store_true",
                   help="ignore deltas: the previous crawl was stopped, empty or not comparable. "
                        "Switches off NEW and RE-MEASURE.")
    r.add_argument("--indexed", type=int, default=0,
                   help="pages_indexable from list_crawls - enables the coverage check")
    r.add_argument("--limit", type=int, default=15)
    r.add_argument("--assume", action="append", metavar="REPORT=CLASS",
                   help="override an effort class with what the user tells you about "
                        "their site, e.g. --assume heading-h1-problems=template. "
                        "Repeatable. The user's answer always beats the table.")
    r.add_argument("--json", help="also write the scored rows to this file")
    r.set_defaults(func=rank)

    c = sub.add_parser("cluster", help="group one report's URLs by path pattern")
    c.add_argument("report", help="saved get_report payload, or - for stdin")
    c.add_argument("--label", help="the report's analysis slug - used for the heading and to "
                                   "keep written-per-instance reports out of the reach promotion")
    c.add_argument("--depth", type=int, default=2, help="path segments to keep (default 2)")
    c.add_argument("--limit", type=int, default=8)
    c.add_argument("--indexed", type=int, default=0,
                   help="pages_indexable from list_crawls - enables the reach "
                        "test, which is the decisive signal")
    c.add_argument("--threshold", type=float, default=60.0,
                   help="share of rows in one pattern or shape that counts as generated")
    c.set_defaults(func=cluster)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
