#!/usr/bin/env python3
"""Turn a saved Seobility `get_report` payload into ticket units.

A report is not a ticket. One report holds several different defects, each needing a different
fix, and the affected URL is not always the row's `page` field. This script does the three
mechanical parts of that split so the model never has to read a large payload:

    1. group the rows by defect key (`problems[].name`), including rows carrying several keys
    2. resolve which URL each row is actually about (see ROLE below)
    3. cap the URL list, deduplicate it, and state how much of the total it covers

Usage:
    python tickets.py <saved-report.json> [<page-2.json> ...] --analysis title-problems
                      [--limit 10] [--host www.example.com] [--defect h1_toshort]
                      [--anchor "read more"] [--json]
                      [--out-dir tickets/] [--id SEO-01] [--crawl 2026-09-18]

Pass `-` instead of a path to read one payload from stdin. Pass several files to merge the
pages of one report fetched with `limit` and `offset`.

ROLE — which URL the ticket names. Pass --analysis: on reports with a `pages[]` list the role
depends on the report, and two reports with the SAME row shape have OPPOSITE roles (verified):

    on-page reports            rows[].page    is the affected page
    external link reports      rows[].page    is the link TARGET, often a foreign domain;
                               items[].page   is the own page carrying the link
    redirect link reports      pages[]        are the own pages containing the link
    title/description dupes    pages[]        are the pages sharing the text: edit these
    anchor text duplicates     pages[]        are link TARGETS; the pages carrying the anchor
                                              are not in the payload at all

For reports not in ROLES the script falls back to the host test: a row whose `page` sits
outside the project's site (subdomains count as the site) is a target. A row with no `page` and
a `pages[]` list is flagged as unverified, not guessed.

FINDINGS ARE NOT PAGES. The `filters` count counts findings, not affected pages: three broken
outbound links can sit on two pages, and on one verified report they did. Both numbers are
printed, and the ticket needs both — a developer schedules by pages, a report counts findings.

`get_report` returns 100 rows by default and pages with `limit` and `offset` (offset a multiple
of limit). A payload that stops short of the report is flagged per run, with the offset of the next
page. Never present a partial URL list as complete.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict, defaultdict
from urllib.parse import urlparse

# Windows consoles default to cp1252 and choke on umlauts and box glyphs.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NO_DEFECT = "_report"  # reports with `filters: []` carry no defect keys; the report is the unit

# Verified roles for rows that carry a `pages[]` list. The row shape alone does not decide it:
# description-duplicates and link-anchor-text-duplicates-for-different-pages both return
# {items: [text], pages: [...]} with no `page`, and the lists mean opposite things.
EDIT_PAGES = "pages[] (pages to edit)"
TARGETS_ONLY = "pages[] (link targets; linking pages not in payload)"
UNVERIFIED = "pages[] (role unverified for this report: look at one row)"
ROLES = {
    "internal-link-targets-on-redirects": EDIT_PAGES,
    "redirect-target-problems": EDIT_PAGES,
    "title-duplicates": EDIT_PAGES,
    "description-duplicates": EDIT_PAGES,
    "link-anchor-text-duplicates-for-different-pages": TARGETS_ONLY,
}

# Reports whose rows are redirecting URLs. When those URLs share one path pattern, the links are
# generated - one template or setting builds them - and the ticket is that one change, not a list
# of linking pages. Verified on a wiki (24.09.2026): 375 targets were the home link with a
# trailing slash plus article images on an old image path, two tickets instead of 375 repoints.
# Same rule as `seobility-audit-triage` (`internal-link-targets-on-redirects` is a `~` row there).
PATTERN_REPORTS = {"internal-link-targets-on-redirects"}
# Reports with one row per anchor text: each anchor text is a unit (`--anchor` picks one).
PER_ANCHOR = {"link-anchor-text-duplicates-for-different-pages"}
# Reports whose `rows[].page` is a foreign link target and whose own page is `items[].page`.
OWN_IN_ITEMS = {"external-link-target-problems"}
LANG = re.compile(r"^/(?:[a-z]{2})(?:-[a-z]{2})?(?=/)", re.I)


def pattern_of(url, depth):
    path = LANG.sub("/{lang}", urlparse(url).path or "/")
    path = re.sub(r"/\d+(?=/|$)", "/{n}", path)
    parts = [p for p in path.split("/") if p]
    return "/" + "/".join(parts[:depth]) + ("/..." if len(parts) > depth else "")


def target_patterns(rows, depth=2):
    """Path patterns of the redirecting URLs, one segment deeper while one pattern holds >= 90%."""
    urls = [r["page"] for r in rows if isinstance(r.get("page"), str)]
    if not urls:
        return [], 0.0
    top = Counter(pattern_of(u, depth) for u in urls).most_common(5)
    share = 100.0 * top[0][1] / len(urls)
    while share >= 90 and top[0][0].endswith("/..."):
        deeper = Counter(pattern_of(u, depth + 1) for u in urls).most_common(5)
        deeper_share = 100.0 * deeper[0][1] / len(urls)
        if deeper_share < 90:
            break
        depth, top, share = depth + 1, deeper, deeper_share
    return [(p, n, round(100.0 * n / len(urls), 1)) for p, n in top], share


def load(path):
    if path == "-":
        payload = json.load(sys.stdin)
    else:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    data = payload.get("data", payload) if isinstance(payload, dict) else None
    rows = data.get("rows") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        sys.exit("Unexpected payload: expected 'rows' under 'data'. Is this a get_report result?")
    pagination = payload.get("pagination", data.get("pagination", {})) or {}
    return rows, data.get("filters"), pagination


def load_all(paths):
    """One payload, or the pages of one report merged. Pagination is the last page's."""
    rows, filters, pagination, last_rows = [], None, {}, 0
    for path in paths:
        page_rows, page_filters, page_pagination = load(path)
        rows.extend(page_rows)
        last_rows = len(page_rows)
        if filters in (None, []) or (isinstance(filters, dict) and not any(filters.values())):
            filters = page_filters
        if page_pagination.get("offset", 0) >= pagination.get("offset", 0):
            pagination = dict(page_pagination, rows_on_page=last_rows)
    return rows, filters, pagination


