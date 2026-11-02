#!/usr/bin/env python3
"""Helpers for the content gap comparison: read pages side by side, and reduce a saved tfidf_check.

Usage:
    python competitor_gap.py pages <our url> <competitor url> [<competitor url> ...] [--keyword "<kw>"]
    python competitor_gap.py tfidf <saved tfidf_check file|-> [--min-weight 5.0] [--noise noise.txt]
    python competitor_gap.py links <saved backlink_check file|-> [--top 5]

`pages` fetches each URL once (free, no credits) and prints what a reader of the search results and
of the page itself sees: title, meta description, H1, the H2/H3 outline in page order, word count,
tables and lists, FAQ blocks, structured data types (JSON-LD @type), the publish/modified date
(meta tags, JSON-LD datePublished/dateModified, or the first <time datetime>), and
whether the keyword is in title and H1 (every word, any order: yes / partly / missing) and how
often it appears in headings. The first URL is ours. Pages that block
scripts print FAILED; read those with seo_check instead, or leave them out.

`tfidf` reduces a saved `tfidf_check` response to the parts the comparison uses: the live top 10 with
titles, the terms our page under-uses, and the terms competitors weight that our page never uses.
It merges hyphenated compounds with their spaced form before calling a term missing: `tfidf_check`
counts "saas-seo" as its own token, so a page that writes "SaaS SEO" shows `url_tf: 0` for it.
It names URLs that appear twice in the top 10 (their terms are counted twice), says when the results
look location-dependent, and flags terms that are a place named in the results ("in Hildesheim") or
part of a competitor's domain name: those are never a gap.
Use it only on a result the host saved as a file; an inline result is read directly.

`links` reduces a saved `backlink_check` response (URL mode) to what the comparison uses: how many
sites link to the page, the host's domain score, and the strongest active follow links by rating,
which are the sources worth approaching when links are what separates the pages. On a well-linked
page the response holds the whole link list (100k characters and more), so it is usually saved.
The "1 / 1 / 1" answer with no title and no links means no link data for the page yet: it prints as
NO LINK DATA, never as one link.
"""

import argparse
import html
import io
import json
import os
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/128.0 Safari/537.36")
OUTLINE_MAX = 40   # headings printed per page
SKIP_TAGS = {"script", "style", "noscript", "svg", "template"}
CHROME_TAGS = {"nav", "footer", "header", "aside", "form"}

# Generic words that score as high-weight terms but name no topic. Override with --noise.
DEFAULT_NOISE = {
    "better", "wrong", "went", "wait", "power", "proper", "boost", "get", "add", "tip", "help",
    "generate", "improving", "maintain", "besonders", "wichtig", "wichtigsten", "gleich", "schnell",
    "neue", "richtigen", "richtige", "findest", "gesamte", "gesamten", "stellen", "schaffen",
    "fällt", "läuft", "hart", "ehrlich", "teilen", "begleitet", "schwer", "work", "erstellt",
    "überzeugt", "anfang", "verwenden", "funktioniert", "zeit", "jahre", "detaillierte", "gezielte",
}


class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.description, self.h1, self.outline = "", None, [], []
        self.jsonld, self.dates, self.tables, self.lists, self.details = [], {}, 0, 0, 0
        self.words = 0
        self._stack, self._buf, self._skip, self._chrome, self._ld = [], [], 0, 0, None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            name = (a.get("name") or a.get("property") or a.get("itemprop") or "").lower()
            if name == "description" and self.description is None:
                self.description = a.get("content", "").strip()
            elif name in ("article:modified_time", "article:published_time", "datemodified", "datepublished"):
                self.dates.setdefault(name, a.get("content", "")[:10])
        elif tag == "script" and "ld+json" in a.get("type", "").lower():
            self._ld = []
        elif tag == "time" and a.get("datetime") and "time" not in self.dates:
            self.dates["time"] = a["datetime"][:10]
        if tag in SKIP_TAGS:
            self._skip += 1
        if tag in CHROME_TAGS:
            self._chrome += 1
        if tag == "table":
            self.tables += 1
        elif tag in ("ol", "ul") and not self._chrome:
            self.lists += 1
        elif tag == "details":
            self.details += 1
        if tag in ("title", "h1", "h2", "h3"):
            self._stack.append(tag)
            self._buf = []

    def handle_endtag(self, tag):
        if tag == "script" and self._ld is not None:
            self.jsonld.append("".join(self._ld))
            self._ld = None
        if tag in SKIP_TAGS and self._skip:
            self._skip -= 1
        if tag in CHROME_TAGS and self._chrome:
            self._chrome -= 1
        if self._stack and tag == self._stack[-1]:
            self._stack.pop()
            text = " ".join("".join(self._buf).split())
            if not text:
                return
            if tag == "title" and not self.title:
                self.title = text
            elif tag == "h1":
                self.h1.append(text)
            elif tag in ("h2", "h3") and not self._chrome:
                self.outline.append((tag, text))

    def handle_data(self, data):
        if self._ld is not None:
            self._ld.append(data)
            return
        if self._stack:
            self._buf.append(data)
        if not self._skip and not self._chrome:
            self.words += len(data.split())


