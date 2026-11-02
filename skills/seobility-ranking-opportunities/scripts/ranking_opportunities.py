#!/usr/bin/env python3
"""Screen the ranking opportunities in a Seobility `list_keywords` payload and pick the candidates.

`list_keywords` overflows the tool-result limit on any real project, so the MCP client writes it
to a file. This script reads that file and returns only what the report needs, so the full payload
never enters the context window. Pass `-` as the path to read the payload from stdin.

Usage:
    python ranking_opportunities.py <saved-file|-> --screen [--top 10] [--scope https://example.com/de/]
    python ranking_opportunities.py <saved-file|-> [--top 3] [--market Google.de] [--since 2026-09-22] [--csv]
                         [--skip <keyword_id>,<keyword_id>] [--scope https://example.com/de/]
    python ranking_opportunities.py --serp <saved get_keyword_rankings file|-> [--expect-rank 7] [--rows 3]
    python ranking_opportunities.py --promise <url> <url> <url>

Candidates are the organic rows at positions 4-20. The next milestone depends on the position:
the top 3 for 4-10 (distance = rank - 3), page 1 for 11-20 (distance = rank - 10). Rows are ordered
by log10(search_volume) / distance. The volume is damped
on purpose: an undamped volume/distance score is dominated by raw volume, so the top of the list
becomes "the biggest terms you happen to rank for" - the opposite of a quick win. Damped, closeness
decides the order and volume modulates it. A volume of 0 or none is a data gap, not proof that nobody
searches: it is shown as "<10" and counted as 5 in the order. No row is dropped or gated for low volume.

Before a row can be picked it passes the ranking-data gate: rows that moved 30 or more places in one
check are suspect and are listed, not picked. A "new" row (no position in the previous check) is not
suspect by itself: on a long-tracked project it is usually a re-entry. It sorts after rows with a
previous position and is only used once its SERP passes the gate. `list_keywords` carries no `date_added`; `--since` only acts on payloads that
do. They are listed, not picked; so are the ids passed with `--skip` (picks that failed the SERP gate), which
frees their URL for the next candidate. Head terms (volume at or above the head-term threshold) are listed, not picked.
One pick per ranking URL; the other keywords that URL ranks for are printed with the pick. A row
whose URL holds a better position for another keyword ranks after every clean row. With `--scope`
(the project URL), a row whose ranking URL lies outside the crawl ranks after every row inside it:
the skill cannot read that page. The exception is the same site in another language than the
market's (the /en/ page on Google.de): such a row stays a normal candidate, and the screen finds the
market's version through the ranking page's hreflang links and checks that version instead.

The ordering is a sorting device and is never shown as a number. It is not a traffic estimate.

When three or more tracked keywords rank with a page other than the one built for them (another city's page,
a tool page, a reference page), the output ends with one "Worth knowing" line. It is a side note for
the report, never a row and never an opportunity.

`--screen` is the first pass of the skill: it takes the top candidates (10 by default), fetches each
candidate's own ranking page once (free, ~1 kB each) and flags what can already be seen there: a
status other than 200, a redirect, noindex, a canonical pointing elsewhere, the keyword missing from
title and H1, an outdated year in title or H1. The order of attractiveness stays: a Tier 1 blocker
(status, redirect, noindex, canonical) comes first, and any other flag only moves a candidate ahead of
neighbours that are about as attractive (within 20%). A flag shared by two or more candidates is
printed as a PATTERN: one change that may fix several pages. The screen decides the order of the
checks. It is not a finding.

`--serp` checks one `get_keyword_rankings` payload against the SERP half of the gate (own URL more
than once, a contiguous "new" block at the top, own position different from `--expect-rank`, three
or more other sites appearing twice) and
prints the top rows above the user, with URLs unescaped so they can be fetched. Local-pack rows are
left out. Another site's URL twice in the top 10 is printed as a note, not as suspect: it says
nothing about the own position. Use it only on a result the host saved as a file,
never on a hand-copied part of an inline result.
"""

import argparse
import csv
import html
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date as _date
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# Windows consoles default to cp1252 and choke on umlauts and box glyphs.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BAND_MIN, BAND_MAX = 4, 20
TOP = 3
SCREEN_TOP = 10        # candidates the first pass screens
THIN_PROJECT = 20      # below this many ranking keywords, the report is thin because the set is
THIN_BAND = 5          # below this many keywords in the band, the report is thin as well
HEAD_TERM_FACTOR = 10  # volume >= this * median volume of all ranking keywords with volume ...
HEAD_TERM_FLOOR = 1000  # ... and never below this many monthly searches
VOLUME_STAND_IN = 5    # a volume of 0 or none is shown as "<10" and counted as this in the order
WRONG_PAGE_MIN = 3     # this many rows on a page built for something else make the side note
GENERIC_SHARE = 0.1    # a keyword word used by this share of the tracked keywords ...
GENERIC_MIN = 3        # ... and by at least this many is generic (the service, not the place)
BIG_MOVE = 30          # a move of this many places in one check is suspect
SERP_NEW = 1000        # `rank_change` value for "new" in get_keyword_rankings rows
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/128.0 Safari/537.36")
NEW_BLOCK = 3          # a contiguous "new" block this long at the top of the SERP is suspect
DOUBLED_MIN = 3       # this many other sites appearing twice: the own position cannot be confirmed
TIE_SHARE = 0.8        # in the screen, candidates within 20% of each other's order value count as close