def filter_counts(filters):
    """`filters` is a {key: count} map on most reports and an empty LIST on some. Both are valid."""
    if isinstance(filters, dict):
        return {k: v for k, v in filters.items() if v}
    return {}


def plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def host_of(url):
    try:
        host = (urlparse(url).netloc or "").lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def same_site(host, own):
    """A subdomain counts as the project's site (contest.example.com under example.com).

    Verified: a 404 on the main site was linked only from a subdomain the project also crawls.
    That linking page is still the site's own, even if another team runs it.
    """
    return bool(host) and (host == own or host.endswith("." + own) or own.endswith("." + host))


def own_host(rows, override=None, analysis=""):
    """The project's own host: whatever most URLs in the payload agree on.

    On external-link reports every row is one foreign target plus one own page, so a plain
    vote ties and the first foreign host won. There only `items[].page` is the site's own.
    """
    if override:
        return host_of(override) or host_of("//" + override)
    seen = Counter()
    for row in rows:
        urls = ([i.get("page") for i in row.get("items") or [] if i.get("type") == "page"]
                if analysis in OWN_IN_ITEMS else urls_in(row))
        for url in (u for u in urls if isinstance(u, str)):
            host = host_of(url)
            if host:
                seen[host] += 1
    return seen.most_common(1)[0][0] if seen else ""


def urls_in(row):
    out = [row.get("page")]
    out.extend(row.get("pages") or [])
    for item in row.get("items") or []:
        if item.get("type") == "page":
            out.append(item.get("page"))
    return [u for u in out if isinstance(u, str)]


def target_urls(row, host, analysis):
    """The URLs a ticket names, and the role they came from."""
    pages = [u for u in (row.get("pages") or []) if isinstance(u, str)]
    if pages:
        if analysis in ROLES:
            return pages, ROLES[analysis]
        if isinstance(row.get("page"), str):
            return pages, EDIT_PAGES  # the redirect shape: page + items + pages[]
        return pages, UNVERIFIED

    page = row.get("page")
    item_pages = [i.get("page") for i in (row.get("items") or [])
                  if i.get("type") == "page" and isinstance(i.get("page"), str)]

    if isinstance(page, str) and host and not same_site(host_of(page), host) and item_pages:
        return item_pages, "items[].page"
    if isinstance(page, str):
        return [page], "rows[].page"
    return item_pages, "items[].page"


