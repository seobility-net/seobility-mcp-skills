---
name: seobility-audit-triage
description: >
  Turn a finished Seobility crawl into this week's fix plan, including the site-architecture findings
  (click depth, weakly linked pages, links pointing at redirects). Reads the Site Audit, groups findings
  by the single change that resolves them, ranks the groups by Seobility's own severity against the cost
  of the fix, and says what to do first. Use when someone asks "I ran a crawl and got hundreds of
  issues, what do I fix this week", "what should I fix first", "which of these errors matter",
  "prioritise my site audit", "click depth and weakly linked pages, what to fix", "give me a fix plan
  from my audit", or the same in any other language; also for an audit turned into a work plan for a
  developer, an agency sprint or a client. Do NOT trigger for keyword opportunities
  (seobility-ranking-opportunities), whether the project is set up well enough to trust (seobility-setup-check),
  diagnosing a ranking drop, or writing tickets once the plan exists (seobility-findings-to-tickets).
---

# Audit triage - from hundreds of issues to this week's fix plan

A crawl of a mid-sized site returns thousands of "problems". Almost none of them are this week's
work. This skill finds the handful of changes worth making, says what each costs, and puts them in
an order someone can start on Monday. The output is three to six fix groups, not a list of issues.

## What this skill can and cannot see

- **One finished crawl.** Everything is as old as that crawl, and only covers what the crawler
  could reach. Pages behind a login, blocked in robots.txt or outside the start path never appear.
- **No effect.** A fix plan is not a forecast. Never say a fix will move a position, recover
  traffic or raise the score by N points.
- **Seobility fixes nothing.** Every line of the output is a change a human makes. Say it once if
  the user seems to expect otherwise.

## Before you spend a call

The helper scripts named below live in this skill's folder (`${CLAUDE_SKILL_DIR}` in Claude Code).
Run them as `python3 <that folder>/scripts/<script>.py`, wherever the current directory is.

1. **Resolve the project.** `list_projects`. Accounts often hold several projects with the same
   name covering different scopes of one site - one test account had three, with 522, 2,703 and
   10,013 pages crawled. Disambiguate by `url`, `pages_crawled` and `finished_date`, never by
   name. `problems: {current, delta}` per project shows which audit actually moved.
   `list_projects` returns every project of the account (about 40,000 characters for 46) and ignores
   `limit`. `compact: true` is smaller but drops `finished_date` and `pages_crawled`; `list_crawls`
   (it takes `limit`) returns them for the one project.

2. **Check the crawl date - and ask before planning on an old one.** A nine-month-old crawl
   produces a nine-month-old plan, and a full plan followed by "run a new crawl first" wastes the
   reader's time. `finished_date` is in `list_projects` and in `list_crawls` (needed for the check
   below), so this costs no extra call.
   When the crawl is **more than 30 days old**, or older than work the user mentions, stop here
   and ask one question before any other call:

   > The last crawl is from 10 December 2025 (9 months ago, 1,000 pages; it took about 50
   > minutes). Should I start a new crawl first, or build the plan on the old data?

   Take the duration from `crawl_duration`. On "new crawl", call `start_crawl` for that project -
   the only write call this skill makes, and only after that explicit yes in the conversation -
   then stop and say when to come back (`list_projects` shows `crawl_status`). On "old data",
   go on and say once near the top of the plan that it rests on a crawl from that date.
   `is_scheduled_crawl: false` means it only runs when someone starts it.
   Rankings are not frozen with the crawl: `get_rankings_landingpages` (step 7) is today's data.
   When the two come from different dates, say so, and that anything published since the crawl
   has no findings at all.