def load(path):
    if path == "-":
        payload = json.load(sys.stdin)
    else:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    return payload.get("data", payload) if isinstance(payload, dict) else payload


def rank_of(row):
    """`rank` is an int when ranking, and `false` or `null` when not. Both mean 'no position'."""
    rank = row.get("rank")
    return rank if isinstance(rank, int) and not isinstance(rank, bool) else None


def milestone(rank):
    return "top 3" if rank <= 10 else "page 1"


def distance(rank):
    """Distance to the next milestone: the top 3 from 4-10, page 1 from 11-20."""
    return rank - 3 if rank <= 10 else rank - 10


def volume(row):
    return row.get("search_volume") or 0


def vol_str(row):
    """0 or none is a data gap, never "0" or "no searches"."""
    return str(volume(row)) if volume(row) else "<10"


def score(row):
    """Damped opportunity: closeness decides, volume modulates. Ordering only, never displayed.
    A volume of 0 or none counts as VOLUME_STAND_IN, so such rows are neither dropped nor last."""
    return math.log10(max(volume(row), VOLUME_STAND_IN)) / distance(rank_of(row))


def change_str(row):
    """`rank_change` is usually an int, but is the string "new" for a first-time ranking."""
    change = row.get("rank_change")
    if isinstance(change, str):
        return change
    return f"{change or 0:+d}"


def suspect_reasons(row, since, skip=()):
    """The part of the ranking-data gate this payload can answer."""
    reasons = ["failed the SERP gate"] if str(row.get("id")) in skip else []
    change = row.get("rank_change")
    if isinstance(change, int) and change != SERP_NEW and abs(change) >= BIG_MOVE:
        reasons.append(f"moved {change:+d} places in one check")
    added = row.get("date_added")
    if since and added and str(added)[:10] >= since:
        reasons.append(f"added {str(added)[:10]}, inside the window")
    return reasons


LANG_SEGMENT = re.compile(r"^[a-z]{2}([-_][a-zA-Z]{2})?$")


def is_first(row):
    """No position in the previous check: a first ranking or a re-entry."""
    change = row.get("rank_change")
    return change == "new" or change == SERP_NEW


def norm(url):
    """Compare URLs without scheme and www."""
    u = (url or "").lower().split("://", 1)[-1]
    return u[4:] if u.startswith("www.") else u


START_PAGES = {"hauptseite", "main_page", "startseite", "start", "home", "index", "pagina_principal", "inicio"}


def scope_root(scope):
    """The project URL is often a start page (/de/wiki/start): its folder is the scope."""
    root = norm(scope)
    if "/" in root and not root.endswith("/"):
        head, last = root.rsplit("/", 1)
        if last.endswith((".html", ".htm", ".php", ".asp", ".aspx")) or last in START_PAGES:
            root = head + "/"
    return root.rstrip("/")


def in_scope(row, scope):
    # Whole path segments only: scope /de must not take in /demo/, nor example.com example.community.
    if not scope:
        return True
    url, root = norm(row.get("best_ranking_url")), scope_root(scope)
    return url.rstrip("/") == root or url.startswith(root + "/")


# Language a market's searchers expect, from the search engine's domain.
MARKET_LANG = {"de": "de", "at": "de", "ch": "de", "es": "es", "com.mx": "es", "fr": "fr", "it": "it",
               "nl": "nl", "pl": "pl", "pt": "pt", "com.br": "pt", "com": "en", "co.uk": "en", "ie": "en",
               "com.au": "en", "ca": "en"}


def lang_of(url):
    """Language segment of a URL (/de/, /en-us/), or None."""
    u = url or ""
    parts = [p for p in urlparse(u if "://" in u else "https://" + u).path.split("/") if p]
    return parts[0].lower()[:2] if parts and LANG_SEGMENT.match(parts[0]) else None


def market_lang(row):
    name = (row.get("search_engine_name") or "").lower()
    return MARKET_LANG.get(name.split("google.", 1)[1]) if "google." in name else None


def site_of(url):
    return norm(url).split("/", 1)[0]


def twin_lang(row, scope):
    """The language of the page that should rank for this row: the market's, else the scope's."""
    scope_lang = lang_of(scope_root(scope)) if scope else None
    want = market_lang(row) or scope_lang
    return want if want and (not scope_lang or want == scope_lang) else None


def twin_candidate(row, scope):
    """The ranking URL lies outside the crawl, on the same site, in another language than the
    market's (the EN page ranking on Google.de). The page built for this market may well be inside
    the crawl: the screen finds it through the ranking page's hreflang links. Such a row is not
    "outside the crawl", it is a wrong-language candidate (Tier 2)."""
    if not scope or in_scope(row, scope):
        return False
    url = row.get("best_ranking_url") or ""
    want, have = twin_lang(row, scope), lang_of(url)
    return bool(want and have and have != want and site_of(url) == site_of(scope_root(scope)))


def readable(row, scope):
    """Inside the crawl, or a wrong-language row whose twin may be inside it."""
    return in_scope(row, scope) or twin_candidate(row, scope)