def _ld_dates(blob):
    """datePublished / dateModified from one JSON-LD block, nested ones included (first found)."""
    found = {}

    def walk(node):
        if isinstance(node, dict):
            for key in ("datePublished", "dateModified"):
                v = node.get(key)
                if isinstance(v, str) and key.lower() not in found:
                    found[key.lower()] = v[:10]
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    try:
        walk(json.loads(blob))
    except (ValueError, TypeError):
        pass
    return found


def _types(blob):
    """@type values from one JSON-LD block, nested ones included."""
    out = []

    def walk(node):
        if isinstance(node, dict):
            t = node.get("@type")
            if isinstance(t, str):
                out.append(t)
            elif isinstance(t, list):
                out.extend(x for x in t if isinstance(x, str))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    try:
        walk(json.loads(blob))
    except (ValueError, TypeError):
        pass
    return out


def fetch(url):
    url = html.unescape(url)
    req = Request(url, headers={"User-Agent": BROWSER_UA, "Accept": "text/html",
                                "Accept-Language": "de,en;q=0.8", "Accept-Encoding": "identity"})
    try:
        with urlopen(req, timeout=25) as resp:
            if "html" not in resp.headers.get("Content-Type", ""):
                return url, None, "not an HTML page"
            charset = resp.headers.get_content_charset() or "utf-8"
            body = resp.read(3_000_000).decode(charset, errors="replace")
    except HTTPError as e:
        return url, None, f"HTTP {e.code}" + ("" if e.code in (404, 410) else " - the site blocks scripts")
    except (URLError, TimeoutError, OSError) as e:
        return url, None, f"{getattr(e, 'reason', e)} (a timeout or dropped connection counts as a block)"
    page = _Page()
    page.feed(body)
    for blob in page.jsonld:
        for k, v in _ld_dates(blob).items():
            page.dates.setdefault(k, v)
    if not page.h1 and page.words < 150:
        return url, None, "empty shell (the page builds its content in the browser)"
    return url, page, None


def _norm(text):
    """Shared definition: lower case, umlauts and sharp s spelled out, punctuation as spaces."""
    t = (text or "").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", " ", t).split()


def _same_word(a, b):
    """Inflected forms of the same word count as that word (singular and plural, verb and noun forms
    such as "kosten" and "kostet"). Same rule as seobility-ranking-opportunities' same_word: a shared
    start of at least 4 letters (3 for a short word) and at most 2 more letters on each side (1 for a
    short word). Compounds and derivations ("haus" and "hausverwaltung", "kosten" and "kostenlos")
    are other words."""
    shared = 0
    for x, y in zip(a, b):
        if x != y:
            break
        shared += 1
    if shared < max(3, min(len(a), len(b)) - 2):
        return False
    room = 2 if shared >= 4 else 1
    return len(a) - shared <= room and len(b) - shared <= room


def _kw_state(keyword, text):
    """'yes' when every word of the keyword is in the text (any order), 'partly' when some are,
    'missing' when none are. Words are compared with _same_word."""
    have = _norm(text)
    words = _norm(keyword)
    hits = sum(any(_same_word(w, h) for h in have) for w in words)
    return "yes" if hits and hits == len(words) else "partly" if hits else "missing"


