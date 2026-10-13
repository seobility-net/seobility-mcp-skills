---
name: seobility-setup-check
description: >
  Check whether a Seobility project is configured to show the whole picture, and what to adjust
  to get more out of it. Reads the account's real limits, the crawl's reach and recency, the
  monitored keyword set, the competitor set and the uptime monitor, then names the settings worth
  changing, one fix each. Use this skill when someone asks "is my account set up
  properly", "am I tracking the right things", "why does my project show so few pages", "is this
  data even worth acting on", when they are onboarding a
  new project or taking one over from someone else, or when another Seobility skill returned
  something that looked wrong or empty. Also when they ask how close they are to their keyword or
  crawl limits, or what domain verification would buy them. Do NOT trigger for working through the
  issues a crawl found (that is audit triage), for finding ranking opportunities (that is quick
  wins), or for the weekly delta report (that is the weekly check-in).
---

# Project check — are you getting the most out of this project?

Every other skill in this library assumes the project underneath it is configured. This one
checks that assumption and says which settings to adjust.

**Every detected gap should be based on a setting the user controls.** Almost
everything this skill finds is a choice made in the project: a page limit, a keyword list, a
competitor list, a monitored URL. Say what the
user gains by changing it: a report that covers the whole site, deltas that compare like with
like, a monitor that reports real outages.

The output is a verdict per area, the specific gaps named, and one fix per gap. Read-only
throughout: there is a write tool for almost everything this skill finds, and it calls none of
them.

## What "set up" means here

Five things have to hold before the data means anything. They fail independently, and a project
can look healthy in the app while three of them are broken:

| Area | The question | Fails silently as |
|---|---|---|
| Crawl reach | did the crawler see the whole site? | an audit that describes a fraction of the site as if it were all of it |
| Crawl recency | is the audit current, and is there a second crawl to compare against? | confident deltas against a crawl from 2023 |
| Keyword coverage | is enough of the site's demand monitored? | "nothing moved this week" from a set that covers two pages |
| Competitor set | are the tracked competitors the real ones? | a gap analysis against Wikipedia |
| Uptime | is anybody watching, and does "down" mean down? | a three-month outage that is a redirect, or a monitor switched off in February |

Each section below ends in a fix the user can carry out. None of them is carried out here.

## Before you spend a call

The helper scripts named below live in this skill's folder (`${CLAUDE_SKILL_DIR}` in Claude Code).
Run them as `python3 <that folder>/scripts/<script>.py`, wherever the current directory is.

**1. Resolve the project, and do not guess.** `list_projects` is one call and already carries
four of this skill's findings for every project at once: `is_verified`, `is_scheduled_crawl`,
`health_status`, `total_crawls`, plus `pages_crawled`, `finished_date` and `created_date`. It
returns every project in the account (about 35,000 to 40,000 characters for 46 projects);
`compact: true` drops all of those fields and `limit` is ignored. Search the result for the
name or URL instead of reading it top to bottom.

Accounts routinely hold several projects with the **identical name and the identical URL** for
different scopes of one site. In the test account three projects shared one name and two of
those shared the same URL — distinguishable only by page count and last crawl date.

When more than one candidate matches, **show the candidates with id, URL, name suffix, page
count, last crawl date, `is_scheduled_crawl` and `health_status`, and ask**. Twins can differ
by two pages and one day (same URL, page counts two apart). A wrong project id does not error. Every call succeeds and describes a
different site than the one the user is looking at.

**2. Read the account's real limits from `user_info`, never from `get_limitations`.**

`get_limitations` sounds like the user's quotas and is not: it returns the matrix of every plan
tier, keyed by an opaque plan id. In the test account the row for its own plan said 300
keywords, while `user_info` reported more than 30 times that. Reading it as the user's limit
would have been wrong by that factor.

`user_info` carries the effective numbers directly — `keywords_count` / `keywords_max`,
`projects_count` / `projects_max`, `max_pages`, `max_competitors` — already including add-ons.
Use those.

Call `get_limitations` only when a **plan-gated feature** is actually in question
(`scheduled_crawls`, `javascript_crawling`, `localisation_city`, `website_health_email_alert`),
and resolve the plan id from `user_info.level` first.

