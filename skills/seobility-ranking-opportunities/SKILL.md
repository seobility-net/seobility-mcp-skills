---
name: seobility-ranking-opportunities
description: >
  Overview of the ranking opportunities in a Seobility-tracked site: keywords in positions 4-20,
  sorted into a quick win (one concrete change) or a case for a deeper analysis of content and
  links. Screens the monitored rankings against the current SERP's search intent and the page's crawl
  data, and writes up to three quick-win guides.
  Use when someone asks "which keywords am I close to winning", "where are my quick wins", "what
  are my ranking opportunities", "which keywords are just off page 1", "three talking points about
  ranking potential for a client call", or the same in any other language; also for a short list
  of low-effort ranking opportunities. An open "what should I work on this week" belongs to
  seobility-weekly-checkin, not here. Do NOT trigger for choosing a keyword for a page that does
  not exist yet (keyword research), diagnosing a ranking drop, working through a full site audit
  (seobility-audit-triage), or checking whether the project is set up well enough to trust
  (seobility-setup-check).
---

# Ranking opportunities: where you are close, and what it takes

Turns a project's monitored rankings into an **overview of its ranking opportunities**: the
keywords just outside the positions that matter, each with a verdict. Either the data shows a
**quick win** (one concrete change that fixes a visible problem), written up as a step-by-step
guide, or the page shows no technical or on-page problem, and the keyword needs a **deeper
analysis**: a closer comparison of content and links with the pages that outrank it.

**Possible factors, never causes.** Nobody outside Google can prove why a page ranks where it does.
Everything this skill reports is a visible problem or a difference, i.e. a possible factor, and
every change is a suggestion. The report never says "this is why you are on position 7", "because",
"the reason is", and never promises that a change
brings a position.

The overview comes first, so the reader sees at a glance what was checked and what each keyword
needs. The guides follow for the quick wins only.

**A quick win is a concrete measure, never a topic.** Either one page gets one specific change
(a title that promises the wrong thing, a canonical pointing away, a keyword missing from title and
H1), or one change fixes several pages at once (the same outdated year in every title of a
series, one template setting). "The gap is competitive" is a correct finding, but it is not a quick
win, so it never fills one of the three slots.

That is why the skill screens more candidates than it reports as quick wins. It checks up to ten
keywords, cheapest checks first, and stops when it has three quick wins. Three good guides beat
twenty shallow tips: if only one candidate has a real fix, the report has one guide, and the others
get their verdict in the overview.

**This is not the competitor comparison.** The search intent comes from what the current top 3
promise in the search results: their title, meta description and H1. The skill does not read the
competitors' pages to compare structure, depth or wording. That is the deeper, more expensive job
the overview points to (see "The deeper look" at the end).

## What this skill can and cannot see

It reads **only keywords that are in the project's Ranking Monitoring**. It does not discover new
keywords, and it cannot see anything the user has not added. Say this in the output, with the
size of the tracked set, so nobody reads the list as "all my opportunities".

It also never predicts. "Close" is a measured distance between the current position and the next
band — not a likelihood, not a forecast, not a traffic estimate. Never tell a user a change will
move them to position 3.

## Definitions

**Keyword in title or H1.** Normalise both strings (lower case; ä→ae, ö→oe, ü→ue, ß→ss; hyphens and
punctuation as spaces). The keyword is _in_ the title when every word of it appears, in any order;
_partly_ when some words appear; _missing_ when none do. Inflected forms of the same word count as
that word (singular and plural, verb and noun forms such as "kosten" and "kostet").

**Kind of page.** Judge it on the top 3 results and say so ("the top 3 are …"). When positions 4–10
look different, add one sentence ("the rest of page 1 is mixed: …"). Never mix the two in one verdict.

**Search volume.** A volume of 0 or none is shown as "<10" and counted as 5. It is a data gap, not
proof that nobody searches.

## Before you spend a call

The helper scripts named below live in this skill's folder (`${CLAUDE_SKILL_DIR}` in Claude Code).
Run them as `python3 <that folder>/scripts/<script>.py`, wherever the current directory is.

1. **Resolve the project.** `list_projects`. If the user has more than one and has not named
   one, ask — but **do not offer them a list of names**. Accounts routinely hold several projects
   with the identical name for different scopes of the same site. Disambiguate with `url`,
   `pages_crawled` and `finished_date`, which do differ.

   In a large account, call `list_projects` with `compact: true` (the full shape runs to ~40k
   characters for 46 projects). Compact returns only id, name and url, so take `pages_crawled`
   and the finish date of the few candidates from `list_crawls(project_id, limit: 1)`.

   **Always show the number of monitored keywords alongside them.** `get_keyword_count(project_id)`
   returns `{"count": n}` — one tiny call per candidate, worth spending before the user picks.
   The keyword count decides whether the analysis can produce anything at all: a project with
   2,700 crawled pages and 4 monitored keywords yields no quick-win list, while a 500-page project
   with 300 keywords yields a good one. Without the count, the user picks on crawl size and crawl
   date and gets a near-empty report. So the choice reads like this:

   > - example.com/de/ · 2,708 pages · crawl today · **4 keywords monitored**
   > - example.com/de/wiki/ · 522 pages · crawl 11.09.2026 · **335 keywords monitored**

   Say which one you would pick and why — the keyword count usually decides it, and a project
   under roughly 20 keywords cannot carry this analysis whatever else it has going for it.
   Do not call `get_keyword_count` for every project in a large account; cap it at the handful
   that plausibly match what the user asked for.
2. **Check how old the crawl is.** `finished_date` from `list_projects`. The on-page half of this
   skill reads crawl data, so a crawl from nine months ago produces nine-month-old actions. State
   the crawl date whenever it is more than a few weeks old, and offer a fresh crawl as the first
   step instead of presenting stale findings as current. Rankings and crawl data are collected
   separately, so recent positions sitting on a stale crawl is normal — and misleading.
3. **Check the tracked set is worth analysing.** The keyword count from step 1 is the first
   filter; after step 1 of the method below you also know how many of those actually rank. Under
   roughly 20 ranking keywords, or under five in the 4-20 band, say so plainly: the list will be
   thin because the tracked set is thin, and the better next step is to add keywords, not to read this report. If the monitored
   count alone is already in single digits, say it before pulling the full payload — a report is
   not worth the call.

   If the set looks misconfigured rather than just small — most keywords ranking nowhere, a
   market the site does not serve, a crawl that stops far short of the site — name
   **`seobility-setup-check`** as the next step instead of building a list on it.