def evidence(row):
    """The current value and the threshold the tool judged it against, if the row carries them.

    Item shapes verified: `formatted_text` (the current title/H1/text), `number` (the value sits
    under a key NAMED by the item's own `key` field, e.g. `statuscode`), `filesize` (a
    {size, unit} object), `typo` (a list of misspelled/correction pairs; the row's `text` item
    only carries the language code) and `page` (handled as a URL role, not as evidence).
    """
    out = {}
    for item in row.get("items") or []:
        if item.get("type") == "typo":
            pairs = [f"{t.get('misspelled')} -> {t.get('correction')}"
                     for t in item.get("typos") or []]
            if pairs:
                out["value"] = "; ".join(pairs)  # replaces the language code taken from `text`
            continue
        text = (item.get("formatted_text") or {}).get("raw")
        if not text and item.get("type") == "text":
            text = item.get("text")  # anchor text, duplicated title or description
        if text and "value" not in out:
            out["value"] = text
        if item.get("type") == "number":
            key = item.get("key")
            if key in item and "value" not in out:
                out["value"] = f"{key}: {item[key]}"
        if item.get("type") == "filesize" and "value" not in out:
            size = item.get("filesize") or {}
            if size.get("size") is not None:
                out["value"] = f"{size['size']} {size.get('unit') or ''}".strip()
        for key, val in (item.get("properties") or {}).items():
            out.setdefault(key, val)
    return out


def defects_of(row, analysis=""):
    names = [p.get("name") for p in (row.get("problems") or []) if p.get("name")]
    if not names and analysis in PER_ANCHOR:
        # One row per anchor text and no defect keys: each anchor is its own unit, so a ticket
        # or URL file can be written for one anchor group instead of the whole report.
        texts = [i.get("text") for i in (row.get("items") or [])
                 if i.get("type") == "text" and i.get("text")]
        if texts:
            return [texts[0]]
    return names or [NO_DEFECT]


def inside_limits(ev):
    """True when the row's measured values sit inside every limit it carries, False when one
    is outside, None when it carries no limit. A title inside the character limits can still
    break the pixel limits."""
    inside = None
    for kind in ("character_length", "pixel_length"):
        got = ev.get(kind + "_calculated")
        lo, hi = ev.get(kind + "_min"), ev.get(kind + "_max")
        if got is not None and (lo is not None or hi is not None):
            if (lo is not None and got < lo) or (hi is not None and got > hi):
                return False
            inside = True
    return inside


def group(rows, host, analysis):
    units = defaultdict(lambda: {"rows": 0, "urls": OrderedDict(), "roles": Counter(),
                                 "values": [], "props": {}, "detail": Counter(), "inside": 0})
    for row in rows:
        urls, role = target_urls(row, host, analysis)
        ev = evidence(row)
        if inside_limits(ev):
            for defect in defects_of(row, analysis):
                units[defect]["inside"] += 1
        for defect in defects_of(row, analysis):
            unit = units[defect]
            unit["rows"] += 1
            unit["roles"][role] += 1
            for url in urls:
                unit["urls"].setdefault(url, None)
            for prop, val in ev.items():
                if prop == "value":
                    if len(unit["values"]) < 5:
                        unit["values"].append(val)
                else:
                    unit["props"].setdefault(prop, val)
        for problem in row.get("problems") or []:
            if problem.get("name") and problem.get("value") is not None:
                units[problem["name"]]["detail"][str(problem["value"])] += 1
    return units


def threshold_line(unit):
    """Rebuild the tool's own rule, e.g. 'character_length 20-120' — only when it IS the rule.

    Every title row carries the pixel limits, whatever its defect. Verified: 15 of 17
    `title_wordrepeats` rows sat inside them. A limit the rows do not break is not the
    acceptance criterion for that defect, and printing it as one invents a criterion.
    """
    props = unit["props"]
    out = [f"{kind} {props.get(kind + '_min')}-{props.get(kind + '_max')}"
           for kind in ("character_length", "pixel_length")
           if props.get(kind + "_min") is not None or props.get(kind + "_max") is not None]
    if not out:
        return ""
    if unit["inside"]:
        return (f"none for this defect ({unit['inside']} of {unit['rows']} rows are inside "
                f"{'; '.join(out)})")
    return "; ".join(out)