def section(url):
    """First path segment, used to find control pages of the same kind. A language segment
    (/de/, /en-us/) says nothing about the page type, so it takes the next segment with it."""
    parts = [p for p in urlparse(url or "").path.split("/") if p]
    if not parts:
        return ""
    if LANG_SEGMENT.match(parts[0]) and len(parts) > 1:
        return parts[0] + "/" + parts[1]
    return parts[0]


def holds_better(row, ranking):
    """The URL ranks better for another keyword, so it must not be re-aimed at this one."""
    return any(rank_of(o) < rank_of(row) for o in same_url(row, ranking))


def same_url(pick, ranking):
    """Other keywords the pick's URL ranks for. The same keyword in another market is not another
    keyword: a better position there says nothing against re-aiming the page."""
    others = [r for r in ranking if r is not pick and r.get("best_ranking_url") == pick.get("best_ranking_url")
              and r.get("name") != pick.get("name")]
    return sorted(others, key=rank_of)


def depth_of(url):
    return len([p for p in urlparse(url or "").path.split("/") if p])


def controls(pick, ranking, own=None):
    """Top-3 pages of the same section, the same URL depth first: a post is compared with posts,
    not with the category page above it. `own` overrides the pick's URL (a wrong-language row is
    compared through its twin)."""
    own = own or pick.get("best_ranking_url")
    sec, depth = section(own), depth_of(own)
    cands = []
    for r in ranking:
        url = r.get("best_ranking_url")
        if rank_of(r) <= 3 and r.get("rank_type") == "organic" and section(url) == sec \
                and url != own and url not in [c[2] for c in cands]:
            cands.append((abs(depth_of(url) - depth), rank_of(r), url))
    return [url for _, _, url in sorted(cands)[:3]]


_SEEN_CONTROLS = []


def emit_pick(i, r, ranking, scope=None):
    print(f"## {i}. {r['name']} - position {rank_of(r)} ({change_str(r)}), next milestone {milestone(rank_of(r))},"
          f" volume {vol_str(r)}")
    print(f"- Ranking URL: {r.get('best_ranking_url') or '-'}")
    if twin_candidate(r, scope):
        print(f"- WRONG LANGUAGE: the {lang_of(r.get('best_ranking_url')).upper()} page ranks on"
              f" {r.get('search_engine_name')}. Run --screen to find its {twin_lang(r, scope).upper()} version.")
    aio = r.get("ai_overview")
    aio_rank = r.get("ai_overview_rank")
    aio_text = f"{aio}" + (f", our position in it: {aio_rank}" if aio and aio_rank else (", we are not cited" if aio else ""))
    print(f"- keyword_id: {r['id']} | market: {r.get('search_engine_name')} | AI Overview: {aio_text}"
          f" | intents: {r.get('intents')}")
    if is_first(r):
        print("- FIRST RANKING since the previous check: use it only once its SERP passes the gate.")
    others = same_url(r, ranking)
    if others:
        better = [o for o in others if rank_of(o) < rank_of(r)]
        print("- Same URL also ranks for: " + "; ".join(
            f"{o['name']} #{rank_of(o)} ({vol_str(o)})" for o in others[:8]))
        if better:
            print("  HOLDS A BETTER POSITION ELSEWHERE - do not retitle or re-aim this URL.")
    ctrl = controls(r, ranking)
    if len(ctrl) >= 2 and ctrl in _SEEN_CONTROLS:
        print("- Controls: the same pages as an earlier pick (same section and page type) - pull them once.")
    elif len(ctrl) >= 2:
        _SEEN_CONTROLS.append(ctrl)
        print(f"- Controls (top 3, same section /{section(r.get('best_ranking_url'))}/): " + ", ".join(ctrl))
    else:
        print(f"- Controls: {len(ctrl)} top-3 page(s) in the same section - no comparison possible"
              + (f" ({ctrl[0]})" if ctrl else ""))
    print()


def path_words(url):
    return set(_words(urlparse(url or "").path))


def slug_words(url):
    """Words of the last path segment: what the page is named for."""
    parts = [p for p in urlparse(url or "").path.split("/") if p]
    return set(_words(parts[-1])) if parts else set()


def page_label(row):
    path = urlparse(row.get("best_ranking_url") or "").path
    return path or row.get("best_ranking_url") or "-"


def wrong_page_rows(ranked, rows, suspect, scope=None):
    """Organic rows on positions 1-20 whose ranking page is not the one built for the keyword. A page is built for a
    keyword when its URL slug is made of the keyword's words and carries all of its distinguishing
    words (those that fewer than GENERIC_SHARE of the tracked keywords use: a place, not the service:
    /locations/leeds/ for "roof repair leeds"). A page whose slug holds only generic words is not
    built for it. The row counts when such a page exists, the ranking URL is another page and its
    path carries none of the distinguishing words (another city's page, a tool page, a reference
    page). Home pages, wrong-language rows and suspect rows are other findings."""
    own_urls = {r["best_ranking_url"] for r in rows if r.get("best_ranking_url")}
    use = Counter(w for r in rows for w in set(_words(r["name"])))
    generic = {w for w, n in use.items() if n >= GENERIC_MIN and n >= GENERIC_SHARE * len(rows)}
    found = []
    for r in ranked:
        url = r.get("best_ranking_url")
        if not url or suspect[r["id"]] or twin_candidate(r, scope) or not (urlparse(url).path or "").strip("/"):
            continue
        words = set(_words(r["name"]))
        key = words - generic
        built = [u for u in own_urls if u != url and slug_words(u) and slug_words(u) <= words
                 and key and key <= slug_words(u)]
        if built and not key & path_words(url):
            found.append(r)
    return found