3. **Check the crawl is worth triaging.** In `get_site_audit_overview`:
   - `start_url_tests.is_crawling_total_failure: true` - the crawl never got in. Report it and stop.
   - `special_checks.was_crawling_budget_reached: true` - the crawl stopped at the plan's page
     limit, so the findings describe an arbitrary slice. Say so before ranking anything.
   - `special_checks.javascript_crawling_recommended: true` - content findings are unreliable;
     technical ones survive.

   If any of these fire, or the project looks misconfigured (a start URL that is not the site, a
   page count far below what the user expects), name **`seobility-setup-check`** as the next step
   rather than triaging data nobody should act on.

   **Check the crawl is complete and the baseline is comparable.** A crawl with `completion_reason: "stopped"` or `is_stopped: true` is partial, even though it reports `status: "done"` and 100%: do not build a plan on it; say so and hand off to seobility-setup-check. For deltas, compare against the last *regular, completed* crawl — skip crawls that were stopped, fetched 0 pages, or have `data_removed: true` — and say which crawl you compared against.

   `list_crawls(project_id, limit: 5)` carries all of this per crawl (`completion_reason`,
   `is_stopped`, `data_removed`, `pages_crawled`, `pages_indexable`). Compare `pages_indexable` as well
   as `pages_crawled`: at the page limit `pages_crawled` stays flat while the slice changes (10,000 to
   10,000 pages, indexable 9,784 to 3,529). The `delta` values in `list_projects` and the audit are
   computed against the previous crawl whatever it was (`problems.delta: 11255` against a stopped
   57-page crawl), so they are wrong when it fails this test: rank with `--no-baseline`.

   **Watch for a crawl that covers another project's section.** When the report rows carry URLs
   outside the start URL's section (`/de/glossary/…` on a project started at `/en/glossary/`),
   check `list_projects` for a second project whose `url` covers that section, and
   `get_crawler_settings`: a `robots_txt` override such as `Allow: /de/glossary` / `Allow: /en/glossary`
   means the overlap is configured, not accidental. Say it in one plain sentence near the top -
   which section is covered twice, and that its findings then show up in both projects - and
   plan the findings anyway. It is information, not a defect; do not hand it to another skill.

4. **Compare what was crawled with what may be indexed.** `pages_crawled` against
   `pages_indexable`, both from `list_crawls`. No report flags the gap, and it is often the
   biggest structural fact about the site: one blog had 3,459 URLs crawled and 200 indexable.
   Below roughly a quarter, spend one call on `get_report(analysis="pages-non-indexable")`. Each
   row carries its reason in `problems[].name` (`failure`, `noindex`, `redirect`), and `cluster`
   on the rows shows the pattern - on that blog, `/{post}/page/{n}/` copies of single articles,
   set to noindex. When the pattern is copies of real pages, it goes in the plan as a group of
   its own: what the extra URLs are, why they matter (search engines keep fetching thousands of
   copies of a 200-page blog), and a first step - find out where they come from - for whoever
   runs the site. That the reader cannot fix it themselves is never a reason to leave it out.
   A large gap also inflates other reports: on one site with 13% indexable, the top-ranked report
   (27,513 "medium response" pages) was mostly `/blog/category/…?page=N` crawler-trap URLs. With a
   gap this large, pull the rows of the top-ranked report and cluster them before accepting its class.
   A crawl failure (Method, step 2) is the exception: re-crawl first.

## Method

### 1. One discovery call

`get_site_audit_overview(project_id)` returns the whole catalogue in about 4,000 characters: four
scores with deltas, and every one of the ~60 reports with `status`, `count` and `delta`. Beyond the
counts, read:

- `scores` - the worst category is where the points are, not necessarily where the work is.
- `ai_search_bots.total_blocked_pages` - pages blocked from OAI-SearchBot, Claude-SearchBot,
  PerplexityBot and others. Anything above zero is a finding on its own: it is invisible in every
  other view and it is about AI search, not Google.

### 2. One ranking call, then the script

`get_site_audit_problems(project_id)` returns every report with `count` and `total_impact`. Save the
payload and run:

```bash
python3 scripts/triage.py rank <saved-file> --indexed <indexed_pages>
```

If a result arrived inline instead of as a saved file, write it to a file first (or pipe it to the script and pass `-` as the path). If the host tells you to read an oversized result in full, don't: run the script on the saved file instead.

`--indexed` switches on the coverage check; its value is `pages_indexable` from `list_crawls`, which
costs no call. `get_report_meta` also returns it as `overview.indexed_pages`, but read its warning in
`references/tool-notes.md` first: on an old project it returns every crawl ever
run. `categories: ["content"]` or `["structure"]` cuts the payload by two thirds.

