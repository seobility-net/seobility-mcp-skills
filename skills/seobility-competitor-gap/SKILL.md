---
name: seobility-competitor-gap
description: >
  Compare one page with the pages that outrank it for one keyword and show where the page is
  behind, level or ahead: possible factors, never claimed as the cause of a position, ending in
  a ranked list of suggested improvements with evidence. Use when someone asks "why does the competition rank better", "why are the pages
  above me ahead", "what is my page missing", "content gap for this keyword", "compare my page
  with the top 3", "what do the competitors do differently",
  "content gap analysis", or the same in any other language;
  also as the deeper look for keywords that seobility-ranking-opportunities marked "Deeper
  analysis needed", and for planning a new article. Do NOT trigger for
  finding which keywords are worth working on (seobility-ranking-opportunities), a site-wide
  audit (seobility-audit-triage), keyword research for a topic without a target page, a backlink
  analysis of a whole domain, or writing the content itself.
---

# Competitor gap: how your page compares with the pages above it

For **one keyword and one of the user's pages**, this skill compares the page with the pages that
outrank it in every area the Seobility MCP can measure, shows in which areas the page is behind,
level or ahead, and ends in a ranked list of suggested improvements. Every suggestion carries its
evidence in plain words ("all three pages above you have a section on this, and people search for
it") and a concrete place where it goes.

**This skill shows possible factors, never causes.** Google ranks on many signals, most of which
nobody outside Google can see, and no comparison of four pages can prove why one of them ranks
higher. A difference this skill finds is a *possible factor* and a suggestion worth trying, nothing
more. That holds for every sentence of the report, including the short answer:

- Never: "this is why you rank lower", "because", "the reason is", "this holds your page back",
  "that's why", "that's why the competition ranks higher", and never the negative form either
  ("that's not the reason", "that does not explain it").
- Never a promise or a forecast: no "if you add this, you will reach position 3", no "this will
  get you onto page 1", no traffic estimate.
- Instead, describe the difference and offer the improvement: "In this area your page is behind
  the pages ahead of it", "a possible factor", "This is something you could improve", "You have
  no disadvantage here".

The method follows the Seobility guide "Why are my competitors ranking higher on Google?"
(https://www.seobility.net/en/blog/why-is-my-competitor-ranking-higher/): on-page optimisation matters, but it
is one factor among several. The areas, cheapest first:

| Area | What the skill compares |
|---|---|
| **Kind of page** | Which kind of page Google shows for the keyword (guides, shops, tools, glossaries …) and whether ours is that kind |
| **On-page and technical** | The SEO score of ours and the pages compared, server response time, and for a project page whether it can be indexed and what the Website Audit lists |
| **Content** | Topics, format, depth, FAQ, structured data, freshness, what people search around the keyword |
| **Links to the page** | How many other sites link to each page, and which strong sites link to the competitors |
| **Strength of the domain** | The domain score of each site |
| **The user's own site** | Internal links to the page, and other own pages that compete for the same keyword |

**An area where the page is not behind is a result too.** When a page above has a lower SEO score,
fewer links or a weaker domain than ours, our page has no disadvantage in that area against that
page. Say it plainly ("Position 2 has a lower SEO score than you: you have no disadvantage
here"). It points the effort at the areas where the page is behind and saves the user work on
the wrong thing. It says nothing about why the other page ranks where it does.

**Term statistics are one input, never the headline.** Users have told us plainly that a TF\*IDF
list on its own helps them little. What they want is the comparison and what follows from it.

## What this skill can and cannot see

- It compares **what can be measured**: the pages as a script reads them, the Seobility scores and
  the link data. It cannot measure how good a text is. A section on four competitor pages is
  evidence that searchers expect the topic, not that it is well written.
- It **cannot see** how visitors behave (time on page, going back to the search results), page
  experience beyond server response time (Core Web Vitals), or how long a site has built trust with
  Google. The report names these as not visible, with the place where the user can check the first
  two for their own page: Google Analytics for engagement, PageSpeed Insights for Core Web Vitals.
- It never predicts. No position, no traffic, no "this will get you into the top 3". It says where
  the pages differ, not what Google rewards them for.

## Before you spend a call

The helper scripts named below live in this skill's folder (`${CLAUDE_SKILL_DIR}` in Claude Code).
Run them as `python3 <that folder>/scripts/<script>.py`, wherever the current directory is.

1. **Keyword, page, market.** Take them from the request or from the hand-over of
   `seobility-ranking-opportunities` (keyword, position, ranking URL, market; see "The hand-off
   block" below). The market is a
   search engine name such as `google.de`. If the page is in a Seobility project, the market of the
   monitored keyword is the one to use. Otherwise infer it from the page's language and domain, and
   ask only if both are unclear. Term data does not transfer between markets.
2. **One to three keywords per run.** The term analysis is one of the expensive live calls. Run it
   once per keyword, never twice for the same keyword and market, and never "to see if it changed".
   If the user asks for more than three keywords, ask which three to do, or take the three closest
   to the user's next milestone, and offer the rest.
3. **Cost.** A deep dive is one of the more expensive runs: the term analysis is one of the
   expensive live calls, and each SEO score is a live call too. You may say so, for example before a
   run on several keywords, but never with a credit figure; the decision stays with the user. Call
   `get_credits` only when the user asks about the balance or it is visibly low in an earlier
   response (the live tools return the remaining balance in their `credits` field).
4. **Project context, if there is one.** `list_projects` resolves the project when the page belongs
   to one. The project adds the crawl data of our page (indexability, audit findings, internal
   links, own competing pages); the rest of the skill works on any public URL.
5. **Search volume never gates a run.** A volume of 0, or one that was not measured, is a data gap,
   not proof that nobody searches; ultra-long-tail keywords can convert very well. Show it as
   "<10" (never "0" or "no searches") and count it as 5 in any arithmetic. Never refuse, discourage
   or skip a keyword or a deep dive because of low or missing volume.

### The hand-off block

When `seobility-ranking-opportunities` ran earlier in the same conversation, take the same fields
from what it established there (project, market, device, keyword id, position, URL, intent, kind of
page of the top 3, page check, ranking-data check) and apply the rules below to them; it writes no
block in that case. When the user pastes a report from elsewhere, it can carry an HTML comment that
starts `<!-- seobility-handoff v1 ranking-opportunities` and holds `project`, `market`, `device`,
`rankings_as_of` and one `kw=` line per keyword (one block per market; read each). Then:

- Take the project, market, device, keyword id, position and URL from it. Pass `device` to
  `tfidf_check` (`get_keyword_rankings` and `get_keyword_overview` take no `device` and return
  desktop data; with a mobile hand-off, say so), and state `rankings_as_of` as the date of our position.
- Take `intent` and `kind_top3` as the starting point, then check them against your own comparison
  set, and say in one sentence where they differ (for example, the rest of page 1 is mixed).
- Reuse `onpage=ok` for our page when the crawl is the same, instead of re-deriving it.
- When `data=not confirmed`, say neutrally in the first lines that the position could not be
  confirmed, and continue only because the user asked. Never refuse.
- Without the block, behave as before: keyword, page and market come from the request.

### Check the ranking data before you use it

> **Check the ranking data before you use it.** Mark a keyword as suspect, and do not base an action on
> it, when any of these holds: the own URL appears more than once in the same SERP; a contiguous block at
> the top of the SERP is all "new" (`rank_change` 1000); `list_keywords` and the keyword's own SERP
> snapshot (`get_keyword_rankings`) disagree on the own URL's position (never compare with
> `get_keyword_ranked_pages`: it returns the best-ever position, not the current one); three or more
> other sites appear twice in the SERP; the keyword moved 30 or more places in one check; or it was added (`date_added`) inside the comparison window. Name
> suspect rows as "not confirmed", never as findings. The weekly view compares Monday to Monday, so a run
> on another weekday can legitimately differ from the latest-vs-previous view.

For one project keyword, read `get_keyword_overview(project_id, keyword_id)` (about 500 characters:
position, `rank_change`, `date_added`; it stands in for `list_keywords`, which has no keyword
filter and returns the whole project) and its snapshot with `get_keyword_rankings` before step 1,
unless the hand-off already says `data=confirmed` for it. Use `list_keywords` only when it
is already in hand. Without a project, only the checks the data allows apply (the own URL twice
in the `tfidf_check` results). A suspect keyword is named "not confirmed" in the first lines of the
report; the run continues because the user asked for it, and never ends in a refusal.

**How it reads in the report.** One line per keyword: "I could not confirm this position, so I did
not assess it". The check is how you decide what to assess; its details stay out of the report.

### Definitions

> **Keyword in title or H1.** Normalise both strings (lower case; ä→ae, ö→oe, ü→ue, ß→ss; hyphens and
> punctuation as spaces). The keyword is _in_ the title when every word of it appears, in any order;
> _partly_ when some words appear; _missing_ when none do. Inflected forms of the same word count as
> that word (singular and plural, verb and noun forms such as "kosten" and "kostet").
>
> **Kind of page.** Judge it on the top 3 results and say so ("the top 3 are …"). When positions 4–10
> look different, add one sentence ("the rest of page 1 is mixed: …"). Never mix the two in one verdict.
>
> **Search volume.** A volume of 0 or none is shown as "<10" and counted as 5. It is a data gap, not
> proof that nobody searches.

`competitor_gap.py pages --keyword` applies the first definition.

## Method

### 1. The search results and the term weighting: one call

```
tfidf_check(search_term=<keyword>, search_engine=<market>, website=<our URL>)
```

It is the most expensive call of the run and the one to keep. Its term weighting, the word counts and the
link counts of every page are the part nothing else provides. When the hand-off already
gives the kind of the top 3 (`kind_top3`), do not derive it again in step 2. The stored SERP of a
project keyword (`get_keyword_rankings`) is a cross-check of order and domains, not a source of
kinds. It takes no `device` parameter and returns desktop data.

Leave `serp_depth` at its default of 10. It decides how many competitor pages the term bands are
built from; a smaller depth changes the verdicts and does not make the call cheaper. Never pass
`calculation_result_limit`, the deprecated alias for the same thing. Without `website` (a page that
does not exist yet) you get the competitor side only: see "New article" below.

The response carries four parts you use:

- `results`: the live top 10, each with `rank`, `domain`, `url`, `title`, `description`,
  `word_count`, `load_time` (server response in seconds), `crawl_error` and the page's `backlinks`
  and `referring_domains`. This is the SERP of record for the whole run.
- `stats`: one row per term, with `avg_tf_idf_used` (its weight among the pages that use it),
  `occurrences` (on how many of the pages), and `url_tf` (its weight on our page; `0` means our page
  never uses it).
- `term_suggestions`: about 20 core terms with a `usage` verdict for our page (`perfect`,
  `not_often_enough`, `too_much`).
- `target_url_results.tf_idf`: every term found on our page.

It usually arrives **inline** (35,000 to 45,000 characters). Read it there: the top 10, the
`term_suggestions` verdicts, and the `stats` rows with `url_tf: 0`. Do not copy it into a file to run
the script on it. If the host saved it to a file, run:

```bash
python3 scripts/competitor_gap.py tfidf <saved-file>
```

**Read the term data with these traps in mind** (all verified, see `references/tool-notes.md`):

- **`current_keyword_use_count` is not a count.** It holds our page's weight, while
  `min_keyword_use` and `max_keyword_use` are counts. Never write "you use it 6 times, competitors
  76-149". Use the `usage` verdict only.
- **Hyphenated compounds are their own term.** A page that writes "Image SEO" shows `url_tf: 0` for
  "image-seo". When every part of a hyphenated term is on the page, it is not missing.
- **Inflections and synonyms count as present.** "guides" is covered by "guide",
  "guest article" by "guest post", "alt tag" by "alt attribute". The script catches inflections;
  synonyms are your judgement.
- **One or two pages is at most two sites' vocabulary.** A term with `occurrences` of 1-2 is usually
  a brand, a city, an author or a product of one or two competitors ("hubspot", "berlin", "llc"). It
  is a finding only as a deliberate bet (see "Confidence").
- **Place names are never a gap**, whatever their `occurrences`. In a local result list "hildesheim"
  or "niedersachsen" can sit on four pages. The script flags terms that name a place in the results'
  titles or descriptions ("in Hildesheim"), and terms that are part of a competitor's domain name
  (a place or a brand: check which).
- **The same URL twice in the top 10** counts its terms twice. The script names such duplicates;
  read `occurrences` for those terms as one page fewer, and compare the page once.
- **Generic words are not topics.** "wichtig", "besonders", "better", "proper". If a term could not
  become a heading, drop it.
- **Pages with a `crawl_error` were not analysed** (forums, video pages). They count in the SERP
  picture, not in the term data.

### 2. Kind of page: read the search results before anything else

If the hand-off gives `kind_top3`, start from that and classify only what is still missing
(the pages below the top 3, the pages not yet typed). Then check it against the comparison set and
say in one sentence where they differ. Without it, classify from `results`.

From `results`, classify each of the ten: guide or article, listicle or checklist (a number or
"checklist" in the title), **local service provider** (a business's page for a service in a place,
built to get a call or a quote request: a city or region in title or address, "Angebot anfordern",
a price "ab ..."), service or agency page (nationwide, no place), shop or marketplace, tool, forum or
Q&A, video, glossary or encyclopedia entry, official documentation, news. Then answer, in one
sentence each:

- **What kind of page ranks here?** Say it for the top 3 first ("the top 3 are guides"), then count
  the rest in one sentence ("the rest of page 1 is mixed: 3 guides, 2 shops, 1 forum, 1 video").
- **Is our page that kind?** If the top 3 are not the same kind as ours, the biggest difference is
  the **kind of page**, not its content. Say so first. Changes to the page can still be worth
  making, but the list gets shorter. A mixed rest of page 1 is context, one sentence, not this
  verdict.
- **Do the results depend on the place?** When three or more of the top 10 name a place in title or
  address, or several pages come from one or two local providers, say so in one sentence: Seobility
  fetches these results without a location, they look like the results for one region (name it),
  and in another city the list can look different. Place names are never a gap for our page
  (step 1 and "What not to recommend"). `competitor_gap.py tfidf` prints the places it found.
- **Are the top 3 local providers and ours a guide?** Then that is the kind-of-page verdict: Google
  mostly shows businesses to hire here. Say it first. A guide can still answer what those pages do
  not (costs, steps, what to watch for); never suggest turning it into a provider page.
- **Does a buying intent sit next to the informational one?** A keyword whose "buy", "cost" or
  "agency" variant has as much search volume (step 5) as the keyword itself splits the results. A
  guide cannot become a shop; it can answer the buying question honestly (costs, risks,
  alternatives), which is often what the guides above it do.

Then pick the **comparison set**. It depends on where our page stands:

| Our position | Comparison set | Why |
|---|---|---|
| 1 | None: no page ranks above ours | Say so. Compare with #2 and #3 only when the user asks how far ahead the page is |
| 2-3 | The pages above ours (one or two) | Those are the only positions left to pass |
| 4-10 (next step: top 3) | The three highest-ranking pages of the same kind as ours | The top 3 are the positions the page wants to reach |
| 11-20 (next step: page 1) | **The whole top 10** | Page 1 holds ten pages, often of different kinds, and any of them is a page to pass |
| Below 20, or not ranking | **The whole top 10**, as for 11-20 | Page 1 is the next step. The report leads with two questions: is ours the kind of page Google shows here, and does another own page already rank for the keyword (step 7)? Then the other areas |

With one or two pages above ours, "most" means all of them.

Skip pages that were not analysed (`crawl_error`). For the top 10 the work stays light: step 1
already holds kind of page, words, linking sites and server response of all ten; step 3 scores
ours and the pages actually compared (the rest only when ours scores lower); step 4 reads only the
pages of the same
kind as ours, at most five; step 6 checks the strength of the website for ours and those same
pages.

**"Most of the comparison pages"** below means two thirds of the pages compared, rounded up:
2 of 3, 3 of 4, 4 of 5, 7 of 10. The count is always of the pages actually checked in that area:
the SEO score and the domain score both cover only the competitor pages actually compared (3, or at
most 5 for the top 10), so "most" there means 2 of 3 or 4 of 5, not 3 of 5. The one exception is the content table in step 4, which sets
its own, lower bar for topics and formats (3 of 4 or 5 pages read).

### 3. On-page and technical

- **SEO score.** `seo_score(url)` for our page and each page actually compared (the pages read in
  step 4, at most five). It returns one number from 0 to 100, the same score the free SEO Check shows.
  **Top-10 case only:** when ours scores below most of the pages compared, score the rest of the top
  10 as well before you call the area behind. A page above with a lower score than ours rules the
  area out, and on page 1 that page can be of another kind. The verdict then counts all pages scored
  (7 of 10 for "most"). When ours is level with or ahead of most of the pages compared, the other
  pages add nothing and are not scored. The guide's rule of
  thumb: from about 80, a page is well optimised on-page.
  - Ours is under 80 **and** below most of the comparison pages: our page is behind on-page. Get
    the details from the Website Audit when the page is in a project (`get_page_analysis`, its
    todos), otherwise from one `seo_check(website=<our URL>)` (an expensive live call, ours only,
    never for the competitors).
  - Most of the comparison pages score at or below ours: no disadvantage. Say how many score lower
    ("2 of the 3 pages ahead of you have a lower score than you", "3 of the 5 pages compared
    on page 1 have a lower score than you").
  - Anything in between: the scores are close, and they are context, not a finding.
- **Server response.** `load_time` from step 1. When our page is not in the live top 10 (it ranks
  below), take `response_time` from `get_page_analysis` for a project page, or leave ours out. A
  finding only when ours is more than twice as slow as the slowest comparison page and over one
  second. This is the time until the server answers, not
  the full page speed: Seobility does not measure Core Web Vitals.
- **Can the page win at all?** For a project page, `get_page_analysis(project_id, url)` shows
  `statuscode`, `is_noindex`, `canonical_target` and the audit todos. A noindex, a canonical
  pointing elsewhere or a status other than 200 comes before everything else in the report.
  When the hand-off says `onpage=ok` for our page and the crawl is the same, reuse that
  instead of calling again; any other `onpage` value is the starting point, to confirm here.

### 4. Content: the pages side by side

In one run (free, about 1-3 kB per page):

```bash
python3 scripts/competitor_gap.py pages <our URL> <competitor 1> <competitor 2> <competitor 3> --keyword "<keyword>"
```

It prints for each page: title, description, H1, word count of the body text, the H2/H3 outline in
page order, tables, lists, expandable blocks, the structured data types (JSON-LD `@type`), the
publish and modified dates, and where the keyword appears. Pages that block scripts print
`FAILED`: for one of those, `seo_check(website=url)` reads it (an expensive live call, at most one
per keyword), or leave it out and say so.

**Ignore the page furniture in the outlines.** Author boxes, comment forms, "related posts",
newsletter and trial boxes, table-of-contents headings and footer contact blocks are printed too.
They are not content. Compare the headings that carry the topic.

What to compare, and what counts as a difference:

| Signal | A finding when |
|---|---|
| **Topics** (H2/H3) | A topic appears as its own section on most of the pages read (2 of 3; with four or five pages, at least 3) and not on ours |
| **Format** | A table, a checklist, numbered steps or an FAQ block on most of the pages read, missing on ours |
| **FAQ** | `FAQPage` structured data or an FAQ section on most of the pages read, and the demand (step 5) holds questions |
| **Depth** | Ours is under half the word count of the shortest page read. Longer is never a goal on its own |
| **Freshness** | The competitors were updated in the last 12 months and ours not for two years or more, or ours carries an old year in title or H1 |
| **Promise** | Title and H1 of the top 3 promise something ours does not (a number of tips, "for beginners", a year, a checklist) |

If ours is already the longest and most complete of the four, say so in plain words. That is a
finding: it moves the answer away from content.

### 5. Content: what people search around the keyword

```
keyword_autocomplete(search_term=<keyword>, search_engine=<market>)
```

It returns related searches with volume and intent: about a hundred for a big seed ("frontend"),
only a few or none for a low-volume one. It is the cheap call in this skill. Use it to see **what people search around the keyword**:

- **Cluster by intent, not by spelling.** "alt tag image seo", "alt-text image-seo" and "seo image
  alt text" are one topic. Add their volumes. Three or more variants make a topic real even at
  10 searches each.
- **Drop the off-topic rows.** Autocomplete matches words, not meaning ("seo" is also a surname, a
  restaurant, a Korean actor). If you cannot say how a row relates to the page, drop it.
- **Watch the commercial twin.** A "buy", "agency", "cost" or "tool" variant as big as the keyword
  itself is the split intent from step 2.
- **A single "<10" or 10 search is not a topic** unless the same topic is also a term gap. Show a
  volume of 0 or none as "<10", count it as 5 when adding up, and never read it as "nobody searches".
  An empty result is a data gap too: say that demand was not measured, and go on.

`keyword_similar` and `keyword_questions_and_similar_searches` are not part of the default run:
on the tested keywords the first drifted to unrelated terms and the second returned a handful of
generic questions without volume. Call the questions tool only when the demand from autocomplete is
thin and the page needs an FAQ.

### 6. Links to the page and strength of the domain

**Links to the page** for every comparison page are already in step 1: `results[].referring_domains`
gave the same count as `backlink_check` on all three pages checked. For the top 10 that is the
source; no extra call per page.

**Strength of the website:** `backlink_check(website=<full URL>)` for our page and the three
comparison pages, or, for the top 10, for ours and the same-kind pages read in step 4. Always the
full page URL (URL mode): it returns `meta_info.referring_domains_count` (how many other sites link
to that page) and `domain_score` (the strength of the whole site, 0-100). A bare domain switches to
domain mode and returns the whole site's link list instead. Not for every page of the top 10: on a
well-linked page the response carries its link list, 30k characters and more.

**Same-day reuse.** When a `backlink_check` for the exact same full URL already ran **today**,
in this conversation or in an earlier run whose report or test log records the two counts with
today's date, reuse `referring_domains_count` and `domain_score` instead of calling again. Link
data changes slowly, and each call is one of the expensive live checks. Three limits:

- Same URL only. `www` and non-`www`, `http` and `https`, or a trailing slash make it a different
  URL: call again.
- The counts only. When links to the page turn out to be a clear difference and the report needs
  sources (see below), the saved link list must still exist; if only the counts were written down,
  call again for that page.
- Say it in the line under the comparison table that names the pages read: "Link data for
  <pages> from an earlier check today."

The response arrives inline or saved, depending on its size (a Wikipedia article with 41 linking
sites came inline at about 30k, one with 107 was saved at 113k). Inline: read `meta_info`, and the
link list only when links to the page are a clear difference. Saved: do not read it; run:

```bash
python3 scripts/competitor_gap.py links <saved-file>
```

It prints the two counts and the strongest active follow links, one per linking site. On a page
with few links the response arrives inline and small: read `meta_info` directly.

How to read the numbers:

- **Links to the page** are a clear difference when **all three** (or at least 7 of the top 10)
  have at least ten times as many linking sites as ours, and at least 10 each. "0 against 1" or "4 against 12" is not a difference
  anyone can act on: say "for links to the page, there is no clear difference".
- **"1 / 1 / 1" with an empty title and no link list** is the answer for a page with no link data
  yet. Report it as "no link data", not as one linking site; a `referring_domains` of 1 in step 1
  can be the same answer. `competitor_gap.py links` marks it.
- **Strength of the domain** is a clear difference when **most of the pages checked** (2 of 3,
  or 4 of 5 same-kind pages in the top-10 case) have a domain score 10 or more points above ours
  **and of at least 30**. When the competitors are below 30, every site here is still small in
  Seobility's rating (0, 10 and 20 are all at the bottom of the scale): say so in one sentence
  ("All websites here have few links so far; their strength is not a clear difference") and give
  the area no verdict in the table.
  3 of 5 is not a clear difference: report it as mixed, with the counts on both sides. A page
  above us on a weaker domain means our page has no disadvantage in domain strength against that
  page. Say so.
- **Very strong sites** (an encyclopedia, official documentation of Google or a browser vendor, a
  large brand) have a domain score far above ours and, as the guide puts it, years of search
  history and visitors behind them. Say plainly that competing with such a site is hard in the short
  term, and name the next page above ours that is on a site of similar strength, as the more
  realistic comparison. Never promise that position.

When links to the page are a clear difference, the report names **where links could come from**: up to
three sites from the `links` output that link to a competitor page, are about the topic and are not
directories, link lists or the competitor itself. The guide's approach is to offer them the more
current or more complete page. Links to an encyclopedia article are rarely transferable: leave them
out. Never suggest buying links.

### 7. The user's own site

Only when the page is in a project:

- **Internal links:** `get_page_incoming_links(project_id, url, limit: 1)`, read
  `pagination.total`. Context, one line. Name it as a difference only when ours has under half the
  internal links of the project's own pages that already rank in the top 3 for similar keywords
  (two or more of them, same kind of page); never against the site's biggest hub.
- **Own pages competing for the keyword:** two own URLs in the live top 10 of step 1, or, for a
  monitored keyword, more than one URL in `get_keyword_ranked_pages(project_id, keyword_id)` (it returns each URL's
  best-ever position, not the current one: say "has ranked", and take current positions from the
  keyword's own SERP snapshot, `get_keyword_rankings`). Then
  several of the user's pages take turns for the same search. Name the page that should own the
  keyword (the right kind of page, the best recent position) and say what happens to the others:
  aim them at a different keyword, or link them to the owner with the keyword as link text, or
  merge them into it with a redirect. Never recommend deleting a page, and say that merging can cost
  the positions the other pages hold.
- **Language versions:** when the keyword ranks with our page in another language (the English
  page on Google.de), compare the market's language version, not the ranking page, and add one line
  on how the two compare in words and linking sites.

### 8. Sort each area: behind, no disadvantage, not visible

For each area, one of three results:

- **Behind:** the pages above are clearly ahead of ours by the rules above, on most of the
  comparison pages. A possible factor, and where the suggestions come from.
- **No disadvantage:** ours is level or ahead, or a page above is weaker than ours in this area.
- **Not visible:** the data cannot say (pages not read, no project, engagement, Core Web Vitals).

The short answer of the report names the areas where the page is behind, most evidence first, as
possible factors. When the page is behind in no measurable area, say exactly that: in everything
this comparison can measure, your page is level with the pages above; other signals that cannot be
measured here (visitor behaviour, page experience, search history) may play a role, and name where
the user can look. That is a correct answer. Never fill it with general SEO advice.

### 9. Derive the changes

Content changes combine their evidence per topic:

| The topic shows up in | Confidence, in the report |
|---|---|
| The side-by-side (2 of 3) **and** term data (3+ of 10) **or** demand (a cluster) | **Strong** |
| Two of the three sources | **Strong** |
| One source only, but a clear one (4+ of 10 pages, or a cluster of 3+ variants) | **Likely** |
| A heavily weighted term used by only the one or two highest-ranking pages | **A bet**: say that it is one |
| Nothing but general SEO knowledge | Not a finding. Drop it |

Suggestions from the other areas are **strong** when the page is behind in that area, and only
then appear:

- **On-page:** the audit todos or SEO Check findings of our page, each explained, most important
  first.
- **Links:** the named sites from step 6, each with what to offer them.
- **Own site:** the owner page and what happens to the competing pages; named pages to link from,
  with the link text.

Write each change as a task:

- **What to add or change**, as a proposed heading, link, or fix, in the page's language.
- **Where**: after which existing section, on which page, or in which setting.
- **What it must answer or achieve**: two to four bullet points. Not text to copy.
- **The evidence**, in plain words.

Order: the area where the page is furthest behind first; within content, strong before likely before bets.
Stop at **seven changes**. A longer list is a rewrite, and the user should be told that instead.

**What not to recommend:**

- More of a term the page already uses at the right level (`usage: perfect`). That is keyword
  stuffing.
- Brand names, cities, prices or authors of a competitor.
- Anything copied from a competitor page. The skill says which topics are expected, never how
  another site phrased them.
- Deleting sections or pages, or cutting a page because competitors are shorter.
- Buying links, or "build more backlinks" without named sources.
- Anything from an area where the page has no disadvantage.

### New article (no page yet)

Without `website`, step 1 returns the competitor side only, step 3 scores only the competitors,
and step 4 reads them without an "ours". For step 6, run `backlink_check` on our site's start page:
its `domain_score` set against the domain scores of the top 3 says whether the results are within
reach for this site at all. The output becomes an outline proposal: the sections most of the top
pages share, the format the results reward, and the demand clusters, each with its evidence. Say
that this is a starting outline, not a finished brief.

## Output

Write in the language the user writes in. Headings, bullets, no tool names, no field names, no SEO
shorthand without a plain explanation (SERP, TF\*IDF, referring domains, canonical, domain score
all get a few plain words on first use or are replaced: "how many other websites link to the
page", "how strong the whole website is in Seobility's rating").

> **<keyword>** · our page at position <n> · <market> · <our URL> · search results as of <date>

When the position is "not confirmed" (see "Check the ranking data before you use it"), the next
line says so neutrally: "I could not confirm this position; the comparison covers
the pages Google is showing right now."

**What I compared** (two sentences): our page against the pages above it (position 2-3), the
three highest pages of the same kind (position 4-10) or the whole first page of results (position
11 and below, or not ranking), in six areas: kind of page, technology and on-page, content, links
to the page, strength of the website, and the own site. At position 1, say that no page ranks
above ours and offer the comparison with #2 and #3.

**The short answer** (two or three sentences): in which areas the page is behind the pages above
(possible factors, never "the reason"), and where it has no disadvantage. What the page already
does well.

**How your page compares**, one table, ours and the three comparison pages, one row per area, and
a last column with the result in plain words:

> | | Yours | <competitor 1> | <competitor 2> | <competitor 3> | Result |
> |---|---|---|---|---|---|
> | Position | | | | | |
> | Kind of page | | | | | |
> | SEO score (0-100) | | | | | |
> | Words / main sections | | | | | |
> | Table, checklist, FAQ | | | | | |
> | Last updated | | | | | |
> | Websites linking to the page | | | | | |
> | Strength of the website (0-100) | | | | | |

For the top 10, the table summarises instead of listing ten columns:

> | | Yours | Page 1 (10 pages) | Ahead of you | Result |
> |---|---|---|---|---|
> | Kind of page | <kind> | top 3: <kind>; rest: <count per kind, e.g. "3 explainers, 2 articles, 1 agency"> | | |
> | SEO score (0-100) | <n> | <lowest-highest> (pages compared) | <how many score higher> of <n> | |
> | Words | <n> | <lowest-highest> | | |
> | Websites linking to the page | <n> | <lowest-highest> | <how many have 10x yours> of 10 | |
> | Strength of the website (0-100) | <n> | <lowest-highest> (same-kind pages) | <how many 10+ above> of <n> | |

and names the same-kind pages that were read side by side under it.

**Which word count goes where.** The three sources count differently (on one tested page: script
~970, term analysis 1,254, crawl 1,255), so never mix them in one comparison:

- **Both tables:** the term analysis of step 1, `results[].word_count` for the competitors and
  `analyzed_text.word_count` for ours. It is the only source that counts every page of the top 10
  the same way. Round to the nearest ten with a "~".
- **The depth rule of step 4:** the script's count, for ours and every page read, since the rule
  compares the pages read and the script is what read them.
- **The crawl's `word_count`:** not in the report. It counts our page only.

When the term analysis ran without our URL (new article), the "Yours" cell stays empty.

"Result" says *behind*, *no disadvantage* or *not measurable* in words the reader understands
("Your page has fewer sections than all three", "Position 2 has a lower score than you:
you have no disadvantage here"). The own-site area
(internal links, own competing pages) goes under the table in one line when the page is in a
project. When our page is below 20 or does not rank, and another own page ranks for the keyword,
that finding leads the short answer instead.

**What you could improve**, numbered, strongest evidence first:

> **1. <proposed heading, link or fix>** (strong)
> - **What I saw:** <the evidence in plain words: "3 of the pages above you have a section on this, and
>   people search for it in five variants, about 100 times a month together">
> - **Where:** after "<existing section>" / on <page>
> - **It should answer:** <2-4 bullets>

**Keep as it is:** one or two lines on what the page already does better and must not lose.

**Checked and left out:** a short list of what looked like a gap and is not, with the reason
("'hubspot' and 'berlin': names on one competitor's page", "links: the pages above you have no
more linking websites than yours"). This stops the reader from assuming the list is everything.

**What this cannot see:** one or two lines: how visitors behave on the pages, page experience
beyond the server's response time, and how long the sites have built trust with Google. For their
own page the user can check the first two in Google Analytics and PageSpeed Insights.

Offer the next step rather than doing it: the same comparison for the next keyword, or turning the
suggestions into a content brief. Never draft the new sections unless asked.

## Guardrails

- **Never name a cause.** Not for the lower position, not for a competitor's higher one, and not
  in the negative ("that is not the reason"). Every difference is a possible factor; every change
  is a suggestion. Read the finished report once for "because", "that's why", "the reason", "this is due to"
  and the same words in the report's language before you hand it over.
- **Never promise a position or traffic.** The comparison shows where the pages differ, not what
  Google rewards them for.
- **Never name an area as the difference without its rule.** "The competitors have more backlinks"
  needs the ten-times rule on all three; "stronger domains" needs 10 points on two of three, with
  those competitors at 30 or more. A
  plausible story is not evidence.
- **Never lead with term statistics.** They confirm the side-by-side; they are not the finding.
- **Never gate on search volume or cost.** Low or missing volume ("<10") is a data gap: never
  refuse, discourage or skip a keyword or a deep dive for it. You may say that a run is one of the
  expensive ones; the user decides.
- **Never state a credit cost**, per call or per run. Name a call as "one of the expensive live
  checks" when the user needs to know.
- **Never run the term analysis twice** for the same keyword and market in one run.
- **Never read more than six pages** side by side per keyword (ours plus three, or plus five
  same-kind pages from the top 10), and never a competitor page in full into the conversation: the
  script extracts what the comparison needs.
- **No disclaimer lines in the report** such as "none of these suggestions comes with a promised
  position". The no-cause rule shapes how every sentence is written; it is not a line to append.
- **Never compare against the tracked competitor list.** The competitors are whoever outranks the
  page for this keyword.
- **Never call a page not read "empty".** Name it as not read and classify it from its title and
  domain in the search results.
- **Never change anything.** This skill reads. It does not edit the page, the project or its
  settings.