**3. Check the budget only when it is in question.** `get_credits` gives the balance, the
monthly allowance and the reset date. Call it once at the start of an account-wide sweep, or when
the user asks about their budget. A single-project run skips it.

## Method

### 1. Crawl reach — the finding nothing else surfaces

**Start with `get_site_audit_overview` and read `special_checks.was_crawling_budget_reached`.**
It answers "did the crawl hit its budget" directly. Then `get_crawling_limits`: for
`max_pages`, `current` above `limit` closes the case too. A verified project returned
`max_pages: {current: 10013, limit: 10000}`.

**That rule holds for `max_pages` only.** `max_external_links.current` counts discovered
external targets and is uncapped, so it can exceed its limit without anything being wrong;
`limit: 0` means external checks are switched off (one project showed thousands against 0).
`max_file_sources` can also overshoot (5,036 against 5,000) with no page cut. Report neither
as a blown budget.

Then take the newest crawls from `list_crawls` (`limit: 10` is enough) and the project's own
ceiling, and run:

```bash
python3 scripts/setup_check.py crawls <saved-file> --page-limit <max_pages.limit> --budget-reached <true|false>
```

If a result arrived inline instead of as a saved file, write it to a file first (or pipe it to the script and pass `-` as the path). If the host tells you to read an oversized result in full, don't: run the script on the saved file instead.

**A truncated crawl reports itself as a normal one.** The verified case: `pages_crawled: 10013`,
`pages_found: 16480`, limit 10,000 — and `completion_reason: "regular"` with `is_stopped: false`.
Nothing in the row admits that the rest of the site was never fetched. The tell is
`was_crawling_budget_reached: true`. `pages_crawled` at the limit with `pages_found` past it is
only a hint: `pages_found` is uncapped and shown nowhere in the account, so never quote it.

This is the most consequential finding in the skill, because it is inherited. Every issue count,
every score and every "we fixed 43 things" on that project describes a fraction of the site, and
audit triage will treat it as the whole.

The fix is to raise the page limit or narrow the crawl scope on purpose — **their choice**, and
they need to know the trade-off: more pages costs crawl budget, a narrower scope makes the score
comparable again.

**Check the crawl is complete and the baseline is comparable.** A crawl with `completion_reason: "stopped"` or `is_stopped: true` is partial, even though it reports `status: "done"` and 100%: say so and name it as the gap; other skills must not build a plan on it. For deltas, compare against the last *regular, completed* crawl — skip crawls that were stopped, fetched 0 pages, or have `data_removed: true` — and say which crawl you compared against. The script picks that baseline.

**A small crawl is not automatically a problem.** Check `get_crawler_settings` before calling one
a gap. The verified 522-page project crawls a site with thousands of pages because its
`robots_txt` override is `Disallow: / / Allow: /de/wiki` — deliberately scoped to one directory.
Reporting that as broken is how this skill loses the user's trust in its first paragraph.

**Two projects can crawl the same section.** The same override can also widen a crawl. Verified
24.09.2026: an English glossary project carries `Disallow: / / Allow: /de/glossary / Allow: /en/glossary`, so
it also crawls the German glossary, which has its own project. Compare the allowed paths and start URLs
of the account's projects (`list_projects` plus `get_crawler_settings` per project in question).
Report an overlap as information, not a defect: which section is covered twice, that its findings
and its crawl budget count in both projects, and that narrowing one override is the fix if the
overlap is not wanted. Whether it is wanted is the user's call.

**A changed crawl scope makes the score delta meaningless.** Same project, three crawls: 6,897
pages at score 79, then 4,892 at 58, then 10,013 at 29. The site did not lose 50 points. The
crawler reached twice as many pages, most of them worse than the ones it reached before. The
script compares `pages_crawled`, `pages_indexable` and `pages_found` against the last regular
crawl and warns above 25% on any of them: a crawl at its limit keeps `pages_crawled` flat while
the rest moves (the same page count twice, indexable pages down by two thirds, score 95 to 85).
The page count also moves when the site itself grew (a young site by 40%, confirmed in git), so check
`get_crawler_settings` before calling it a scope change. Either way, say the score is not
comparable; do not report the drop.

### 2. Crawl recency

Two numbers from the same call: when the newest crawl finished, and whether there is a second one.