**The ranking is `total_impact / effort`.** `total_impact` is Seobility's own severity, stable across
projects. `importance` and `priority` drift with the count and must never order anything. Effort is
the one thing the API cannot know, so it is written down in `references/impact-effort.md`. Read that
file before presenting a plan: it also carries the fix shape per report, which is the sentence the
user acts on. Never show the score as a number. It orders the rows, nothing more.

**What a problem is and how it is fixed comes from the Seobility Help Center.** Every report has an
article in German, English and Spanish; `references/help-center.md` maps each report to its three
URLs. For every report in the plan, read its article before writing the group, take the
explanation, the reason it matters and the recommended fix from it, and keep its concrete criteria
(thresholds; for titles and descriptions the pixel limit, not the character range). Where the article and `impact-effort.md` disagree on the problem or
the fix, the article wins; `impact-effort.md` still decides the order and the effort on this site.
Link the article in the user's language, English for any language other than DE and ES.

**A blocking report that appeared all at once may be the crawl, not the site.** The script marks a
blocking report `NEW` when `delta == count`. For `pages-broken`, pull the rows: `statuscode: null`
means the crawler got no answer at all, not a 404. On one blog, 51 such pages (every category and
author archive) sat at 0 for 309 crawls and at 51 in the last one, next to 18 slow server
responses - a server that timed out during that crawl. Make the one `get_report_meta` call
on `pages-broken`, and its history answers this in the same call. Then the first step of the plan is "run a new
crawl and check whether these pages come back", not a fix, and the report is only planned as a
blocker if the new crawl confirms it.
The `NEW` mark and the re-measure rule below assume the previous crawl passed the check in "Before you
spend a call", step 3. When it did not, add `--no-baseline`. On a project with fewer than 5 crawls only caveat the deltas.

**The same goes for response times.** When at least half of either response-time report is new
in this crawl (and it is at least 5 pages), the script moves **both** out of the ranking into `RE-MEASURE FIRST`: they measure
the same server in the same crawl. Judged one by one, the wiki below sent slow responses to
re-measure and kept medium ones (100 of 239 new) in the plan as a server job. On one wiki, 90 of
98 slow pages arrived in the last crawl, almost all in one language section, on a site averaging
0.37 s: a busy server during one crawl as often as a slow site. Pull the rows, say which pages
and how slow against the average, and make "run a new crawl" the step. The Help Center itself
says to warm the cache before a crawl for this reason.

### 3. Resolve the effort class yourself - never ask the user

Every class is a claim about the user's site, and whether their titles come from a template is not
in the crawl. **Do not put that question to the user.** Most people did not build their theme;
"is your H1 generated?" hands the work back to the person who came to have it taken off them.

Resolve it from the evidence, in this order:

1. **Reach - the decisive signal.** Above roughly half the indexable set, the issue is what the page
   type does, and it is fixed where the page type is defined. A glossary section flagged 287 of 335
   indexable pages for a short H1: nothing was wrong with 287 pages, one rule built all of them.
   **Exception:** reach does not promote values a person writes per instance - alt texts, anchors,
   any `editorial` report. The script says `SITE-WIDE, BUT WRITTEN` for those.
   **Exception to the exception:** an image that sits on nearly every page, usually the header logo.
   Run `get_page_media_files` on two affected pages: the image both carry is one template edit. Give
   it a descriptive alt (the brand name). An empty `alt` counts as missing for SEO. `aria-hidden="true"`
   may stay, so screen readers still skip it and nothing is lost for accessibility.
2. **Path clustering.** Affected URLs under one path pattern mean that section's template.
3. **The flagged value.** `get_report` returns the offending title or H1 per row. A shared constant
   frame means one template expression. **Distinct values are not evidence of hand-writing** - a
   template with a variable slot produces a different value on every page. Reach beats value
   variance whenever they disagree.
4. **Look at the pages.** If still ambiguous, compare two affected pages and one unaffected page of
   the same type. Same structure, same defect, different content means generated.
5. **Only then, assume - out loud.** Take the more expensive branch and put one line next to the
   affected group:

   > This is planned as 92 individual edits. If those intros come from one template, it is a single
   > change instead - tell me and I will re-order the plan.

The script's `RESOLVE THESE YOURSELF` block lists only the questions that are open and would move
the order - usually one or two. Re-rank once you know:

```bash
python3 scripts/triage.py rank <file> --assume heading-h1-problems=template
```