def cmd_keywords(args):
    rows = load(args.path)
    if not isinstance(rows, list):
        sys.exit("Unexpected payload: expected a list under 'data'.")
    monitored_all = len(rows)
    if args.market:
        rows = [r for r in rows if r.get("search_engine_name") == args.market]

    ranking = [r for r in rows if rank_of(r)]
    band = [
        r for r in ranking
        if BAND_MIN <= rank_of(r) <= BAND_MAX and r.get("rank_type") == "organic"
    ]
    volumes = [volume(r) for r in ranking if volume(r)]
    head_cut = max(HEAD_TERM_FLOOR, statistics.median(volumes) * HEAD_TERM_FACTOR) if volumes else HEAD_TERM_FLOOR
    no_volume = [r for r in band if not volume(r)]
    markets = Counter(r.get("search_engine_name") for r in band)

    skip = {s.strip() for s in (args.skip or "").split(",") if s.strip()}
    suspect = {r["id"]: suspect_reasons(r, args.since, skip) for r in ranking}
    heads = [r for r in band if volume(r) >= head_cut and not suspect[r["id"]]]
    order = sorted(band, key=lambda r: (-score(r), rank_of(r)))

    if args.csv:
        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(["keyword", "market", "band", "rank", "rank_change", "volume", "score",
                         "head_term", "ranking_url", "keyword_id", "ai_overview", "suspect"])
        for r in order:
            writer.writerow([
                r["name"], r.get("search_engine_name"), milestone(rank_of(r)),
                rank_of(r), change_str(r), vol_str(r), round(score(r), 1),
                "yes" if volume(r) >= head_cut else "",
                r.get("best_ranking_url"), r["id"], r.get("ai_overview"), "; ".join(suspect[r["id"]]),
            ])
        return

    if args.top is None:
        args.top = SCREEN_TOP if args.screen else TOP
    print(f"# Ranking opportunities - positions {BAND_MIN}-{BAND_MAX}, the {args.top} most attractive"
          + (" candidates, screened" if args.screen else ""))
    print()
    print(f"- Monitored keywords: {monitored_all}"
          + (f" ({len(rows)} of them on {args.market})" if args.market else ""))
    print(f"- Ranking: {len(ranking)}")
    print(f"- In the {BAND_MIN}-{BAND_MAX} band: {len(band)} (of which {len(no_volume)} have <10 searches: a data "
          f"gap, not proof that nobody searches; counted as {VOLUME_STAND_IN} in the order, none dropped)")
    if len(ranking) < THIN_PROJECT or len(band) < THIN_BAND:
        print(f"- THIN SET: {len(ranking)} keywords rank, {len(band)} are in the band. This report is short")
        print("  because the tracked set is short, not because the site has no opportunities. Say so, and")
        print("  suggest adding keywords to Ranking Monitoring before reading much into it.")
    print(f"- Head-term threshold for this project: {head_cut:,.0f} monthly searches")
    if len(markets) > 1:
        print("- Markets in the band: " + ", ".join(f"{m} ({n})" for m, n in markets.most_common())
              + ". Picks can come from any of them; each names its market.")
    print()

    picks, seen_urls, seen_names = [], set(), set()
    for r in sorted(order, key=lambda r: (not readable(r, args.scope), holds_better(r, ranking), is_first(r))):
        if suspect[r["id"]] or r in heads:
            continue
        url = r.get("best_ranking_url")
        if url in seen_urls or r["name"] in seen_names:
            continue
        seen_urls.add(url)
        seen_names.add(r["name"])
        picks.append(r)
        if len(picks) == args.top:
            break

    if args.screen:
        run_screen(picks, ranking, args.scope)
    else:
        for i, r in enumerate(picks, 1):
            emit_pick(i, r, ranking, args.scope)

    flagged = [r for r in order if suspect[r["id"]]]
    if flagged:
        print(f"Not confirmed ({len(flagged)}, ranking data suspect, not picked): " + "; ".join(
            f"{r['name']} #{rank_of(r)} ({', '.join(suspect[r['id']])})" for r in flagged[:10])
              + (f"; and {len(flagged) - 10} more" if len(flagged) > 10 else ""))
    if heads:
        print("Head terms (not quick wins, not picked): " + "; ".join(
            f"{r['name']} #{rank_of(r)} ({vol_str(r)})" for r in heads))
    held = [r for r in order if r not in picks and not suspect[r["id"]] and r not in heads
            and holds_better(r, ranking) and r.get("best_ranking_url") not in seen_urls]
    if held:
        print(f"Held back ({len(held)}, the URL ranks better for another keyword): " + "; ".join(
            f"{r['name']} #{rank_of(r)} ({vol_str(r)})" for r in held[:5])
              + (f"; and {len(held) - 5} more" if len(held) > 5 else ""))
    twins = [r for r in order if r not in picks and twin_candidate(r, args.scope)
             and not suspect[r["id"]] and r not in heads and r not in held]
    if twins:
        print(f"Wrong language, not screened ({len(twins)}, a page in another language ranks on this market): "
              + "; ".join(f"{r['name']} #{rank_of(r)} ({vol_str(r)})" for r in twins[:5])
              + (f"; and {len(twins) - 5} more" if len(twins) > 5 else ""))
    outside = [r for r in order if r not in picks and not readable(r, args.scope)
               and not suspect[r["id"]] and r not in heads and r not in held]
    if outside:
        print(f"Outside the crawl ({len(outside)}, the page cannot be read, picked only when nothing else is left): "
              + "; ".join(f"{r['name']} #{rank_of(r)} ({vol_str(r)})" for r in outside[:5])
              + (f"; and {len(outside) - 5} more" if len(outside) > 5 else ""))
    firsts = [r for r in band if is_first(r)]
    if firsts:
        print(f"First rankings since the previous check: {len(firsts)} in the band. Not suspect by themselves;"
              " they come after keywords with a previous position.")
    rest = len(band) - len(picks) - len(flagged) - len(heads) - len(held) - len(twins) - len(outside)
    print(f"{rest} more in the band, not analysed.")
    print()
    top20 = [r for r in ranking if r.get("rank_type") == "organic" and rank_of(r) <= BAND_MAX]
    wrong = wrong_page_rows(top20, rows, suspect, args.scope)
    if len(wrong) >= WRONG_PAGE_MIN:
        print(f"Worth knowing: {len(wrong)} keywords rank with a different page than the one you built for them (e.g. "
              + ", ".join(f'"{r["name"]}" \u2192 {page_label(r)}' for r in wrong[:3])
              + "). That is not a quick win on its own; it usually means internal links or titles point Google"
                " to the wrong page.")
        print("(Side note: one line under the overview table. Never a row, never counted as an opportunity.)")
        print()
    print("Order is closeness to the next milestone first (top 3 from 4-10, page 1 from 11-20), search")
    print("volume second; a volume of <10 counts as 5. The SERP half of the gate still has")
    print("to run on each pick (read an inline SERP, or --serp on a saved one).")