- **No second crawl means every delta on this project is meaningless** — and the audit rows will
  not say so. They return `delta: 0` on every row while only `overview.problems_found.delta` is
  `null`. The fix is a second crawl.
- **`is_scheduled_crawl: false`** means the audit never refreshes itself. In the verified account
  three of seven projects had their newest crawl 5 to 10 months old. `total_crawls` is not a
  freshness signal (hundreds of crawls, one full crawl in a year): use the age of the newest crawl,
  which the script prints; over 30 days is stale.
- **`scheduled_crawls_waiting_period`** from `get_project_settings` is the cadence in days, but
  only while `scheduled_crawls` is true (the value stays populated when it is false). It is
  what tells a weekly skill whether "since the last crawl" means seven days or three.

One more finding lives in that call and nowhere else: `scheduled_crawls: true` with
`email_notifications: false` and recipients configured — crawls run every week and nobody is
told.

### 3. Keyword coverage — three numbers, and two of them are not what they look like

```bash
python3 scripts/setup_check.py keywords <saved-file> --room <available_for_venture> --created <created_date>
```

`list_keywords` overflows on any real project (168,000 characters at 335 keywords), so it goes to
a file. Do not read that file. It is also the keyword count: the script counts its rows, so
`get_keyword_count` adds nothing and is not called.

**The keyword count is rows, not keywords.** A project with 4 rows monitors *two* keywords
across *two* markets: each market is its own row with its own id and its own quota charge. Report
the distinct count and the market count, not the row count — "4 keywords" overstates the topical
coverage and hides that the project is multi-market. The script prints both and only comments
when they differ.

**`get_rankings_keyword_limit` never reports the project's usage.** It returns `total` (the
account allowance), `unused` (account-wide free capacity, identical for every project) and
`available_for_venture` (room left in *this* project). Rows used plus `available_for_venture` is
the project's own ceiling, independent of the account allowance — the real answer for an agency
asking why it cannot put everything in one project. In the test account it came to 2,000 on every
project, including an empty one. That is one plan, so **compute the ceiling, do not quote 2,000**:
the script does it when you pass `--room`.

Then read what the set actually covers:

- **Keywords ranking nowhere.** `rank: false` on a row with `ranking_fetched: true` means not in
  the top 100, the depth Ranking Monitoring tracks. Rows with `ranking_fetched: false` were never
  measured and are not in this count. 89 of 335 (26.6%) in the test project sat there, producing
  no visibility and no movement. They are not wasted — that is what monitoring a target looks
  like — but on an established project, if the share is most of the set, it is tracking
  ambitions rather than a business. Under about 60 days from `created_date` (76% to 84% ranking
  nowhere at 16 days), a high share is normal: treat it as context, not a gap.
- **Keywords on positions 21 to 100** rank, but beyond page two they produce almost no visibility.
  The script counts them separately. Do not merge them with the ones ranking nowhere.
- **Keywords per ranking URL.** 246 ranking keywords across 242 URLs is 1.02: broad and thin.
  Fine for site-wide coverage, useless for judging a single page, and worth saying when the user
  wants page-level work.