4. **Say which date the positions are from.** Rankings come from the last completed ranking check,
   not from live Google. One line, in the output. `list_keywords` carries no date: take
   `last_update` from the `get_keyword_overview` call you make for each candidate you check in depth.

## Method

### 1. Pull the tracked set — one call

`list_keywords(project_id)` returns every monitored keyword with everything this skill needs in a
single payload: `rank`, `rank_change`, `search_volume`, `best_ranking_url`, `search_engine_name`,
`visibility`, `ai_overview`, and `intents`.

**This payload overflows the tool-result limit on any real project** (~150 keywords ≈ 83k
characters). It gets written to a file. Do not read that file into context — run
`scripts/ranking_opportunities.py` against it. The script does the filtering, the gate and the ordering, and
with `--screen` it also reads each candidate's own page (step 3):

```bash
python3 scripts/ranking_opportunities.py <saved-file> --screen --scope <project url>
```

`--scope` is the project's URL from `list_projects`; a start page such as `/de/wiki/start` is
read as its folder `/de/wiki/`. Keywords whose ranking page lies outside it (a tool outside the
crawled section, another site section) sort last: the crawl has no data on that page, so the skill
cannot judge it.

**One exception: a page in the wrong language.** When the ranking page is the same site in another
language than the market's (the `/en/` page ranking on Google.de, while the crawl covers `/de/`),
the row is not "outside the crawl". The page built for this market usually is inside it, and
Google showing the other language instead is itself a finding. The script treats these rows as
normal candidates, and the screen finds the market's version through the ranking page's hreflang
links (step 7, Tier 2, point 4). Never swap the language folder in the URL to guess it: slugs differ
between languages (`/es/wiki/Dominios_caducados` next to `/en/wiki/Expired_Domains`).

If a result arrived inline instead of as a saved file, write it to a file first (or pipe it to the script and pass `-` as the path). If the host tells you to read an oversized result in full, don't: run the script on the path the host printed (or on a copy of it outside the skill folder) instead.

Do **not** use `get_rankings_keyword_overview` for this. Despite the name it returns four summary
counters, not a per-keyword table. See `references/tool-notes.md`.

### 2. Build the band

Keep rows where `rank` is between 4 and 20 and `rank_type` is `organic`. Rows with `rank: null`
are not ranking in the tracked range — they are not quick wins, and they are not a finding either.

**Group by `search_engine_name` first.** The same keyword appears once per search engine
(Google.de and Google.com are separate rows with different positions and different volumes). In a mid-sized tracked set, roughly one name in six appeared more than once. Reporting both as two opportunities is
double-counting. **Do not ask which market.** A quick win is a quick win on any market: the script
picks across all of them, takes each keyword and each ranking URL once, and every pick names its
market. Pass `--market` only when the user names one. Volumes are per market, so quote the volume
of the pick's own market.

**Check the ranking data before you use it.** Mark a keyword as suspect, and do not base an action on it, when any of these holds: the own URL appears more than once in the same SERP; a contiguous block at the top of the SERP is all "new" (`rank_change` 1000); `list_keywords` and the keyword's own SERP snapshot (`get_keyword_rankings`) disagree on the own URL's position (never compare with `get_keyword_ranked_pages`: it returns the best-ever position, not the current one); three or more other sites appear twice in the SERP; the keyword moved 30 or more places in one check; or it was added (`date_added`) inside the comparison window. Name suspect rows as "not confirmed", never as findings. The weekly view compares Monday to Monday, so a run on another weekday can legitimately differ from the latest-vs-previous view.

Also suspect here: a percentage change that rests on a base under 1 visibility point. One
`get_keyword_overview` call (~500 characters) is a cheap cross-check.

The script applies the part the `list_keywords` payload can answer (moves of 30 or more) and never
picks a suspect row. **"New" alone is not suspect.** It means the keyword had no position in the
previous check, which on a long-tracked project is usually a re-entry (a keyword tracked since 2018
showed it). The script sorts such rows after rows with a previous position and marks a pick with
`FIRST RANKING`; it may be used once its SERP passes the checks below. Do not list "new" rows as
"not confirmed": they are ordinary re-entries.