# A place in a result's title or description: a capitalised word after "in", "aus", "bei", "nahe",
# "rund um", "Raum" or "Region" (German results such as "oil tank disposal in Hildesheim" or "in the Peine area").
_PLACE = re.compile(r"\b(?i:in|im|aus|bei|nahe|um)\s+(?:(?i:raum|region|landkreis|kreis)\s+)?([A-ZÄÖÜ][\wäöüß-]+)")
_NOT_PLACE = {"der", "die", "das", "dem", "den", "deutschland", "kuerze", "minuten", "stunden", "zukunft",
              "zeiten", "ordnung", "sachen", "bezug", "folge", "form", "frage", "zusammenarbeit", "verbindung",
              "the", "a", "an", "raum", "region", "landkreis", "kreis", "ihrer", "ihre", "ihrem", "ihren",
              "ihr", "unserer", "unserem", "unseren", "deiner", "deinem", "naehe", "kombination",
              "praxis", "regel", "theorie", "zeit"}


def _places(text):
    out = set()
    for m in _PLACE.finditer(text or ""):
        for w in _norm(m.group(1)):
            if w not in _NOT_PLACE and len(w) > 2:
                out.add(w)
    return out


def _url_key(url):
    """One key per page: no scheme, no www, no trailing slash, no query."""
    u = re.sub(r"^https?://(www\.)?", "", html.unescape(url or "").strip().lower())
    return u.split("?", 1)[0].split("#", 1)[0].rstrip("/")


def _host(url):
    """The host of a URL without www: where a business puts its brand or its town
    ("dachdecker-musterstadt.de"). The path is left out, since it usually names the topic."""
    return re.sub(r"^https?://(www\.)?", "", (url or "").lower()).split("/", 1)[0].split("?", 1)[0]


def cmd_pages(args):
    kw = args.keyword
    for i, raw in enumerate(args.urls):
        url, page, err = fetch(raw)
        label = "OURS" if i == 0 else f"COMPETITOR {i}"
        print(f"=== {label}: {url}")
        if err:
            print(f"FAILED: {err}\n")
            continue
        types = sorted({t for blob in page.jsonld for t in _types(blob)})
        print(f"title: {page.title or '(none)'}")
        print(f"description: {page.description if page.description is not None else '(none)'}")
        print(f"h1: {' | '.join(page.h1) or '(none)'}")
        print(f"words (body text, navigation and footer excluded): ~{page.words}")
        print(f"headings: {sum(1 for t, _ in page.outline if t == 'h2')} H2, "
              f"{sum(1 for t, _ in page.outline if t == 'h3')} H3 | tables: {page.tables} | "
              f"lists: {page.lists} | expandable blocks: {page.details}")
        print(f"structured data: {', '.join(types) or '(none)'}")
        if page.dates:
            seen = {}
            for k, v in sorted(page.dates.items()):
                label = {"published_time": "published", "datepublished": "published",
                         "modified_time": "modified", "datemodified": "modified"}.get(k.split(":")[-1], k)
                seen.setdefault(label, v)
            print("dates: " + ", ".join(f"{k} {v}" for k, v in seen.items()))
        if kw:
            heads = [h for _, h in page.outline]
            print(f"keyword \"{args.keyword}\": title {_kw_state(kw, page.title)}, "
                  f"H1 {_kw_state(kw, ' '.join(page.h1))}, "
                  f"in {sum(_kw_state(kw, h) == 'yes' for h in heads)} of {len(heads)} headings "
                  f"(yes = every word, partly = some, missing = none)")
        print("outline:")
        for tag, text in page.outline[:OUTLINE_MAX]:
            print(f"  {'  ' if tag == 'h3' else ''}{tag.upper()} {text[:110]}")
        if len(page.outline) > OUTLINE_MAX:
            print(f"  ... and {len(page.outline) - OUTLINE_MAX} more headings")
        print()


def load_noise(path):
    if not path:
        return set(DEFAULT_NOISE)
    with open(path, encoding="utf-8") as fh:
        return {line.split("#", 1)[0].strip().lower() for line in fh if line.split("#", 1)[0].strip()}