- **Keywords with no volume** have no measured volume in the provider data. 0 is a floor value,
  not proof nobody searches for the term; deliberate city long-tail looks like this (two thirds
  of one project's set). Context, not a gap.
- **Tag coverage.** 9.3% tagged means the set cannot be filtered or reported by segment.

An under-used project — a few dozen keywords monitored on an account that could hold hundreds —
shows up here as a small distinct count next to a large `available_for_venture` and a large
account `unused`. Say all three: what is monitored, what this project could still hold, what the
account has left.

### 4. Untracked demand — optional, and never passed through raw

Only when the coverage section found a gap worth filling. `get_rankings_keyword_suggestions`
returns **up to 500 rows (observed 0 to 500) with no paging and no filter** — 116,000 characters on a
project with four monitored keywords. This is the call behind the reported 110–117k-character context
blowouts, and it reproduces on the smallest project in the account.

```bash
python3 scripts/setup_check.py suggestions <saved-file> --top 10 --min-rating 40
```

`reason: "alreadyranking"` is the signal: the domain already surfaces for this term and it is not
monitored. **It means the domain appeared somewhere in that SERP, at any depth.** It does not
mean the keyword is relevant or winnable.

The verified run proves why this needs a human. Sorted by `rating`, the top five for an SEO tool
were `seo check` (100), `backlinks checken` (91), then `amazon seller central` (79),
`amazon sell center` (75), `seller amazon central` (75). Sorted by volume, four of the top five
were `google search console` and `keyword research` variants at 368,000 searches with ratings of
2 to 7.

So: shortlist a handful, show the rating and the volume, say plainly that the list needs their
judgement, and stop. Adding keywords is `add_keywords` and this skill does not call it. Hand the
shortlist to keyword research if they want it developed.

Note if the suggestions came back for a different search engine than the project monitors — all
500 did in the verified run. That is a market question, not a keyword question.

### 5. Competitor set

`list_competitors` returns an **object keyed by competitor id, plus a literal `self` key** for the
project's own domain. Counting its length gives 16 for 15 competitors, and **1 for a project with
none**. Exclude `self` and trust `pagination.total`.

`self` is worth reading: own visibility, own ranking keywords and own referring domains, no extra
call.

Two findings live here:

- **Dead slots.** Three of the verified project's 15 competitors carried `visibility: 0` and
  `ranking_keywords: 0`, added in 2024 and never seen in a tracked SERP since. Against
  `max_competition: 20` that is three slots producing nothing. The fix is to drop them.
- **Missing competitors**, from `get_competitor_suggestions`. Call it when the project has no
  competitors (that is itself the finding) or fewer than three, or when the user asks who is
  missing; otherwise skip it. This list must never be passed through raw. It returns "domains that rank for your keywords", which for the verified project
  meant youtube.com (614), de.wikipedia.org (445), instagram.com, facebook.com, amazon.de and
  duden.de. Correct answers to "who else ranks here", wrong answers to "who is my competitor".

  Filter to domains that plausibly sell what the user sells, propose at most a handful, and say
  what you filtered out and why. Drop platforms and reference sites first: youtube.com, any
  wikipedia, instagram.com, facebook.com, linkedin.com, reddit.com, pinterest.com, amazon and
  other marketplaces, dictionaries such as duden.de, news and government sites. If you cannot tell what the user sells, ask rather than guess.

`visibility_change: 9999` is a sentinel value, not a percentage. Do not print it.

### 6. Uptime, and what verification buys

**Check `list_projects.health_status` before reading any health payload.** A project with
monitoring switched off still answers `get_health_status` — with the last reading it ever took.
The verified case returned `status: "down"` dated February against
`health_status: "inactive"`: the monitor was switched off in February, and read alone the payload
says the site has been down for seven months.

A `monitoring: {active: false}` block in the payload, or `uptime_percentage: null`, is the
second tell.

When monitoring *is* active, `info` decides what "down" means. `"redirect"` is a monitor pointed
at a URL that redirects — a setup problem, and the fix is the monitored URL, not the server. A
permanently redirecting monitor returns `uptime_percentage: 0`, not null. The monitored URL
cannot be read through the MCP: read the project URL's status with the host's web fetch, or run `redirect_check` (it needs
`target_state`, checks www/https consistency, and is unverified for path redirects). If the start
URL redirects, the monitor and the crawl start URL both point at a redirect.
`"available"` is genuinely up. Name any other value rather than paraphrasing it. `interval` in `get_health_status` is the
chart bucket, not the check interval; that one is in `get_health_job` or `get_health_config`.

**"Not monitored", "no downtime" and "misconfigured" are three different sentences.** Write the
one that is true.

Verification is worth one line here because it has a concrete consequence: a shorter uptime
check interval. On the test account's plan it went from **15 minutes to 1 minute**. That is the
answer to "why should I verify", but the numbers are per plan: when the user is unverified and
asks, read `website_health_smallest_interval` and `website_health_smallest_interval_verified`
from `get_limitations` for their plan id (`user_info.level`) and quote those. `is_verified` is per
project — the same domain can have one verified project and one unverified.

**Do not print the verification token.** `get_verification_status` returns the DNS record, meta
tag and file contents whether or not the project is verified, and they are credentials. Name the
method and offer to fetch the value when the user is actually about to verify.

## Output

The reader asked one question — *does my project show me the whole picture, and what do I adjust
first* — and the report answers it in that order.

**Open with the verdict in one sentence.** Everything in place; one setting worth adjusting; or
adjust X before relying on the reports. Not a table, not a checklist.

**Then the settings that change what the reports show**, most important first, each with its fix. A gap
that makes existing data wrong (a truncated crawl, a monitor reporting a phantom outage) outranks
a gap that only limits future data (untagged keywords, three dead competitor slots).

**Then the areas that are fine, in one line total.** Not one line each — "crawl, uptime and
competitor set are fine" is the whole sentence. A setup check that lists five green ticks reads
like a report and gets skimmed; one that names two problems gets acted on.

**A well-configured project is the most common outcome and must read as one.** This skill runs
before the work, so the useful answer is usually "yes, go ahead". Manufacturing findings to
justify the run is the failure that kills it — the user learns the check always finds something
and stops believing the times it matters.

### Every number has to earn its place

A number goes in only if the reader would **do something different** depending on its value.

- **In:** 10,013 pages crawled at a 10,000 limit. 2 keywords across 2 markets. 3 of 15 competitor slots
  dead. Last crawl 24.04.2026.
- **Out:** exact quota figures nobody is near. Percentages of things that are fine. The account
  credit balance when it is not close to running out. Second-decimal precision anywhere.

### Never explain the tooling

Payload shapes, page limits, which field is a boolean, what the script could not compute, how
many rows came back — all of it governs **what you are allowed to write**, and then it is done.
It is not content.

"`get_keyword_count` returns rows rather than distinct keywords" is a note for you. "You track
2 keywords in 2 markets" is the sentence for them.

### Fixes, not topics

Each gap ends in something the user can do, naming the setting:

- Not: "You should look at your crawl settings."
- But: "The crawl captured 10,013 pages and ran into the page limit of 10,000. Increase the limit to 20,000 in your crawl settings —
or limit the crawl to a certain area so the SEO score becomes comparable again."

Where a gap has a skill behind it, offer it: keyword gaps → keyword research, a fresh audit →
audit triage, the weekly rhythm → the weekly check-in.

### Mechanics

Write in the language the user is writing to you in. Report the project by **id and URL** the
first time you name it, so a user with three projects called the same thing knows which one this
is about.

The report is a message, not a file. If the user wants it archived, write one dated Markdown file
and say where it went.

## Guardrails

- **Never change anything.** There is a write tool for nearly every finding here —
  `update_crawler_settings`, `add_keywords`, `add_competitor`, `start_crawl`,
  `update_project_settings`. This skill calls none of them. It names the setting and the value;
  the user decides.
- **Never guess the project.** Identical names and identical URLs are normal. Show the candidates
  with id, URL, page count and last crawl date, and ask. A wrong id does not error.
- **Never read the user's limits from `get_limitations`.** It is the plan matrix, not their
  account. `user_info` is the source.
- **Never print the verification token.** It is a credential, and it is returned whether or not
  the project is verified.
- **Never report a scoped crawl as a broken one.** Check `get_crawler_settings` — a robots
  override or a subdirectory crawl explains most "too few pages" cases, and they are deliberate.
- **Never compare scores across a changed crawl scope.** Different page sets: not like-for-like,
  whatever caused the change.
- **Never pass `get_competitor_suggestions` through raw.** Wikipedia and YouTube rank for
  everything. Filter, propose a handful, say what you cut.
- **Never present a keyword suggestion as a recommendation.** `alreadyranking` means the domain
  surfaced somewhere in that SERP. `rating` put `amazon seller central` third for an SEO tool.
- **Never report "fine" for something that is not monitored.** An inactive uptime monitor still
  returns a payload, and it is stale, not current.
- **Never invent a finding to justify the run.** Most projects are set up well enough. Say so and
  get out of the way.
- **Never claim a cause.** A dropped score next to a stale crawl is two facts. Which one explains
  the other is not in this data.
- **Roughly 10 to 11 calls per project.** `user_info`, `list_projects`, `list_crawls`,
  `get_site_audit_overview`, `get_crawling_limits`, `get_crawler_settings`, `get_project_settings`,
  `get_rankings_keyword_limit`, `list_keywords`, `list_competitors`, plus `get_health_status` when
  the monitor is active. `get_credits` only for an account-wide sweep or a budget question,
  `get_limitations` only for a plan-gated feature. The two suggestion calls are extras, added only
  when a gap was found. Everything else needs a reason.