If the user volunteers how their site is built, take their answer over your reading.

### 4. Three counts that are not what they look like

The biggest numbers in an audit are usually one of these. The script flags them; you explain them.

- **Coverage rows.** A report whose count equals `indexed_pages`, with `total_impact: 0`, counts
  pages checked, not pages broken. Both signals are required: a real defect on every page
  (compression off) also equals `indexed_pages`, and it carries a weight.
  **`schema-validation` is not one.** It has no weight, but its rows are real, each `critical` or
  `tip`. Read `filters` with `get_report(analysis="schema-validation", limit=1)`. When every non-zero
  key is `schema_recommended_missing`, the rows are optional tips: put the report under "not worth
  changing" (`--assume schema-validation=none`). Anything else is planned. A `critical` row on a
  property whose value is a `{"@id": …}` reference (`breadcrumb`, `publisher`) may be a valid
  reference to a node in another JSON-LD block: read the page's JSON-LD. A reference that resolves is
  no defect; one that does not resolve on that page is a warning, never critical. Wrong types and
  missing required properties stay critical.
- **Block counts.** `pages-with-duplicate-text-content` can exceed the whole indexable set several
  times over: its rows are text blocks, not pages (`get_report_meta.columns` reads `text`, `pages`).
  The count cannot be planned against, but **the finding is real - read the rows, never drop
  it.** Each row gives the repeated text and the pages it sits on. Sort them into three groups:
  - **Teasers on the homepage, category or overview pages.** The Help Center counts long ones as
    a problem: they compete with the article itself. Shortening the excerpt is one setting.
  - **The same paragraphs across several articles** - a rewrite per article. On one blog this was
    a whole seven-article series sharing more than 20 paragraphs per language, on pages that rank:
    the most valuable content finding in the audit, hidden behind a count that looked meaningless.
  - **Author bios, credit lines, quotes in both language versions of one article** - low priority.
    Site-wide disclaimers and cookie banners are already left out by Seobility itself.

  The script lists these under `READ THE ROWS`.
- **Minicheck and hint rows.** `minicheck_avglinks: 51` is an average, not 51 problems. Only
  `type: "analysis"` rows are findings; the script filters.

Any other report whose count exceeds `indexed_pages` lands under `COUNT ABOVE THE INDEXABLE SET`.
Check its `columns`: `page` first means it also counts non-indexable URLs and stands; `text` or
`item` means it is a block count: read its rows the same way.

### 5. Split each report into the edits it contains

`title-problems: 113` on one project was 91 too long, 17 with a repeated word and 7 too short -
three edits, and only one worth a sprint. The split costs about 200 characters:

```
get_report(project_id, analysis="title-problems", problems=["title_missing"])
-> {"rows": [], "filters": {"title_short": 7, "title_long": 91, "title_wordrepeats": 17, ...}}
```

Ask for a sub-type with no hits and `filters` still returns the full histogram; `limit: 1` returns it
with one row, where no sub-type is known. Do this for every report in the plan with a count above 2.

- Sub-type counts are occurrences, not pages, so they can sum to more than `count`.
- `filters` is an empty **array** `[]` on reports with no sub-types. Test the shape.
- `canonical-link-target-problems` returns `filters: []` but carries its sub-type in each row's
  `problems[]`. Read the rows. Its four sub-types are four different jobs, from one plugin setting
  to one decision per foreign domain; `references/impact-effort.md` classes each.

The script marks sub-typed reports with `*`.

### 6. Cluster before you promote

A fix on 939 pages is either the largest job in the audit or a ten-minute template change, and
nothing in the counts says which. For every report you plan, pull its rows and run:

```bash
python3 scripts/triage.py cluster <saved-report> --label <analysis> --indexed <indexed_pages>
```

Pass the report's slug as `--label` and always pass `--indexed`. The verdict is one of
`SYSTEMATIC`, `SITE-WIDE, BUT WRITTEN`, `ONE STRING`, `SCOPED TEMPLATE`, `PER PAGE` or `UNCLEAR` -
and `UNCLEAR` means go and look at the pages. It also prints the query parameters of the URLs: a
`?page=N` family that dominates is a crawler trap, not a page type, and a reach over 100% means the
count is not on the indexable set. Neither gets a verdict; look at the URLs.