`list_keywords` carries no `date_added`: it comes from the one `get_keyword_overview` call you make
for each candidate you check in depth (position, `date_added`, `last_update`). Then, before any
call of step 5, pull the candidate's SERP with `get_keyword_rankings(project_id, keyword_id)` — step 5 reuses
it. A SERP already pulled in this conversation may be reused for the intent read while its
`next_snapshot_date` has not passed, which saves a 30k payload per keyword; the own position always
comes from today's `list_keywords`, and the report names the date of the reused SERP. It usually
arrives inline: then read its rows and apply the checks yourself — **the same own
URL** more than once, a contiguous `rank_change: 1000` block at the top, own position against
`list_keywords` — and do not copy it to a file. Two *different* own URLs in the SERP are not a
data problem: they are the cannibalisation signal for Tier 2 in step 7. **Another site's URL twice
in the top 10 is not a reason to drop the pick either**: it says nothing about your own position.
Note it, and keep the pick. Three or more other sites twice, one high and one far down (#9 and #93),
do not pass the gate: then the own position in that list cannot be confirmed either. A list of
25-30 rows is normal for some searches and passes.
Only when the host already saved the SERP as a file, run:

```bash
python3 scripts/ranking_opportunities.py --serp <saved-serp-file> --expect-rank <position from list_keywords>
```

Never run the check on a partial copy. Local-pack rows don't count. The script prints one other
site's duplicate as a `Note`, not as `SUSPECT`; three or more as `SUSPECT`.

If a candidate fails the gate, drop it, say "not confirmed" and go on with the next one on the
screened list. It counts towards the six candidates of step 4.

**How it reads in the report.** One line per keyword: "I could not confirm this position, so I did
not assess it". The check is how you decide what to assess; its details stay out of the report.

### 3. Order the candidates and screen them

The next milestone depends on where a keyword stands, and the distance is measured to that
milestone:

| Current position | Next milestone | Distance |
|---|---|---|
| 4-10 | top 3 | `rank - 3` |
| 11-20 | page 1 | `rank - 10` |

A keyword at #11 is one step from page 1, not eight steps from the top 3. Measuring everything
against the top 3 would push the whole 11-20 band to the back, although page 1 is the step that
changes the most for a page nobody sees yet. Each quick win names its milestone in the output.

The script orders rows by `log10(volume) / distance`. **The damping is the point.**
An undamped `volume / distance` is dominated by raw volume — on a large tracked set it returns the
five biggest head terms in the account and nothing else. Those are the hardest
positions in the account to move, which is the opposite of a quick win.

The ordering is never shown as a number, in the table or in the report. A score column invites the
reader to treat it as traffic. Row order carries the priority; volume is shown on its own.

Closeness deciding the order has one side effect worth watching: a keyword one position from the
milestone can top the list even when its volume is tiny. Keep it — it is genuinely the easiest
move available — but say its volume out loud with it ("<10" for 0 or none). The user decides.

The script lists head terms apart and never picks them: volume at least ten times the median of
all ranking keywords, and never below 1,000 a month. They are close on paper and they are the
hardest fight in the account. Name them in one line, and do not sell them as quick wins. A volume
of 0 or none counts as 5 in the order (see Definitions): such rows are never dropped, never gated and
never sent to the back, and on a young long-tail site they can fill a pick. The report says "<10",
never "0" or "no searches".

The script takes one keyword per ranking URL; the other keywords of that URL print with the candidate.
A keyword whose URL ranks better for another keyword comes after every clean candidate, because
its page must not be re-aimed; if it is not picked, the script names it as held back. When three or
more band rows rank with a page built for something else, the script also prints a "Worth knowing"
line: that is the wrong-page side note of the report (see Output), not a candidate.
When two candidates are close, prefer the one whose ranking page is the right page type for the
query (a template page for "X template", a city page for "<service> <city>"). That is judgement,
and it is yours. Everything below the screened candidates becomes one line: how many more are in
the band, not analysed. No second table.

**The screen.** `--screen` takes the ten best candidates in that order and fetches each one's own
ranking page once. It is free and prints about 1 kB per page: title, H1 and a `SCREEN` line with
what the page itself already shows:

| Flag | What it means |
|---|---|
| `HTTP <code>`, `redirects to`, `noindex`, `canonical points to` | Tier 1: the page cannot win as it stands |
| `keyword not in title or H1` | Tier 2 candidate: check it by hand with the rules in step 7, the script's word match is only a hint |
| `outdated year in title/H1` | The page promises last year's (or older) information to someone searching today |
| `the EN page ranks on Google.de; the DE version is <url>` | Wrong language. The screen prints the market's version under "Market-language version": **that** is the page you analyse from here on, not the ranking one (step 7, Tier 2, point 4) |
| `the DE version: noindex` (or canonical, status, redirect) | Tier 1 on the market's version: it cannot rank, so Google shows the other language |
| `language links do not match` | The market's version does not name the ranking page, or not itself, in its hreflang links |
| `keyword not in title or H1 of the DE version` | Tier 2 candidate on the market's version, same rules as above |
| `declares no DE version` | The ranking page names no version for this market: either none exists, or its language links miss it |

**The order of attractiveness stays.** A Tier 1 flag (status, redirect, noindex, canonical) comes
first: the page cannot win as it stands, and the check is short. Any other flag only moves a
candidate ahead of neighbours that are about as attractive (within 20% in the order); it never lifts
a near-zero-volume keyword over a clearly more attractive one. The script prints the candidates in
that order: work down it. A `PATTERN` line means two or more
candidates share a flag. If they share the cause too (one series of posts, one template), that is
one change for all of them and it is reported as one quick win covering those keywords. Check that
they really share the cause before you merge them: two titles with "2024" written by hand in two
different places are two edits, still one quick win if the task is the same.

The screen orders the work, it does not decide it. A flag is not a quick win until steps 4-7
confirm it. A candidate without a flag can still be one (a promise that misses the intent, a
cannibalisation, too few internal links). If the site blocks the script ("Page not read"), read that
page from the crawl in step 4.

**Never write "head term" without explaining it.** It is jargon, and a reader who does not know it
cannot tell whether you skipped real work. Spell out what the flag means and what you did about it,
in the reader's own words — for example:

> "rendering" and "ascii-code" have ten times the search volume of the other keywords in this band.
> Big terms like these attract the strongest competitors, so moving from position 4 to the top 3 is
> a months-long project, not a quick win. That is why I did not analyse those two pages — the
> analysis budget went to keywords where a single change can plausibly matter.

The same rule holds for every term of art the report uses: **cannibalisation**, **click depth**,
**canonical**, **band**. One short clause on first use. If you catch yourself writing a label the
user would have to look up, either explain it or drop it.

### 4. Check candidates in depth until you have three quick wins

Work down the screened list. For each candidate: the SERP gate (step 2), the search intent
(step 5), the page against it (step 6) and the decision (step 7). **Stop as soon as three
candidates are confirmed quick wins, or after six candidates checked in depth**, whichever comes
first. A pattern that covers several candidates counts as one quick win.

Budget per run: six candidates in depth, six row pages from the crawl, three control pages, three
`seo_check` calls. The first five cost stored-data calls only. Do not go beyond six to fill the
slots: if six candidates yield one quick win, the report has one, and says so.

**Stop when too many positions cannot be confirmed.** When half or more of the candidates checked so
far failed the ranking-data check (and at least three did), stop checking. The report then says, in
its first lines and neutrally, that several positions could not be confirmed this time, so it shows
only the keywords that passed, and that the next ranking update is on <date> (`next_snapshot_date`
of the SERPs read). Never keep going to fill the slots on positions that fail the check.

**Read the ranking page from the crawl** (below) for a candidate you are about to report, for one
whose page the screen could not read, and for one that needs the internal-link check of Tier 3.
A candidate that already fails on the intent (mixed SERP, wrong page type) needs no crawl read.

For each of these pages, in this order:

1. `get_page_analysis(project_id, url=best_ranking_url)` — one call that returns the title,
   description, H1, canonical, noindex flag, word count, click depth, incoming internal links and
   the page's audit todos. **Use this, not `get_page_meta_tags`** — that tool returns Open Graph
   tags and has no `<title>` or `<meta description>` in it at all.
2. `get_keyword_ranked_pages(project_id, keyword_id)` only when one of these holds:
   `best_ranking_url` is empty; the SERP from step 2 holds a second own URL; an `/en/` (or other
   foreign-language) URL ranks on this market; or the user asks which page Google picked. These
   are the cannibalisation triggers for Tier 2. It lists every own URL that has ranked for
   the keyword, each with its own `last_ranking_date` — these are snapshots from different days,
   not a current SERP. Take the current position from `list_keywords`, always.
3. `get_page_headlines(project_id, url)` — which headings the page has. It returns them sorted
   alphabetically within each level, not in page order, so it shows what the page covers, not in
   which order. That is enough to judge the page type and whether it answers the intent (step 6).
   `get_page_text_blocks` only when title, H1 and headings leave the page type unclear.

**Cap it at six row pages per run**, plus up to three control pages (see the control check).
`get_page_analysis` returns a large payload. Do not spend row budget on a page you only want to
verify the existence of.

**A wrong-language candidate is read through its market version.** The ranking page (`/en/`)
comes back `CrawlUndiscovered`, which is expected and not a reason to drop it. Run
`get_page_analysis` and `get_page_alternate_links` on the "Market-language version" the screen
printed; the controls the script prints for it are from that version's section. It counts as one row
page. Only when the screen found no market version inside the crawl does the candidate drop as below.

**When the page cannot be read from the crawl, take the next candidate.** Two cases look alike:

- `CrawlUndiscovered`: the URL lies outside the crawl's scope; the analysis comes back empty.
- `display_type: "robots_excluded"` (with an `error` naming a robots block): the crawler found the page but was
  not allowed to read it. Title, description and H1 are null, `word_count` is 0 and `statuscode`
  is null — **not** a failed status, so Tier 1 does not fire, and the empty headings do not mean
  the page has no H1. Link counts are still filled; do not use them either.

In both cases there is nothing to judge on the page. Drop the candidate and take the next one (it
counts towards the six). Name the dropped keywords in the closing
lines, with the reason that applies: "<keyword> #<n>: the page is outside the crawled area" or
"<keyword> #<n>: the crawler is not allowed to read this page (robots rules)". If several of the
band's ranking pages are affected, say so once and point to `seobility-setup-check`: the crawl
scope or the crawler rules decide what Seobility can see.

### 5. Read the search intent from the SERP

The SERP from step 2 (`get_keyword_rankings`) carries URLs and domains, but no titles, and a URL
is not enough to judge intent: `/guide/roof-maintenance/` can be a price guide, a checklist or a
sales page. So read what each of the top 3 promises in the search results:

1. **Read title, meta description and H1 of each top-3 page**, in this order of routes:
   - **The script first**, all three URLs in one run. It is free and prints about 1 kB per page:
     ```bash
     python3 scripts/ranking_opportunities.py --promise <url1> <url2> <url3>
     ```
   - **`seo_check(website=url)` only for a page the script marks FAILED** because the site blocks
     scripts (403, bot wall). It reads those pages, but **is one of the expensive live calls** and
     returns 20-50 kB, so never use it for a page the script already read. A 404 or 410 needs no
     second route: the page is gone.
   - **The host's web fetch** only when both fail. It turns the page into text, so it usually
     misses title and description, but finds the main heading.

   The script prints three outcomes besides a normal read. `FAILED` with a block, a timeout or a
   dropped connection: one `seo_check`. `FAILED` with 404 or 410: no second route, the page is
   gone. `EMPTY` (a bare site name as title and no H1, typical for pages that build their content
   in the browser, such as Reddit threads): one `seo_check`; if that is empty too, classify the
   page from its URL and domain ("a Reddit discussion thread") and say it was not read. At most
   three `seo_check` calls per run; after that, classify from the URL.

   When a page has several H1s (the script lists them all), take the one that names the page's
   topic, not a navigation label ("Tutorials", "Menu"). These three fields are what the page
   promises the searcher, and they are the strongest signal of which intent Google serves with it.

   **A page counts as read when title and H1 are in hand.** A missing meta description is common
   (Wikipedia has none) and is not a failed read; say "no description" rather than "not read".
2. **Classify each page** from that promise plus its domain: guide or glossary entry, forum
   thread, tool or calculator, template or download, shop or category page, local service provider,
   directory, manufacturer, news. Judge the kind of page on the top 3 and say so ("the top 3 are …").
3. **Search intent**, in one sentence: what the searcher wants to get done — learn, compare, find
   a provider nearby, download a template, calculate, check an obligation. Derive it from the
   three promises, not from the keyword string; `intents` in the payload is a hint, not the
   answer. When the three disagree (a guide, a shop and a forum), say the intent is mixed — then a
   change of page type is a bet, not a fix.

**Stop at the promise.** Do not describe the pages' structure, depth, sections or what they answer
first, and do not read their body text. That is the content gap analysis, the deeper look.

Stored URLs are HTML-escaped: unescape `&amp;` before fetching. If a page cannot be read (bot wall,
timeout, PDF) by one route, try the other once; if that fails too, name it as not read, classify it from
its URL and domain only, and do not read the #4 page in its place. With two of three unread, say
the intent could not be read rather than guessing it.

### 6. Our page against the intent

From the screen (title, H1) and, where you read it, the crawl (headings, word count): is the
ranking page **the kind of page** the searcher is looking for, and does it say in its title and H1
that it answers that? The findings this step is built for:

- **Wrong page type:** the top 3 are local providers and the page is a nationwide hub; the
  searcher wants a template and the page is a service page; the top 3 are calculators and the page
  is an article.
- **Right page, wrong promise:** the page covers the intent, but its title and H1 name something
  else (the top 3 are about costs, the title never mentions them).
- **The right page exists, but another one ranks:** Tier 2 below.
- **A dated promise:** title or H1 carry a past year ("(2024)" on a 2026 search results page). The
  searcher reads it as outdated information. The change is to bring the content up to date and
  then update or remove the year, never to swap the year alone.

Say how many of the top 3 each point held for. A point that holds for one of three is not a
pattern. What the page should say, section by section, is beyond this skill: that is the
content gap analysis.

### 7. Decide: quick win or not

A candidate is a quick win when the data shows **one concrete change to the page or to the links
pointing to it** that addresses the gap from step 6 or one of the tiers below. From evidence in the
data, never from general SEO advice. Work down the tiers and stop at the first hit; a tier action
counts only when its evidence, and the control check where it applies, supports it.

| Finding | Quick win? |
|---|---|
| Tier 1 blocker (noindex, canonical elsewhere, status not 200, redirect) | Yes |
| Right page, wrong promise; dated promise; keyword missing from title and H1 (when most of the top 3 name it, see below) | Yes, unless the URL holds a better position for another keyword |
| Several own URLs take turns (Tier 2) and one is clearly the right owner | Yes, with the steps below |
| Wrong-language page ranking while the right one exists | Yes, if the market's version is blocked, its language links are broken, or it misses the keyword in title and H1 (Tier 2, point 4) |
| Too few internal links, confirmed by the control check (Tier 3) | Yes, with named link sources |
| Wrong page type (the searcher wants a calculator, the page is an article) | No: that is a new page, not a quick change. One line in the report |
| Mixed intent, or no on-page cause visible | No. One line in the report, with the deeper look it needs |

**When the page is already the right type with the right promise, it is not a quick win.** Do not
promote an audit todo (alt texts, empty bold tags) or a guess to get it into the three.

**Tier 1 — the page cannot win as it stands.** Report this and nothing else.

| What the data shows | The action |
|---|---|
| `is_noindex: true` | The page is excluded from the index. Everything else is moot |
| `canonical_target` points elsewhere | You are telling Google a different page should rank |
| `statuscode` is not 200 | Resolve the status before optimising anything |

**Tier 2 — the page is not aimed at the keyword.**

| What the data shows | The action |
|---|---|
| The keyword is absent from `title` and `h1_headline`, **most of the top 3 (2 of 3) name it in their title**, and our page uses no word with the same meaning | Name the keyword in the title and the H1 — unless the URL holds a better position for another keyword (see below) |
| `get_keyword_ranked_pages` returns several own URLs | Several of your own pages take turns ranking for this. Name the owner and demote the rest — steps below |
| `best_ranking_url` is not the page built for the keyword | Report the mismatch — Google picked a different page than you did |

**Before any retitle, list the other keywords the same URL ranks for** (the script prints them
with each candidate). Never retitle or re-aim a URL that holds a better position for another keyword:
serve the keyword from the page built for it, or add a section, and link to it.

"Absent" means the keyword is not _in_ the title or H1 as defined under Definitions (partly or
missing). **A missing keyword is a quick win only when the top 3 use it.** Check the top-3 titles you
read in step 5 with the same definition: when fewer than two of them name the keyword, and when our
title names the topic in other words ("Gewerbeobjekte" for "Gewerbeimmobilie", "Wartungsvertrag" for
"Wartung"), the page already promises the right thing. Then it is not a quick win; the rule "already
the right type with the right promise" applies.

**"Decide which page owns it" is not an instruction anyone can act on.** Whenever
`get_keyword_ranked_pages` returns more than one own URL, write out the concrete steps instead. The
tool gives you each URL's `rank` and `last_ranking_date`, which is enough to say who the candidate
owner is and what follows:

1. **Name the owner.** Take the URL that is the right page type for the search intent from step 5
   — a definition page for "what is X", an article for "how do I X", a template page for "X
   template"; among those, the one that has ranked best and most recently. List the competing URLs
   explicitly so the user sees what is at stake.
2. **Say what happens to the others.** Each losing page either targets a different keyword (rewrite
   its title and H1 so it stops competing), or links to the owner with the keyword as anchor text,
   or is merged into the owner and redirected. Recommend one per URL, with a reason.
3. **Point the internal links at the owner.** `get_pages_using_anchor_text(project_id, ...)` shows
   which pages currently link with that anchor. Links pointing at the losers are the mechanism
   keeping them alive in the SERP. Anchors are stored lowercase and matched exactly, so lowercase
   the anchor before the call; an empty result for a mixed-case anchor means nothing.
4. **Language pairs are their own case.** An EN page ranking on Google.de while a DE page exists
   means Google prefers the wrong page for these searchers. The DE page is the one built for the
   keyword, so every check runs on it, never on the EN page. Never retitle the EN page for a German
   market. Work down this list and stop at the first hit:
   1. **The DE page is blocked** (`twin-blocked` in the screen, or `is_noindex`, a canonical
      elsewhere, a status other than 200 in `get_page_analysis`). Tier 1: Google cannot show it,
      so it shows the EN page. The quick win is removing the blocker.
   2. **The language links are broken.** `get_page_alternate_links(project_id, url)` on the DE page
      lists its declared language versions (`get_page_analysis` only gives a verdict and a count).
      The EN page must be listed, and the DE page must list itself for `de`. The screen has already
      read the EN side live (it found the DE page through it). If either side is missing, the quick win
      is fixing the language links on both pages. When several candidates share it, it is usually
      one template or plugin setting: one quick win.
   3. **The DE page does not name the keyword** in title or H1 (common when the German page uses a
      German term: "Strukturierte Daten" for "structured data"). Tier 2 retitle of the DE page, with
      the retitle guard above: check the other keywords the DE page ranks for first.
   4. **The DE page gets too few internal links.** Tier 3, with the controls the script printed for
      the DE section, same threshold.
   5. **None of these.** The language links are in order and the DE page is aimed right: do not
      tell the user to rewrite a page that is fine. Verdict **Deeper analysis needed**, on the DE page,
      and one "worth checking" line: whether the EN page is much stronger than the DE page (far more
      words or backlinks). That would be a possible factor for Google showing it despite correct
      language links. It stays a question until checked.

   If the ranking page declares no version for the market, look for the topic in the crawl before
   you conclude anything. No DE page on the topic means **New page needed** (a German version of
   this page). A DE page that exists but is not linked is case 2.

Never recommend deleting a page. And say plainly that consolidating can cost the positions the
losing pages already hold — it is a trade, not a free win.

**Tier 3 — the page is aimed right but unsupported.**

One rule, and it does not fire without the control check below.

| What the data shows | The action |
|---|---|
| `incoming` internal links under half of the **lowest** value among at least two control pages of the same page type | Link to this page from named pages (below) |

"Clearly below" means that threshold, not a gut call: 3 incoming links against controls with 8, 13
and 8 fires; 6 against 8, 13 and 8 does not. With fewer than two controls of the same type, the
rule does not fire.

**Name the link sources.** "Link from pages that already rank" is not a task. Take two or three
own pages from the `list_keywords` payload that rank in the top 10 for a keyword sharing a word or
topic with the candidate, and name them with their URLs. Check with `get_page_outgoing_links` that they
do not link to it already.

**If the rule fires on several candidates, it is one quick win.** Three separate "add internal
links" blocks read like a template. Write one block for the finding ("these pages get far fewer
internal links than your pages that already rank") with the link sources per page.

**Otherwise, say there is nothing — and then say where else to look:**

> "No technical or on-page problem visible. The page can be indexed, names the keyword and is
> linked internally. Possible differences to the pages in front lie in content or links, which
> needs the deeper analysis."

This is a correct result, and on a well-kept site it is the **most common** one. It is the reason
the skill screens ten candidates instead of reporting the first three. A report that finds a cause
on every candidate is a report that went looking for one.

These candidates go into the closing list, one line each, not into a quick-win block. A line that
only says "nothing on-page" reads like a dead end, so name possible factors instead, each with the
check that would look at it. One or two that actually fit the keyword, never the whole
table, and keep them as questions, never findings:

| Possible factor | How it shows up | What looks at it |
|---|---|---|
| The SERP wants a different kind of page | Dictionaries, Wikipedia, forums, shops or a same-named brand hold the top spots | Already in hand from step 5 |
| Authority gap on this specific page | The pages that outrank the user carry far more referring domains | `get_page_backlinks` for the user's page, `seo_check` for theirs — identify them from the real SERP, not the tracked competitor list |
| Thin coverage against what ranks | The page is long enough but misses terms the top 10 all cover | `tfidf_check` (one of the expensive live calls, 35-45k characters inline) |
| Staleness | Competing snippets carry recent dates, yours does not | Snippet dates in `get_keyword_ranked_pages` |
| The keyword is somebody's brand or a different word sense | "markup" is also a company and a pricing term | Visible in the ranking URLs |
| The click is going to an AI Overview | `ai_overview` is set on the row in the `list_keywords` payload | Already in hand — `get_keyword_ai_rankings` for detail |
| The other language's page is stronger | An `/en/` URL ranking on Google.de although the DE page is linked correctly and aimed right | Word count and backlinks of both pages: `get_page_analysis` on the DE page, `get_page_backlinks` on both |

Phrase them as "worth checking", with the check named in plain words and offered, never as a tool
name: "Worth checking: whether the pages above you have far more backlinks. I can compare that
if you want." When the same check applies to several keywords, write it once with all of them. The
moment you write one of these as the
reason without running its check, you have broken the control rule two sections down — the whole
point of that rule is that a plausible story is not evidence.

The verdict for these keywords is **Deeper analysis needed**, and the next step is the deeper look
at the end of this file, so the offer is one you can keep.

### The control check — required before naming any measured value as the cause

A number is only a cause if it separates winners from losers. Before writing any action that
rests on a measured value — internal links, click depth, word count, page score — pull
`get_page_analysis` for two or three pages **in the same project that already rank in the top 3**
and compare. If the winners show the same value, you have found a site-wide trait, not a cause.
Write "no on-page cause visible" instead.

Get the control pages from the same `list_keywords` payload you already have: filter `rank <= 3`,
`rank_type: organic`, and pick ones whose `best_ranking_url` is the same kind of page as the rows
you are explaining. The script prints up to three per candidate from the same URL section, preferring
pages at the same URL depth (a post next to posts, not to its category page). When candidates share a
section, they share controls: the script says so, and you pull each control page once per run.
With one control page or none, no comparison is possible: say so, and name no measured value as a
cause.

**Never benchmark against the project maximum.** `incoming.max` and `outgoing.internal.max` are
whatever the site's largest hub holds — a main page, an index, a category listing. A leaf article
measured against a hub always looks starved, so the rule fires on every row and the report
collapses into "add internal links", ten times over.

The failure this prevents looks like this. A set of pages just outside the milestone each carry a
handful of incoming internal links, against a project maximum in the hundreds. Every row looks
starved, so every row gets the same action. Then the control group is pulled, and a page already
holding position 2 turns out to have fewer internal links than any of them — along with the same
short H1 and the same unused title words. The trait was never a cause. It was just what a page on
that site looks like.

Template-built sites make this especially likely: every page shares a layout, so every page shares
its flaws, and the audit surfaces them on winners and losers alike.

The control costs at most three calls. Spend them — a wrong action costs the user a week of work
on the wrong thing, and it is the kind of error they will catch.

**The control check never appears in the report.** It is how you decide what to write, not
something the reader needs to follow. A paragraph explaining that "Relaunch" has 4 internal links
and "Viewport" has 9 asks the user to re-derive your reasoning from two pages they did not ask
about — and it reads as if those control pages were the finding. Do the check, let it silently
remove the actions it disproves, and report only the conclusion it produced: an action, or "nothing
to change here".

The one exception is when the user asks how you arrived at a row. Then show the comparison.

### What is not an action

**Audit todos are reported, but they are not the reason for a position.** A page can sit outside
page 1 with thousands of words, the keyword in title and H1, and still carry a couple of
`important` todos — images without alt text, a duplicate heading. Offering those as *the* quick win
for that keyword would claim a cause you have not shown.

So they never fill a quick-win slot (Tier 1 blockers excepted), and they are never dropped either:
every `important` or higher todo of a page you checked in depth goes into the report's section
"Technical problems from the Website Audit", explained in plain words. The user asked to see what
the audit found; leaving it out because it does not explain the ranking would hide a real finding.

Scope them right. An empty `alt` counts as missing alt for SEO, but an image that sits on nearly
every page (a logo in the header) is one template edit, not a per-page task: give it a
descriptive alt such as the brand name; `aria-hidden="true"` may stay. A title or description
over its pixel limit is a real finding, because the limit is the SERP cutoff — no tolerance band.
Quote the pixel limit, not a character count, and rate the effort low (usually one word).

The same goes for a missing meta description: worth reporting, but it does not move a position. It
affects whether people click the result you already have.

**A side finding has to pass one test: does the reader now know something they can act on?**
Side findings are welcome when they do. They are not a place to park every number the payload
happened to contain.

The failure looks like this: "All ten keywords trigger an AI Overview. Seobility is cited as a
source in six of them (ascii-code at 2, rendering at 3, expired domains at 6 ...)." Every word is
true, and the reader is left holding a list of figures with no idea what to do with them — plus an
implication that the pattern means something you never stated.

The same data can earn its place, if you do the interpreting:

> Four of these keywords show an AI Overview that does not cite us — markup, 404 not found, meta
> description and anchor tag. On those, a better position wins less traffic than it looks like,
> because the answer sits above the results. Worth a look if AI visibility matters as much as
> rankings here.

So: before writing a side finding, say what follows from it. If nothing does, cut it. This holds
for every metric in the payload — visibility, CPC, competition, intent percentages — not just AI
Overviews.

## Output

The reader is usually not an SEO expert, and they did not watch you work. Before they see a single
result they need to know what was looked at and why, and every result has to read as something
about *their keyword*, not as a verdict on your analysis. A report that opens with "none of the six
keywords has a change that would close the gap" fails both: the reader does not know what "the
gap" is, which six, or whether that is good or bad news.

The report has this order. Keep the headings, in the user's language.

**1. What this is.** Three or four plain sentences under a heading such as "Where you are close to
the next step". Say:

- what was looked at: the keywords from the project's Ranking Monitoring that sit just behind the
  top 3 (positions 4-10) or just before page 1 (positions 11-20), where a move up makes the most
  visible difference;
- how many: "<m> keywords are in your Ranking Monitoring, <n> of them are on positions 4 to 20. I
  took the <k> that are closest to the next step, and checked them one by one";
- what was checked for each: whether the ranking page has a technical problem (in the Website Audit
  and on the page itself), whether it names the keyword in its title and main heading, and what the
  three pages in front of it promise searchers in Google;
- the date of the positions and of the crawl.

> **Where you're close to the next step**
> Your Ranking Monitoring has 335 keywords, and 74 of them are on positions 4 to 20: just behind
> the top 3 or just short of page 1. I took the 6 that are closest to their next goal and checked
> each one: Does the page have a technical problem? Does it name the keyword in the title and main
> heading? And what do the three pages ahead of you on Google promise? Positions from
> 30 September 2026, Website Audit from 25 September 2026.

**2. The result in one or two sentences**, as what the user can do next, never as a bare "none":

> For 2 of the 6 keywords there's a concrete change you can make right away (guides below). The
> other 4 pages are technically fine. Possible differences from the pages ahead of you lie in the
> content or the links, and only a deeper analysis can show those.

When no candidate is a quick win, say what that means in the same way: the pages are technically in
order, so possible differences to the pages in front lie in content or links, which the deeper
analysis looks at. That is a correct and useful result. Never invent a quick win to avoid it.

**3. The overview table**, every candidate you checked in depth, in the order you checked them:

> | Keyword | Position → next step | Searches/month | What I found | What to do |
> |---|---|---|---|---|
> | <keyword> | 4 → top 3 (1 position away) | <volume> | <one plain sentence> | **Quick win** (guide 1) |
> | <keyword> | 12 → page 1 (2 positions away) | <volume> | <one plain sentence> | **Deeper analysis needed** |
> | <keyword> | 7 → top 3 (4 positions away) | <volume> | <one plain sentence> | **New page needed** |

"What I found" is one sentence the reader understands without SEO background: what is wrong, or
what the pages in front of them are ("The three pages in front of you are definitions, just like
yours, and your page has no technical problem"). If the Website Audit lists a problem for the page,
it is named here in plain words (see "Technical problems from the Website Audit" below). No labels
the reader would have to look up: write "Google shows German searchers the English version of your
page", not "wrong-language", "hreflang" or "EN page ranks on Google.de".

Directly under the table, explain the three labels, one plain line each:

- **Quick win:** there is one concrete change to the page (or to several pages at once) that fixes
  a visible problem. The step-by-step guide is below, numbered as in the table. A pattern is one
  quick win: its keywords share one number.
- **Deeper analysis needed:** the page is technically fine, names the keyword and is the right kind
  of page. Possible differences to the pages in front lie in their content or in how many other
  sites link to them, and that needs a closer comparison (see "Next step").
- **New page needed:** searchers want a different kind of page than this one (a calculator, a local
  page, a shop), or the pages in front are a different kind of page than this one can become.

Then one line with the other promising keywords that were screened but not checked in depth, each
with position and volume, so the reader keeps the overview: "Also close to the next step, not yet
checked in depth: hidden content (#4, 50 searches), digital analytics (#11, 50), …"

Wherever the report names a volume, 0 or none reads "<10", never "0".

**Wrong-page side note.** When the script prints a "Worth knowing" line (three or more tracked
keywords rank with a different page than the one built for them: another city's page, a tool page, a
reference page), add it as one line under the table, in the user's language, with at most three
examples:

> Worth knowing: N keywords rank with a different page than the one you built for them (e.g. "<kw>" →
> <page>, …). That is not a quick win on its own; it usually means internal links or titles point Google
> to the wrong page.

Never a row, never counted as an opportunity. When you read an inline payload by hand, apply the
script's test: another page of the site is built for the keyword (its URL slug is made of the keyword's
words and carries all of its distinguishing ones, the place and not the service word that many tracked
keywords share), but the ranking URL carries none of the distinguishing words.

**4. The guides:** up to three quick-win blocks, in table order. Each block is a guide someone can
follow without asking back:

> **1. <keyword>** · position <n> (next milestone: top 3 | page 1) · <volume> searches/month · <market> · <ranking URL>
> - **What the searcher wants:** one sentence.
> - **What ranks:** the top 3 in one line: page type and what their titles promise.
> - **The problem:** what is wrong with the page, in plain words, and why it matters for this
>   keyword, as a possible factor, never as the reason for the position. Explain the problem before the fix, so a reader without SEO background understands
>   what they are changing and why.
> - **The change:** numbered steps, each a task. Write out the concrete text wherever there is
>   one: the proposed new title and H1, the pages to link from with the anchor text, the canonical
>   target. Give one proposal, not a menu.
> - **Leave alone:** only when something must not be touched ("keep the URL: it also ranks #3 for
>   <other keyword>").
> - **How you'll see it:** where the effect shows up in Seobility (Ranking Monitoring after the next
>   ranking checks, the Website Audit after the next crawl). No forecast of a position or a date.

A **pattern** (one change, several pages) is one block. Its header lists every keyword and URL it
covers, and "The change" says where the one change is made (the template, the series, the setting)
and then lists each page with its proposed text. For example:

> **1. One fix for three pages: the year in your "<CMS> SEO check" series** · wordpress seo #5,
> wix seo #7, shopify seo #6 · example.com/blog/…
> - **The problem:** all three titles and H1s end in "(2024)". Someone searching in 2026 reads that
>   as a two-year-old test, while the top 3 for each keyword promise current instructions.
> - **The change:** 1. Check each test against the current version of the system and update what
>   changed. 2. Then change the titles to … (one line per page).

**5. Technical problems from the Website Audit.** For every page you checked in depth whose
analysis lists audit problems (the page's todos, `important` and above), name them here, per
page: what is wrong, in plain words, why it matters, and what to do. Problem before fix, as in the
guides. A problem the audit flags on all the checked pages is one site-wide item, not one per page.
Never wave a finding away and never call it "hygiene" or "not relevant": Seobility flagged it, so
the reader gets it, explained. What you must not do is present it as *the reason* for the position
(see the control check). Say it the honest way: "Worth fixing in any case. Whether it affects the
position cannot be measured." If no checked page has audit problems, one line says so,
because that is part of what was checked: "The Website Audit shows no problems for these pages."

**6. Worth checking:** one line per check that fits the "Deeper analysis needed" keywords (from the
candidate table in step 7), with the keywords it applies to, phrased as a question and an offer.

**7. Next step:** the deeper analysis for the "Deeper analysis needed" keywords (see "The deeper
look"), and the offer of the rest rather than doing it: the next candidates, or a full audit triage
for pages with real technical work. A deep dive is one of the more expensive runs, mostly for one
comparison of the page with the pages in front: say so when it helps the user decide, never with a
credit figure. A low or missing volume never stops the offer: the user decides.

**8. What this is based on**, at the end of the report, at most five short bullets
in plain words:

- The date of the positions and of the stored search results. The position comes from
  `last_update` of `get_keyword_overview`; the stored search results are refreshed less often
  (their payload names only `next_snapshot_date`), so write "search results as stored before
  <next_snapshot_date>" when the two may differ, not a date you cannot back.
- Which markets the results come from.
- The counts: monitored, ranking, on positions 4-20, screened, checked in depth, and the rest in
  one phrase ("<n> more on positions 4-20, not looked at yet").
- Keywords left out, by name, each group with its reason in a plain sentence: positions that could
  not be confirmed ("moved 77 places in one check; I could not confirm the position, so I left it
  out"), the very big terms
  (explained as in step 3, never as "head terms"), keywords whose page is outside the crawl, and
  the count of keywords where Google shows the other language's page that the screen did not reach.
- One sentence on what this cannot see: keywords that are not in the Ranking Monitoring.

**No hand-off block in the report by default.** The block below is written only when the user asks
to pass the report on for later (another session, a colleague). See "The hand-off block".

**Each step has to survive being read on its own.** The user copies these into a task list, where
no surrounding paragraph travels with them. "Decide which page owns it", "improve the page",
"strengthen internal linking" all fail that test: they name a topic, not a task.

**A step changes something on the page or in the links pointing to it.** Three things are not
steps:

- **An investigation.** "Look through the page history since July to see why it dropped" is a
  ranking-drop diagnosis, a different job. If the data points there (the right page once ranked
  much better), say so in its "Worth checking" line and name it as a possible next step.
- **"Change nothing."** Advice not to touch something goes in "Leave alone".
- **A task for the user to check what the skill could have checked.** If a tool can answer it,
  answer it; if not, it is a "worth checking" line, not a step.

**Audit problems stay out of the quick-win guides** unless they are a Tier 1 blocker. They have
their own section (5), where they are explained, not dismissed.

**No tool names in the report.** `get_page_backlinks`, `seo_check`, `ranking_opportunities.py` and the like are
how you worked, not what the reader does. Write what was checked in plain words ("the backlinks of
the pages above you"). The same holds for field names and payload terms.

Never write a block that implies you looked when you did not: a page you could not read is named
as not read.

**No SEO shorthand in the report.** Words such as SERP, intent, band, head term, hreflang,
canonical, cannibalisation or click depth either get one short plain clause on first use or are
replaced by what they mean ("the search results", "what searchers want", "several of your own
pages compete for the same search").

Write the report in the language the user is writing to you in. It is an internal analysis they
read at their desk, not a deliverable that ships.

### The deeper look

The keywords with the verdict **Deeper analysis needed** need what this skill deliberately does not
do: compare the user's page with the pages that outrank it in content, links to the page, strength
of the website and on-page score. If `seobility-competitor-gap` is available in this session, name it
as the next step for exactly those keywords. When it runs in the same conversation, it takes what this
run established (positions, kind of page, page check, ranking-data check) from the conversation; no
block is needed. In the report, describe it in plain words ("a closer comparison with the pages in
front of you: content, links and the strength of the website"), not by its name. If it is not
available, name the same comparison as the next step and say that the `seobility-competitor-gap`
skill does it. Do not run the comparison inside this skill.

#### The hand-off block

Only when the user asks to hand the report on for a deeper look later (in another session, or to a
colleague), give them one HTML comment to paste along with it, so the deeper look starts from what is
already established instead of redoing it. Never put it into the report by default: readers see it as
a block of code in many apps. One `kw=` line per keyword marked "Deeper analysis needed":

```
<!-- seobility-handoff v1 ranking-opportunities
project=<id> | market=<search engine name> | device=<desktop|mobile> | rankings_as_of=<YYYY-MM-DD>
kw=<keyword> | keyword_id=<id> | position=<n> | url=<ranking url> | volume=<n or <10> | intent=<one line> | kind_top3=<kind of page> | onpage=<ok or the issue> | data=<confirmed or not confirmed: reason>
-->
```

Fill it from what the run established, nothing new:

- `project`, `market`: the project and the keyword's search engine. Keywords from several markets get
  one block per market. `device` is named by `get_keyword_overview`, in lower case. `rankings_as_of` is
  its `last_update` date.
- `position` is today's position from `list_keywords`; `url` is the ranking URL of that position,
  unescaped. For a wrong-language row it stays the page that ranks; name the market-language page
  that was analysed in `onpage`.
- `volume` is the number, or `<10` for 0 or none.
- `intent` is the search intent of step 5 in one line; `kind_top3` is the kind of page of the top 3
  only (see Definitions).
- `onpage` is `ok` when the crawl read of the page showed no problem (the "no technical or on-page
  problem visible" case), otherwise the issue in a few words; `not read` when the crawl was not read.
- `data` is `confirmed` once the keyword has passed the ranking-data check. A keyword marked "not
  confirmed" is handed off only when the user asks for the deep dive anyway, as `not confirmed: <reason>`.
- No value contains `|`, `--` or a line break.

## Guardrails

- **Never promise a position or traffic.** Not "this will get you to page 1", not "worth ~400
  visits". The data does not support it and the user will hold you to it.
- **Never present the opportunity score as a number that means anything on its own.** It sorts
  rows. That is all it does.
- **Never name a cause.** Not for the user's position and not for a competitor's, and not in the
  negative either. A measured value is a possible factor at most, and only after the control check;
  without it, it is not even that. "No technical or on-page problem visible" is always the safer
  answer, and usually the true one. Read the finished report once for "because", "that's why",
  "the reason", "this is due to" and the same words in the report's language before you hand it over.
- **Never change anything.** This skill is read-only: no `add_keywords`, no `start_crawl`, no
  settings. If the tracked set is too small, say so and let the user decide.
- **Local pack is off unless asked.** Local-pack positions are not organic positions; mixing them
  silently makes a report wrong in a way nobody can see.
- **State the ranking date.** A position from a check three weeks ago is not today's position.
- **Never gate by search volume.** A volume of 0 or none is a data gap ("<10", counted as 5), not proof
  of no demand. Never drop, block or refuse a keyword or a deep dive because of it; the user decides.
- **Never state a credit cost**, per call or per run. Name a call as "one of the expensive live
  checks" when the user needs to know.