class _Promise(HTMLParser):
    """Collects <title>, the meta description and every <h1> text of one page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.description, self.h1 = "", None, []
        self.robots, self.canonical = "", None
        self.alternates = {}  # hreflang -> URL, the declared language versions
        self._in, self._buf = None, []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "link" and "alternate" in a.get("rel", "").lower().split() and a.get("hreflang"):
            self.alternates.setdefault(a["hreflang"].lower(), a.get("href", "").strip())
        elif tag == "meta" and a.get("name", "").lower() == "description" and self.description is None:
            self.description = a.get("content", "").strip()
        elif tag == "meta" and a.get("name", "").lower() in ("robots", "googlebot"):
            self.robots += " " + a.get("content", "").lower()
        elif tag == "link" and "canonical" in a.get("rel", "").lower().split() and self.canonical is None:
            self.canonical = a.get("href", "").strip()
        elif tag in ("title", "h1") and self._in is None:
            self._in, self._buf = tag, []

    def handle_endtag(self, tag):
        if tag == self._in:
            text = " ".join("".join(self._buf).split())
            if tag == "title" and not self.title:
                self.title = text
            elif tag == "h1" and text:
                self.h1.append(text)
            self._in = None

    def handle_data(self, data):
        if self._in:
            self._buf.append(data)


def fetch_page(raw_url):
    """Fetch one page and parse what it promises. Returns a dict; `failed` or `empty` is set when
    the page could not be read, with the reason."""
    url = html.unescape(raw_url or "")
    page = {"url": url}
    if not url.startswith(("http://", "https://")):
        page["failed"] = "no ranking URL to read"
        return page
    req = Request(url, headers={"User-Agent": BROWSER_UA, "Accept": "text/html",
                                "Accept-Language": "de,en;q=0.8", "Accept-Encoding": "identity"})
    try:
        with urlopen(req, timeout=20) as resp:
            ctype = resp.headers.get("Content-Type", "")
            page["status"], page["final_url"] = resp.status, resp.geturl()
            page["x_robots"] = (resp.headers.get("X-Robots-Tag") or "").lower()
            if "html" not in ctype:
                page["failed"] = f"not an HTML page ({ctype or 'no content type'})"
                return page
            charset = resp.headers.get_content_charset() or "utf-8"
            body = resp.read(1_500_000).decode(charset, errors="replace")
    except HTTPError as e:
        page["status"] = e.code
        page["failed"] = (f"HTTP {e.code} - the page is gone or the URL is wrong" if e.code in (404, 410)
                          else f"HTTP {e.code} - the site blocks scripts")
        return page
    except (URLError, TimeoutError, OSError) as e:
        page["failed"] = f"{getattr(e, 'reason', e)} (a dropped connection or timeout counts as a block)"
        return page
    parser = _Promise()
    parser.feed(body)
    page.update(title=parser.title, description=parser.description, h1=parser.h1,
                robots=parser.robots.strip(), canonical=parser.canonical, alternates=parser.alternates)
    if not parser.h1 and len(parser.title) < 20:
        # A JavaScript page answers a script with an empty shell: title "Reddit", no H1.
        page["empty"] = True
    return page


def cmd_promise(args):
    """Title, meta description and H1 of each URL: what the page promises in the search results.

    Free and small, where `seo_check` is an expensive live call and returns 20-50 kB per page.
    Pages that block scripts (403, bot walls) print FAILED; read those with `seo_check` instead.
    """
    for raw_url in args.promise:
        page = fetch_page(raw_url)
        print(f"URL: {page['url']}")
        if page.get("failed"):
            gone = page.get("status") in (404, 410)
            print(f"  FAILED: {page['failed']}" + ("" if gone else " - read it with seo_check") + "\n")
            continue
        if page.get("empty"):
            print(f"  EMPTY: title '{page['title'] or '(none)'}' and no H1 - the page builds its content"
                  " in the browser. Try seo_check once; if that is empty too, classify it from its URL.\n")
            continue
        print(f"  title: {page['title'] or '(none)'}")
        print(f"  description: {page['description'] if page['description'] is not None else '(none)'}")
        if not page["h1"]:
            print("  h1: (none)")
        for i, h in enumerate(page["h1"][:6], 1):
            print(f"  h1 #{i}: {h[:160]}")
        if len(page["h1"]) > 1:
            print(f"  {len(page['h1'])} H1s: take the one that names the page's topic, not a navigation label.")
        print()


_FOLD = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "-": " ", "_": " ", "/": " "})


def _words(text):
    return re.findall(r"[a-z0-9]+", (text or "").lower().translate(_FOLD))


def same_word(a, b):
    """Inflected forms of the same word count as that word (singular and plural, verb and noun forms
    such as "kosten" and "kostet"). Both words are already folded. They are the same word when they
    share a start of at least 4 letters (3 for a short word) and each has at most 2 letters more
    (1 for a short word). Compounds and derivations ("haus" and "hausverwaltung", "kosten" and
    "kostenlos") are other words."""
    shared = 0
    for x, y in zip(a, b):
        if x != y:
            break
        shared += 1
    short = min(len(a), len(b))
    if shared < max(3, short - 2):
        return False
    room = 2 if shared >= 4 else 1
    return len(a) - shared <= room and len(b) - shared <= room


def keyword_in(keyword, text):
    """Every word of the keyword appears in the text, in any order, as the same word (same_word).
    A hint for the screen, not a verdict: the model checks the flag itself."""
    have = _words(text)
    return all(any(same_word(w, h) for h in have) for w in _words(keyword))


YEAR = re.compile(r"\b(20[0-9]{2})\b")
TIER1 = {"status", "redirect", "noindex", "canonical", "twin-blocked"}


def alternate_for(page, lang):
    """The declared version for a language: an exact code first, then a regional one (de-de)."""
    alts = page.get("alternates") or {}
    return alts.get(lang) or next((u for k, u in alts.items() if k.split("-")[0] == lang), None)


def same_page(a, b):
    return bool(a and b) and norm(html.unescape(a)).rstrip("/") == norm(html.unescape(b)).rstrip("/")


def twin_flags(row, page, scope):
    """A wrong-language row: find the market's version through the ranking page's hreflang, read it,
    and flag what stops it from ranking. Returns (flags, twin page or None)."""
    have, want = lang_of(page["url"]).upper(), twin_lang(row, scope)
    market = row.get("search_engine_name")
    if page.get("failed") or page.get("empty"):
        return [("wrong-language", f"the {have} page ranks on {market}; it could not be read, so its"
                                   f" {want.upper()} version is unknown - look for it in the crawl")], None
    twin = alternate_for(page, want)
    if not twin:
        return [("wrong-language", f"the {have} page ranks on {market} and declares no {want.upper()} version:"
                                   " either that page does not exist or the language links miss it")], None
    if not in_scope({"best_ranking_url": twin}, scope):
        return [("wrong-language", f"the {have} page ranks on {market}; its {want.upper()} version {twin}"
                                   " lies outside the crawl too")], None
    tp = fetch_page(twin)
    flags = [("wrong-language", f"the {have} page ranks on {market}; the {want.upper()} version is {twin}")]
    if tp.get("failed") or tp.get("empty"):
        return flags, tp
    blockers = [text for kind, text in screen_flags(row, tp) if kind in TIER1]
    if blockers:
        flags.append(("twin-blocked", f"the {want.upper()} version: " + "; ".join(blockers)))
    back = alternate_for(tp, lang_of(page["url"]))
    own = alternate_for(tp, want)
    if not same_page(back, page["url"]) or not same_page(own, tp.get("final_url") or twin):
        flags.append(("hreflang", f"language links do not match: the {want.upper()} version names"
                                  f" {back or 'no'} {have} page and {own or 'no'} {want.upper()} page"))
    title, h1 = tp.get("title") or "", " ".join(tp.get("h1") or [])
    if not keyword_in(row["name"], title) and not keyword_in(row["name"], h1):
        flags.append(("keyword-missing", f"keyword not in title or H1 of the {want.upper()} version"))
    return flags, tp


def screen_flags(row, page):
    """What the candidate's own page already shows. Tier-1 flags first."""
    flags = []
    if page.get("status") and page["status"] != 200:
        flags.append(("status", f"HTTP {page['status']}"))
    final = page.get("final_url")
    if final and norm(final).rstrip("/") != norm(page["url"]).rstrip("/"):
        flags.append(("redirect", f"redirects to {final}"))
    if "noindex" in (page.get("robots") or "") or "noindex" in (page.get("x_robots") or ""):
        flags.append(("noindex", "noindex"))
    canon = page.get("canonical")
    if canon and norm(canon).rstrip("/") != norm(final or page["url"]).rstrip("/"):
        flags.append(("canonical", f"canonical points to {canon}"))
    if page.get("failed") or page.get("empty"):
        return flags
    title, h1 = page.get("title") or "", " ".join(page.get("h1") or [])
    if not keyword_in(row["name"], title) and not keyword_in(row["name"], h1):
        flags.append(("keyword-missing", "keyword not in title or H1"))
    this_year = _date.today().year
    old = sorted({y for y in YEAR.findall(title + " " + h1) if int(y) < this_year})
    if old:
        flags.append(("old-year", f"outdated year in title/H1 ({', '.join(old)})"))
    return flags