def cmd_tfidf(args):
    fh = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8") if args.response == "-" else open(args.response, encoding="utf-8")
    with fh:
        payload = json.load(fh)
    data = payload.get("data", payload)
    noise = load_noise(args.noise)
    req = data.get("request", {})
    ours = {k.lower() for k in (data.get("target_url_results") or {}).get("tf_idf", {})}
    print(f"# {req.get('search_term', '?')} on {req.get('search_engine', '?')}, "
          f"{req.get('serp_depth', '?')} competitor pages")
    if req.get("url"):
        print(f"# our page: {req['url']}")

    results = data.get("results", [])
    print("\n## Live top 10 (words, referring domains of the page)")
    for r in results:
        err = f"  [not analysed: {r['crawl_error']}]" if r.get("crawl_error") else ""
        refs = r.get("referring_domains")
        refs_note = " (1/1: possibly 'no data', check with backlink_check)" if str(refs) == "1" and str(r.get("backlinks")) == "1" else ""
        print(f"{str(r.get('rank') or '-'):>2}  {r.get('domain')}  {(r.get('title') or '')[:80]}{err}")
        print(f"    {r.get('url')}  | ~{r.get('word_count')} words | {refs} ref. domains{refs_note}"
              f" | server response {r.get('load_time')} s")

    by_url = {}
    for r in results:
        by_url.setdefault(_url_key(r.get("url")), []).append(r.get("rank"))
    dupes = {u: ranks for u, ranks in by_url.items() if u and len(ranks) > 1}
    if dupes:
        print("\nDUPLICATES: " + "; ".join(f"{u} at #{'/#'.join(map(str, ranks))}" for u, ranks in dupes.items())
              + ". The same page twice: its terms are counted twice in 'on N pages'; compare it once.")
    domains = {}
    for r in results:
        domains.setdefault((r.get("domain") or "").lower(), set()).add(_url_key(r.get("url")))
    multi = {d: len(u) for d, u in domains.items() if d and len(u) > 1}
    if multi:
        print("Several pages from one site: " + ", ".join(f"{d} ({n})" for d, n in multi.items())
              + ". A term on those pages can be one site's vocabulary.")

    kw_words = set(_norm(req.get("search_term", "")))
    places = Counter()
    placed_results = 0
    for r in results:
        found = {w for w in _places(f"{r.get('title') or ''} {r.get('description') or ''}")
                 if not any(_same_word(w, k) for k in kw_words)}
        places.update(sorted(found))  # ties keep a stable order across runs
        placed_results += bool(found)
    addr_words = {w for r in results for w in _norm(_host(r.get("url"))) if w not in ("de", "com", "at", "ch", "net", "org")}
    if placed_results >= 3:
        print(f"LOCATION: {placed_results} of {len(results)} results name a place ("
              + ", ".join(p for p, _ in places.most_common(5))
              + "). The results look location-dependent: Seobility fetches them without a location,"
                " and in another city the list can look different.")

    def spaced_form_used(term):
        """A hyphenated term whose parts all appear on our page is not missing."""
        parts = [p for p in re.split(r"[-_]", term.lower()) if p]
        return len(parts) > 1 and all(p in ours for p in parts)

    def other_form_used(term):
        """An inflected form of the term is on our page ("guides" vs "guide")."""
        t = term.lower()
        for o in sorted(ours):
            if o == t or "-" in o or "-" in t:
                continue
            need = max(5, min(len(o), len(t)) - 3)
            if len(os.path.commonprefix([o, t])) >= need and abs(len(o) - len(t)) <= 3:
                return o
        return None

    # `current_keyword_use_count` holds our page's TF*IDF weight, not a count: never set it against
    # the competitors' min/max, which are counts. Only the verdict is usable.
    print("\n## Under-used (usage = not_often_enough; the verdict only, ours is not a count)")
    thin = [(k, v) for k, v in (data.get("term_suggestions") or {}).items() if v.get("usage") == "not_often_enough"]
    for k, v in thin:
        if spaced_form_used(k):
            note = "  <- the words are on the page, written apart"
        elif not v.get("current_keyword_use_count"):
            note = "  <- not on our page at all"
        else:
            note = ""
        print(f"{k:<22} competitors use it {v['min_keyword_use']}-{v['max_keyword_use']} times{note}")
    if not thin:
        print("(none)")

    print(f"\n## Missing on our page (url_tf = 0, weight >= {args.min_weight}), by number of competitors")
    gaps = [s for s in data.get("stats", []) if not s.get("url_tf") and s.get("avg_tf_idf_used", 0) >= args.min_weight]
    shown = 0
    for s in sorted(gaps, key=lambda s: (-s.get("occurrences", 0), -s["avg_tf_idf_used"])):
        term = s["keyword"]
        if spaced_form_used(term):
            flag = "   <- not missing: the words are on the page, written apart"
        elif other_form_used(term):
            flag = f"   <- not missing: '{other_form_used(term)}' is on the page"
        elif term.lower() in noise:
            flag = "   <- generic word, not a topic"
        elif _norm(term) and all(w in places for w in _norm(term)):
            flag = "   <- looks like a place named in the results ('in <place>'): if it is one, never a gap"
        elif _norm(term) and all(w in addr_words and w not in kw_words for w in _norm(term)):
            flag = "   <- part of a competitor's domain name: a place or a brand? Check before using it"
        elif s.get("occurrences", 0) <= 2:
            flag = "   <- only 1-2 pages: at most two sites' vocabulary, not a consensus"
        else:
            flag = ""
        print(f"{term:<24} weight {s['avg_tf_idf_used']:>5.2f}  on {s.get('occurrences')} of "
              f"{req.get('serp_depth', 10)} pages{flag}")
        shown += 1
    if not shown:
        print("(none)")