def write_url_file(out_dir, ticket_id, analysis, defect, urls, affected, retrieved, crawl,
                   role="", taken=None):
    """One file per unit. With --id it is named after the ticket (SEO-01-urls.txt), which is
    what the ticket's Scope line references; without, after the report and defect key.

    `taken` holds the names already written in this run, compared case-insensitively (macOS and
    Windows): "read more" and "read-more!" reduce to the same name and must not overwrite."""
    os.makedirs(out_dir, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9]+", "-", ticket_id or f"{analysis}-{defect}").strip("-")
    name, n = stem + "-urls.txt", 1
    while taken is not None and name.lower() in taken:
        n += 1
        name = f"{stem}-{n}-urls.txt"
    if taken is not None:
        taken.add(name.lower())
    path = os.path.join(out_dir, name)
    with open(path, "w", encoding="utf-8") as fh:
        head = " · ".join(x for x in (ticket_id, f"{analysis} / {defect}",
                                      f"crawl {crawl}" if crawl else "") if x)
        fh.write(f"# {head}\n")
        fh.write(f"# {plural(affected, 'finding')}, {plural(retrieved, 'URL')} retrieved\n")
        if role == TARGETS_ONLY:
            fh.write("# link targets, not the pages to edit: get_page_incoming_links(target) "
                     "lists the linking pages\n")
        fh.write("\n".join(urls) + "\n")
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", metavar="path",
                    help="saved get_report payload (JSON); `-` reads stdin; several files are "
                         "the pages of one report, merged")
    ap.add_argument("--analysis", default="report",
                    help="the report slug; decides the URL role on reports with pages[]")
    ap.add_argument("--limit", type=int, default=10, help="URLs shown per unit (default 10)")
    ap.add_argument("--host", help="the project's own host, if the payload is ambiguous")
    ap.add_argument("--defect", help="only this defect key")
    ap.add_argument("--anchor", help="only this anchor text (anchor-duplicate reports), "
                                     "case-insensitive")
    ap.add_argument("--crawl", help="crawl date, written into the URL files")
    ap.add_argument("--out-dir", help="write one full URL list per unit into this folder")
    ap.add_argument("--id", help="ticket id for the URL file name, e.g. SEO-01 (with --defect)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()
    if args.id and not (args.defect or args.anchor):
        ap.error("--id names one ticket's URL file: use it with --defect or --anchor")

    rows, filters, pagination = load_all(args.paths)
    host = own_host(rows, args.host, args.analysis)
    counts = filter_counts(filters)
    units = group(rows, host, args.analysis)

    total = pagination.get("total") or len(rows)
    limit = pagination.get("limit", 100) or 100
    # `total` is NOT always a row count: on grouped reports (one row per anchor text, per
    # duplicate set) it counts the pages behind the groups, so total > len(rows) proves nothing.
    # A full last page with more still ahead of it is the only reliable sign that rows were
    # withheld; a short page is the last one, whatever `limit` the caller used.
    offset = pagination.get("offset", 0) or 0
    capped = pagination.get("rows_on_page", len(rows)) >= limit and offset + limit < total

    out, taken = [], set()
    for defect, unit in sorted(units.items(), key=lambda kv: -len(kv[1]["urls"])):
        wanted = args.anchor or args.defect
        if wanted and defect.casefold() != wanted.casefold():
            continue
        urls = list(unit["urls"])
        # `filters` counts findings across the whole report; the rows in hand may be fewer
        # (capped report) and the pages are fewer still whenever one page carries several.
        findings_total = counts.get(defect, unit["rows"])
        roles = unit["roles"].most_common()
        out.append({
            "defect": defect,
            "findings_in_report": findings_total,
            "findings_in_payload": unit["rows"],
            "pages_retrieved": len(urls),
            # Capped for THIS defect: the report holds more findings of it than the payload does.
            "incomplete": findings_total > unit["rows"],
            "report_capped": capped,
            "url_role": "; ".join(f"{r} ({n})" for r, n in roles) if len(roles) > 1
                        else (roles[0][0] if roles else ""),
            "threshold": threshold_line(unit),
            "examples": unit["values"][:3],
            "values": dict(unit["detail"].most_common(5)) or None,
            "urls": urls[:args.limit],
        })
        if args.out_dir:
            out[-1]["url_file"] = write_url_file(args.out_dir, args.id, args.analysis, defect,
                                                 urls,
                                                 findings_total, len(urls), args.crawl or "",
                                                 out[-1]["url_role"], taken)

    patterns, head_share = (target_patterns(rows) if args.analysis in PATTERN_REPORTS
                            else ([], 0.0))

    if args.json:
        print(json.dumps({"analysis": args.analysis, "own_host": host,
                          "rows_in_payload": len(rows), "pagination_total": total,
                          "rows_limit": limit,
                          "report_capped": capped,
                          "next_offset": offset + limit if capped else None,
                          "target_patterns": patterns or None,
                          "one_rule": bool(patterns) and head_share >= 60,
                          "units": out},
                         ensure_ascii=False, indent=2))
        return

    print(f"{args.analysis} · own host: {host or 'unknown'} · "
          f"{len(rows)} rows in payload, pagination.total {total}"
          f"{f'  ← PARTIAL: more rows follow, fetch offset={offset + limit} (limit {limit}) and pass both files' if capped else ''}")
    if not capped and total > len(rows):
        print(f"pagination.total ({total}) is larger than the rows ({len(rows)}) although the "
              f"page size was not reached — on this report `total` is not a row count. Verified "
              f"cause: rows that group several pages. Count rows, not total.")
    if patterns:
        print("redirect targets by path pattern:")
        for pat, n, share in patterns:
            print(f"  {n:>5}  {share:>5.1f}%  {pat}")
        if head_share >= 60:
            print(f"ONE RULE: {head_share:.0f}% of the targets share one pattern. The links are "
                  f"generated: one ticket per pattern, about where the links are built "
                  f"(fix type template or config), with a few linking pages as examples - not a "
                  f"repoint list.")
        else:
            print("MIXED TARGETS: no pattern dominates. One search-and-replace pair per target "
                  "(fix type bulk).")
        print()
    zeros = [k for k, v in (filters or {}).items() if not v] if isinstance(filters, dict) else []
    if zeros:
        print(f"clean defect keys (count 0): {', '.join(zeros)}")
    print()

    for unit in out:
        head = f"[{unit['defect']}] {plural(unit['findings_in_report'], 'finding')}"
        if unit["incomplete"]:
            # How many pages sit behind the missing findings is unknown, so print no page count.
            head += (f", {unit['findings_in_payload']} of them in this payload "
                     f"({plural(unit['pages_retrieved'], 'URL')})  ← "
                     + ("rows missing: fetch the next page(s) with offset" if capped else
                        "the report counts findings per row or target, so this is expected; "
                        "no further page exists"))
        elif unit["url_role"] == TARGETS_ONLY:
            head += f" · {plural(unit['pages_retrieved'], 'link target')}, linking pages unknown"
        elif unit["findings_in_report"] != unit["pages_retrieved"]:
            head += f" on {plural(unit['pages_retrieved'], 'page')}"
        print(head)
        print(f"    URL role: {unit['url_role']}")
        if unit["url_role"] == TARGETS_ONLY:
            print("    next:      get_page_incoming_links(target) per target; the linking pages "
                  "are the ones whose anchor_texts match")
        if unit["threshold"]:
            print(f"    threshold: {unit['threshold']}")
        if unit["examples"]:
            print(f"    examples:  {' | '.join(str(e) for e in unit['examples'])}")
        if unit["values"]:
            print(f"    values:    {unit['values']}")
        if unit.get("url_file"):
            print(f"    full list: {unit['url_file']}")
        for url in unit["urls"]:
            print(f"      {url}")
        if unit["pages_retrieved"] > len(unit["urls"]):
            print(f"      … {unit['pages_retrieved'] - len(unit['urls'])} more retrieved")
        print()


if __name__ == "__main__":
    main()