def emit_screen(i, r, ranking, page, flags, twin=None):
    print(f"## {i}. {r['name']} - position {rank_of(r)} ({change_str(r)}), next milestone {milestone(rank_of(r))},"
          f" volume {vol_str(r)}, {r.get('search_engine_name')}, keyword_id {r['id']}")
    print(f"- Ranking URL: {page['url']}")
    if page.get("failed"):
        print(f"- Page not read: {page['failed']} - read it from the crawl in step 4.")
    elif page.get("empty"):
        print("- Page not read: empty shell (content built in the browser) - read it from the crawl in step 4.")
    else:
        print(f"- title: {page.get('title') or '(none)'}")
        print(f"- h1: {' | '.join(h[:120] for h in page.get('h1') or []) or '(none)'}")
    if twin:
        print(f"- Market-language version (analyse THIS page from the crawl): {twin['url']}")
        if twin.get("failed") or twin.get("empty"):
            print("  not read by script - read it from the crawl in step 4.")
        else:
            print(f"  title: {twin.get('title') or '(none)'}")
            print(f"  h1: {' | '.join(h[:120] for h in twin.get('h1') or []) or '(none)'}")
            print("  declares: " + (", ".join(f"{k} {v}" for k, v in (twin.get('alternates') or {}).items())
                                    or "no language versions"))
    if is_first(r):
        print("- FIRST RANKING since the previous check: use it only once its SERP passes the gate.")
    others = same_url(r, ranking)
    if others:
        print("- Same URL also ranks for: " + "; ".join(f"{o['name']} #{rank_of(o)} ({vol_str(o)})" for o in others[:5]))
        if any(rank_of(o) < rank_of(r) for o in others):
            print("  HOLDS A BETTER POSITION ELSEWHERE - do not retitle or re-aim this URL.")
    ctrl = controls(r, ranking, twin["url"] if twin else None)
    if len(ctrl) >= 2 and ctrl in _SEEN_CONTROLS:
        print("- Controls: the same pages as an earlier candidate - pull them once.")
    elif len(ctrl) >= 2:
        _SEEN_CONTROLS.append(ctrl)
        print("- Controls (only for the internal-link check): " + ", ".join(ctrl))
    else:
        print(f"- Controls: {len(ctrl)} top-3 page(s) in the same section - no internal-link comparison possible")
    print("- SCREEN: " + ("; ".join(text for _, text in flags) if flags else "nothing visible on the page itself"))
    print()