Clustering also finds what should not be in the plan. When most deep pages are author archives and
paginated listings, the right entry is "ignore this report on this site, here is why". Language
prefixes are folded to `/{lang}/`, so one template on a multilingual site stays one cluster.

**Read the anchors before planning `link-anchor-text-duplicates-for-different-pages`.** It carries
the highest weight in the audit (50), so a handful of findings lands near the top. The anchor text
is in each row, and it decides the fix. A generic label on listings ("show more", "read more") is
something the Help Center says to avoid, and it is a template fix: put the target's title into the
link text, once, for every listing. One content anchor pointing at different targets from within the same section is a decision
per link. A descriptive keyword whose target depends on the section ("recycling" to `/disposal/glass/` from one
section and to `/containers/glass/` from another, each section consistent) is by design: it goes
under "not worth changing", not "a decision per link". A generic label reused for different targets
("Read the details →" to six pages) is the defect. A fixed credit line ("original English version by …") is the only kind that can wait.
The rows may also be fewer than the count - 2 groups for 19 findings on one project - so say what
you could see.

**Links to redirects: cluster the targets, not the reach.** A row of
`internal-link-targets-on-redirects` is a redirecting URL, so 375 of them against 631 pages is two
different units. The script says `ONE RULE` when the targets share a path pattern. On one wiki,
375 targets were two patterns: the home link with a trailing slash in every article, and every
article image linking to an old image path. That is two changes where the links are built, not
375 repoints. `--assume internal-link-targets-on-redirects=template` then re-ranks it.

**Read the flagged words before planning `pages-missing-the-title-content-in-the-body`.** The
missing words come back in bold in each row's `formatted`, and the script counts them. When they
are words the title adds to every page ("Definition", "explained", "Best Practices"), the Help
Center says such pages usually need nothing: put the report under "later" with that reason. Topic
words missing from the text are the real edits. The same rows are the best look at the titles
themselves: the script flags `VISIBLE HTML ENTITY` when a title shows `&amp;` as code, which
no report catches and which is a quick fix of its own.

**Read the pairs before planning `pages-with-keyword-cannibalization`.** Each row lists the
competing pages. Two language versions of one article (`/en/…` and `/de/…`) do not compete - they
serve different markets. Two articles about related but distinct terms ("On-Page SEO" and
"Off-Page SEO") are not candidates for merging. Both go under "not worth changing" with that
reason; only pairs that really answer the same question are planned.

**Re-request the outside links before planning `external-link-target-problems`.** Most flagged
links on the audits checked were alive: 503, `down`, 202 (a firewall challenge) and even a 404 (for
the crawler's user agent only) loaded in a browser. Request every flagged URL with a browser user
agent. Only a live 404 or 410 or a DNS failure counts as dead; a 301 becomes a link update; the rest
is dropped, with that reason. Until then the report is `inspect` and not ranked. Plan the confirmed
dead and moved links as one group of their own and place it by its weight.

**Titles and descriptions are cut off in pixels.** `title-problems` and `meta-description-problems`
compare a pixel width with the limit each row carries in `properties` (`pixel_length_max`). Even 1 px
over risks a truncated snippet, so an overshoot is a real finding: keep it, with no tolerance band.
Quote the pixel limit, never the Help Center's character range (a 60-character title can exceed 580
px). The effort is low, usually one word. Descriptions generated by one template (the `cluster`
verdict) are one edit.

### 7. Weight the groups by what the pages are worth

`get_rankings_landingpages(project_id, timescale="weeks")` returns every ranking URL with
`visibility` and `keywords_count`. Use it one way: **an issue on pages that already rank outranks the
same issue on pages that do not.** Say how many of a group's pages rank and name two or three. It
also resolves the `~` rules: a deep page that earns rankings is worth work. Never turn it into a
traffic estimate or multiply it into the score.

### 8. Rows and paging

`get_report` returns 100 rows by default and takes `limit` and `offset` (`offset` a multiple of
`limit`). Rows come back worst-first, and `problems` subsets by sub-type. A small `limit` is the
cheapest way to cut a payload: `limit: 25` is enough to cluster most reports, `limit: 1` reads
`filters`. Say "the first 25 of 605, which is what the clustering is based on", and "most of the
affected pages we can see", never "all", unless you paged to the end.