def cmd_links(args):
    fh = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8") if args.response == "-" else open(args.response, encoding="utf-8")
    with fh:
        payload = json.load(fh)
    data = payload.get("data", payload)
    meta = data.get("meta_info") or {}
    print(f"# {data.get('domain', '?')} ({data.get('mode', '?')} mode)")
    if data.get("mode") != "url":
        print("NOTE: domain mode - pass the full page URL to get the page's own counts")
    placeholder = (str(meta.get("referring_domains_count")) == "1" and str(meta.get("total_link_count")) == "1"
                   and not (meta.get("meta_title") or "").strip() and not data.get("results"))
    if placeholder:
        print("NO LINK DATA for this page yet (1 / 1 / 1, no title, no links)."
              " Report 'no link data', never '1 linking site'.")
    print(f"sites linking to the page (referring domains): {meta.get('referring_domains_count')}"
          + (" (no link data)" if placeholder else ""))
    print(f"links in total: {meta.get('total_link_count')} (one site can link many times; compare sites, not links)")
    print(f"domain score of the host: {meta.get('domain_score')}"
          + (" (0: a small or new site)" if str(meta.get("domain_score")) == "0" else ""))
    rows = []
    for dom, val in (data.get("results") or {}).items() if isinstance(data.get("results"), dict) else []:
        for link in (val if isinstance(val, list) else [val]):
            if link.get("rel") == "follow" and not link.get("link_removed") and link.get("status") == "active":
                rows.append(link)
    best = {}
    for link in rows:
        d = link.get("origin_domain")
        if d not in best or (link.get("rating") or 0) > (best[d].get("rating") or 0):
            best[d] = link
    top = sorted(best.values(), key=lambda l: -(l.get("rating") or 0))[:args.top]
    if top:
        print(f"\n## Strongest active follow links, one per site (top {args.top} by rating)")
        for l in top:
            print(f"{str(l.get('rating') if l.get('rating') is not None else '-'):>3}  {l.get('origin_domain')}  anchor '{l.get('anchor_text')}'")
            print(f"     {l.get('origin_url')}  ({(l.get('origin_title') or '')[:70]})")
    else:
        print("\n(no active follow links listed)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pages", help="read our page and competitor pages side by side")
    p.add_argument("urls", nargs="+", help="our URL first, then the competitor URLs")
    p.add_argument("--keyword", help="the keyword, to count it in title, H1 and headings")
    t = sub.add_parser("tfidf", help="reduce a saved tfidf_check response")
    t.add_argument("response", help="saved tfidf_check JSON, or - for stdin")
    t.add_argument("--min-weight", type=float, default=5.0, help="weight floor for missing terms (default 5.0)")
    t.add_argument("--noise", help="file of generic words to flag, one per line")
    lk = sub.add_parser("links", help="reduce a saved backlink_check response (URL mode)")
    lk.add_argument("response", help="saved backlink_check JSON, or - for stdin")
    lk.add_argument("--top", type=int, default=5, help="strongest linking sites to list (default 5)")
    args = ap.parse_args()
    {"pages": cmd_pages, "tfidf": cmd_tfidf, "links": cmd_links}[args.cmd](args)


if __name__ == "__main__":
    main()