def screen_order(screened, ranking, scope=None):
    """Attractiveness decides the order of the checks. A Tier 1 blocker comes first (the page cannot
    win as it stands); any other flag only moves a candidate ahead of neighbours that are about as
    attractive: within TIE_SHARE of the first one's order value, and in the same pick group (readable,
    holds a better position, first ranking). A flag never lifts a candidate over a clearly more
    attractive one."""
    tier1 = [t for t in screened if any(f[0] in TIER1 for f in t[2])]
    out, group = [], []

    def kind(row):
        return (readable(row, scope), holds_better(row, ranking), is_first(row))

    for t in (t for t in screened if t not in tier1):
        if group and (kind(t[0]) != kind(group[0][0]) or score(t[0]) < TIE_SHARE * score(group[0][0])):
            out += sorted(group, key=lambda g: not g[2])
            group = []
        group.append(t)
    out += sorted(group, key=lambda g: not g[2])
    return tier1 + out


def run_screen(picks, ranking, scope=None):
    screened = []
    for r in picks:
        page = fetch_page(r.get("best_ranking_url") or "")
        twin = None
        if twin_candidate(r, scope):
            # The ranking page is the wrong language: its own title and H1 are not what needs to
            # change. Keep only its blockers and judge the market's version instead.
            flags = [f for f in screen_flags(r, page) if f[0] in TIER1]
            more, twin = twin_flags(r, page, scope)
            flags += more
        else:
            flags = screen_flags(r, page)
        if holds_better(r, ranking):
            # The page must not be re-aimed, so a missing keyword is not a fix here.
            flags = [f for f in flags if f[0] != "keyword-missing"]
        screened.append((r, page, flags, twin))
    screened = screen_order(screened, ranking, scope)
    for i, (r, page, flags, twin) in enumerate(screened, 1):
        emit_screen(i, r, ranking, page, flags, twin)
    kinds = Counter(k for _, _, flags, _ in screened for k in sorted({f[0] for f in flags}))
    for kind, n in kinds.items():
        if n >= 2:
            names = [r["name"] for r, _, flags, _ in screened if any(f[0] == kind for f in flags)]
            print(f"PATTERN: {n} candidates share '{kind}' ({', '.join(names)}). If the cause is the"
                  " same (one template, one setting), it is one change for all of them.")
    unread = [r for r, page, _, _ in screened if page.get("failed") or page.get("empty")]
    if screened and len(unread) == len(screened):
        print("The site answered no script request: read the candidates' pages from the crawl instead.")
    print()