### 9. The lists that are not the plan

- **`CHECK THESE FIRST`** - cost unknowable from the API (`pages-with-duplicate-paragraphs`, the
  same paragraph repeated **on one page**: a box the layout outputs twice is one template change,
  text repeated inside the article is an edit per page). Put it at the top as a
  ten-minute check on one sample page, linked straight to its text-blocks view. Also
  `external-link-target-problems`: its check is re-requesting the links (step 6).
- **`RE-MEASURE FIRST`** - both response-time reports, when at least half the count of either
  one is new in this crawl (step 2). Not ranked; the step is a new crawl.
- **`UNWEIGHTED`** - real defects without a Seobility severity, typically the two sitemap reports.
  Show them, do not rank them; small counts are often worth doing.
- **`READ THE ROWS`** - findings counted in text blocks. Read and sort them (step 4); the shared
  article paragraphs go in the plan, the rest is explained in one sentence.
- **`NO SENSIBLE FIX`** - classes resolved to `none` on this site, such as deep pages that are
  author archives. Say what Seobility flags and why it does not apply here.
- **URL reports** (`url-too-long`, `url-too-many-subdirectories`) are low-priority `page` rows,
  not dismissals: the Help Center wants them fixed. Existing URLs change only with a 301, best
  during a relaunch; new pages follow the rule from now on.
- **Rows marked `~`** depend on the site. Unresolved, they are planned at the `page` default so
  nothing is dismissed or under-costed. Resolve them from the clustering and say which branch you
  took; `--assume <report>=none` moves a resolved non-issue out of the plan.
- **`EXCLUDED`** - coverage rows only: they count pages checked, not pages with a problem. One
  line each, with the reason.

**Seobility's analysis is the baseline, not something to overrule.** Every report it weights stays
visible: in the plan, under "later" with the reason it waits, or with the reason changing it would
do more harm than good. A skill that silently drops a finding contradicts the product the user is
looking at. Long pages are the example: `pages-with-very-much-text-content` is not "length is not a
defect" - a very long article often answers several questions at once, and the check is whether
it should be split or made easier to scan.

## The output

### This week

Three to six fix groups, in plan order. Each group is a short section with a plain heading that
names the problem ("The same headings on almost every page"), then these parts, in this order:

| | |
|---|---|
| **The problem** | What is wrong, in words a site owner uses, with the count and one real example. Then why it matters to a reader, Google or AI search, in one sentence. Never open with the fix |
| **Why it is one job** | Only where it applies: why 174 findings are one template change, or why a big count is a small job |
| **Why it is here** | Whether the affected pages already rank, with two or three named |
| **What you do** | One sentence naming the change, and who does it (editor, whoever runs the theme, the SEO plugin setting) |
| **Effort** | One change / N quick edits / N edits that each need a decision / writing per page, plus the assumption where it is in question |
| **More on this** | The Help Center article for the report, in the user's language, with its title as link text |
| **In the app** | The report in the user's Seobility project, and for a named example page its detail view (URL format below) |

"The problem" and "What you do" follow the Help Center article (Method, step 2). Every "later" and
"not worth changing" line links its article too, so a reader who wants the full explanation is
one click away from it.

**Link every report you name to the app, and every page you name to its detail view.** Never
write "open Details in the app" without the link. The formats, verified 24.09.2026, use the same
slugs as the MCP:

- Report: `https://app.seobility.net/project/{project_id}/site-audit/reports/{analysis}`
- One page inside that report: the report URL + `?browser=site&url={page URL, URL-encoded}`
- Straight to the repeated paragraphs of one page:
  the same + `&tab=elements&element=text-blocks`

Example: `https://app.seobility.net/project/12345/site-audit/reports/pages-with-duplicate-paragraphs?browser=site&url=https%3A%2F%2Fexample.com%2Fglossary%2Fcrawler&tab=elements&element=text-blocks`.
The links open for the project's owner only; they are for the reader, not for a public page.

**Explain before you propose.** The reader has to know what is wrong before a change makes sense.
A plan that opens with "remove the duplicate H3 in the template" loses the reader in its first line.