def cmd_serp(args):
    data = load(args.serp)
    rows = data.get("rankings", []) if isinstance(data, dict) else data
    rows = sorted((r for r in rows if not r.get("localpack")), key=lambda r: r.get("rank") or 999)
    reasons = []
    own = [r for r in rows if r.get("is_self")]
    for url, n in Counter(html.unescape(r.get("url") or "") for r in own).items():
        if n > 1:
            reasons.append(f"own URL appears {n} times ({url})")
    notes = []
    top10 = [r for r in rows if type(r.get("rank")) is int and r["rank"] <= 10]
    for url, n in Counter(html.unescape(r.get("url") or "") for r in top10 if not r.get("is_self")).items():
        if n > 1:
            notes.append(f"{url} appears {n} times in the top 10 (another site's row: says nothing about your position)")
    block = 0
    for r in rows:
        if r.get("rank_change") != SERP_NEW:
            break
        block += 1
    if block >= NEW_BLOCK:
        reasons.append(f"positions 1-{block} are all new")
    if args.expect_rank and own and own[0].get("rank") != args.expect_rank:
        reasons.append(f"own position #{own[0].get('rank')} here, #{args.expect_rank} in list_keywords")
    if not own:
        reasons.append("own URL not in this SERP")
    twice = {}
    for r in rows:
        if not r.get("is_self"):
            twice.setdefault(html.unescape(r.get("url") or ""), []).append(r.get("rank"))
    doubled = [(u, ranks) for u, ranks in twice.items() if u and len(ranks) > 1]
    if len(doubled) >= DOUBLED_MIN:
        reasons.append(f"{len(doubled)} other sites appear twice ("
                       + ", ".join(f"{urlparse(u).netloc} #{'/#'.join(map(str, ranks))}" for u, ranks in doubled[:3])
                       + "): the own position cannot be confirmed in this list")

    snap = data.get("snapshot_position") if isinstance(data, dict) else None
    print(f"SERP rows: {len(rows)} | snapshot_position: {snap} | own: "
          + (", ".join(f"#{r.get('rank')} {html.unescape(r.get('url') or '')}" for r in own) or "-"))
    print("SERP gate: " + ("SUSPECT - " + "; ".join(reasons) if reasons else "pass"))
    for note in notes:
        print(f"Note: {note}")
    print()
    print(f"Top {args.rows} (not self):")
    top = [r for r in rows if not r.get("is_self")][:args.rows]
    for r in top:
        chg = "new" if r.get("rank_change") == SERP_NEW else r.get("rank_change")
        print(f"- #{r.get('rank')} {r.get('domain')} (change {chg}) {html.unescape(r.get('url') or '')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="Saved list_keywords payload (JSON), or - for stdin")
    ap.add_argument("--top", "--limit", dest="top", type=int, default=None,
                    help=f"Keywords to pick (default {TOP}, {SCREEN_TOP} with --screen); "
                         "--limit is the old name")
    ap.add_argument("--market", help="Restrict to one search_engine_name, e.g. Google.de")
    ap.add_argument("--since", help="Start of the comparison window (YYYY-MM-DD); rows with a later "
                                    "date_added are suspect")
    ap.add_argument("--skip", help="Comma-separated keyword_ids that failed the SERP gate or whose page "
                                   "could not be read; pick the next")
    ap.add_argument("--scope", help="The project URL (the crawl's start). Ranking URLs outside it come last")
    ap.add_argument("--screen", action="store_true", help="First pass: screen the top candidates' own "
                                                         "pages (10 by default, free)")
    ap.add_argument("--csv", action="store_true", help="Emit every band row as CSV instead")
    ap.add_argument("--serp", help="Check a saved get_keyword_rankings payload (or - for stdin)")
    ap.add_argument("--expect-rank", type=int, help="With --serp: the position list_keywords reports")
    ap.add_argument("--rows", type=int, default=3, help="With --serp: top rows to print (default 3)")
    ap.add_argument("--promise", nargs="+", metavar="URL",
                    help="Print title, meta description and H1 of each URL (the top 3 of a SERP)")
    args = ap.parse_args()
    if args.promise:
        cmd_promise(args)
    elif args.serp:
        cmd_serp(args)
    elif args.path:
        cmd_keywords(args)
    else:
        ap.error("give a list_keywords payload path, or --serp <file>")


if __name__ == "__main__":
    main()