**The "What you do" line must still survive on its own**, because it goes into a task list without
the surrounding paragraph. "Fix H1 problems" names a topic. "Give the glossary template's H1 the page
title instead of the one-word term, across 284 pages" is a task.

**Write for someone who is not an SEO.** No report slugs, no H1/H3, template, pagination, host,
status code or indexable without a plain clause, or better, the plain word instead ("the layout
every blog page is built from", "pages 2 to 17 of the blog overview", "may appear in Google").

Then, each as full plain sentences, not parentheses:

- **A quick check**, for every `CHECK THESE FIRST` report: what was found, the two possible causes
  and what each would mean, and the link that opens it: for `pages-with-duplicate-paragraphs`,
  the text-blocks view of one affected page, which shows the repeated paragraph directly.
- **Re-measure first**, for every `RE-MEASURE FIRST` report: what was measured, why it looks like
  one crawl rather than the site, and that a new crawl decides it.
- **Later**: each line says what the issue is, why it matters, and why it waits. "Waits" means it
  weighs less than this week's groups - never that someone else has to do it. Work for a
  developer, the theme maintainer or another team goes in the plan when it matters, with who does
  it named.
- **Not worth changing**: the reports where the fix would do more harm than good, each with
  Seobility's concern and the reason. Plus the coverage rows, each with what the number counts. A
  reader who saw thousands of problems in the app needs to know where every one of them went.

**Name no CMS, plugin or theme the data does not show.** "Your SEO plugin" unless the crawl shows
which one (a generator tag, a plugin's markup) or the user said so.

A tidy site produces a short plan, and that is correct. Do not pad to five rows.

### Say these two things once, near the top

- The crawl date and the number of pages in it. An old crawl was already settled with the user
  before the plan (Before you spend a call, step 2); say only that the plan rests on it. If you
  quote a delta, say which crawl it compares against; on a project with fewer than 5 crawls say the
  baseline is too young and quote none.
- How many findings, how many jobs they came down to, and how many were left out.

Write in the user's language. Write a file only if asked.

### The handoff

Offer the next step rather than doing it: the plan as developer tickets
(**`seobility-findings-to-tickets`**), one page analysed in full via `get_page_analysis`, or a
re-run against the next crawl to see which groups closed. Never open tickets or change a setting,
and start a crawl only on the user's yes to the crawl-age question.

### The handoff block

End the plan with one HTML comment, invisible when rendered, that `seobility-findings-to-tickets`
reads if it is pasted along with the plan. Add it only when the plan is shown as rendered Markdown or
handed to `seobility-findings-to-tickets`; in a plain-text channel (email, Slack, a ticket body) leave
it out, where it would show as raw text. One `job` line per job in the plan, in plan order; a job
that covers several reports gets one line per report under the same number, and a quick check counts
as a job with `class=inspect`. `class` is the effort class after you resolved it, `defect` the
sub-type key from `filters` (`-` if the report has none), `rows` the report's count, `crawl` its id
from `list_crawls`. Never mention the block in the prose.

```
<!-- seobility-handoff v1
project=<id> crawl=<id>
job=1 | report=<report slug> | defect=<defect key or -> | class=<effort class> | rows=<n>
job=2 | ...
-->
```

## Guardrails

- **Never claim a fix will improve rankings, traffic or the score.**
- **Never present a count you have not checked the meaning of.** Coverage rows and block counts
  look like page counts.
- **Never plan work on pages you cannot see.** State how many rows you read of the total, and the crawl's scope.
- **Never order by `importance`, `priority` or count.** `total_impact / count` is the severity.
- **Never plan against the count when it is not the cost driver.** Half a million parameter URLs
  are nine decisions; a thousand pages missing alt text are several thousand alt texts. The script
  names these cases. Report both numbers.
- **Never present an effort class as something the crawl established**, and never make the user
  answer a question about their CMS internals. Investigate, then state what you assumed.
- **Never drop a finding Seobility weights**, and never demote one because the reader cannot do it
  themselves. Order it, explain it, name who does it.
- **Read-only, with one exception.** `start_crawl`, and only after the user answered yes to the
  crawl-age question in this conversation. No settings, no other write calls.
- **Explain terms of art on first use** - canonical, click depth, indexable, template - in one
  short clause, or drop the word.
