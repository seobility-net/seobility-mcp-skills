---
name: seobility-findings-to-tickets
description: >
  Turn Seobility Website Audit findings into developer tickets that need no SEO tool to act on, and
  separate out the findings that need no ticket. Reads the audit via the Seobility MCP, splits each
  report into the separate defects it contains, decides who fixes each, and writes one ticket per
  fixable unit: affected URLs, acceptance criterion from the tool's own thresholds, a label. What the
  reader can fix themselves comes back as a checklist. Use when someone asks to "turn the audit into
  tickets", "something I can hand to my developer", "tickets for IT", "make GitHub issues from the
  Seobility findings", "Jira tickets from the crawl", "what goes to the developer and what can I do
  myself", or the same in any other language; also for a triaged fix plan that needs writing up as
  tickets. Do NOT trigger for deciding what to fix first (audit-triage), what changed since last week
  (weekly-checkin), whether the project is trustworthy (setup-check), or keyword and ranking work.
---

# Findings to dev tickets

The audit already knows what is wrong. It does not know who fixes it, in which file, or how
anyone would tell that it is done. That is the whole job here.

A ticket is one fixable unit: **one change, one owner, one acceptance criterion**. If closing it
needs two people or two templates, it is two tickets. If 284 pages are fixed by one change to one
template, it is one ticket, not 284.

**And most findings never become a ticket.** A ticket is overhead: someone writes it, schedules it,
closes it. That is worth paying when the work leaves the reader's hands: a deploy, a server
setting, a template, another team. It is not worth paying for two titles the reader can rewrite in
their CMS in the time it takes to read the ticket. Step 4 routes every group before anything is
written, and on a tidy site most groups never reach the ticket list.

## What a ticket is built from

| Part | Where it comes from | Never |
|---|---|---|
| Title | you write it, in the developer's words | the report slug, a defect key, SEO jargon |
| Affected URLs | the report rows, with the role resolved (step 6) | a URL whose role you did not check |
| What is wrong | the defect key plus its measured value from the payload | a general statement about SEO |
| Acceptance criterion | the threshold the tool itself used | a number you chose |
| Fix type | the effort class from `seobility-audit-triage` | hours, days, story points |
| Owner | `dev`, `editor`, `ops`, `external` | a name: you do not know their team |
| Severity | `total_impact / count` | `importance` or `priority` |

**The acceptance criterion is in the payload.** Rows carry `character_length_min: 20,
character_length_max: 120` or `pixel_length_min: 200, pixel_length_max: 580`. Taken from there, the
next crawl can re-check it. Invented, the developer closes a ticket against a number nobody can
verify.

**Severity is the audit's, not yours.** `total_impact / count` is Seobility's weight for one
finding of that kind (200 for a broken page, 10 for a short H1) and it is stable across projects.
`importance` and `priority` move with the count and disagree between projects for the same report.
Order by the quotient, never by the labels, and never build a ranking of your own: ordering the
backlog is audit triage's job. Both skills use the same rule; if it changes, it changes in both.

## Before you spend a call

The helper scripts named below live in this skill's folder (`${CLAUDE_SKILL_DIR}` in Claude Code).
Run them as `python3 <that folder>/scripts/<script>.py`, wherever the current directory is.

- **Resolve the project.** `list_projects`. Accounts often hold several projects with the same
  name for different scopes of one site: disambiguate by `url`, `pages_crawled` and
  `finished_date`, never by name. The full list returns every project on the account (about
  40,000 characters for 46; `limit` is ignored). `compact: true` is smaller but drops
  `finished_date` and `pages_crawled`: with it, take the crawl date from `list_crawls` (`limit: 1`).
- **The crawl date is the evidence date.** Every ticket says "as of the crawl of <date>". A
  developer sent to fix something fixed in March stops trusting the next batch. `finished_date` is
  already in `list_projects`, so this costs no extra call. When the crawl is **more than 30 days
  old**, stop and ask one question before any other call:

  > The last crawl is from 10 December 2025 (9 months ago, 1,000 pages; it took about 50
  > minutes). Should I start a new crawl first, or write the tickets on the old data?

  Take the duration from `crawl_duration`. On "new crawl", call `start_crawl` for that project -
  the only write call this skill makes, and only after that explicit yes in the conversation -
  then stop and say when to come back (`list_projects` shows `crawl_status`). On "old data", go
  on, say once above the set which date it rests on, and **check one example page per ticket
  live** before handing it over (step 8). Same rule as `seobility-audit-triage`.
- **Check the crawl is usable**, in `get_site_audit_overview`:
  - `special_checks.was_crawling_budget_reached: true`: the crawl stopped early, every count is a
    lower bound. Say it once, above the set.
  - `special_checks.javascript_crawling_recommended: true`: the crawler saw less than a browser.
    No content tickets ("no text", "H1 missing") without checking one page by hand.
  - `ai_search_bots.total_blocked_pages` near `indexed_pages`: the site is blocked from search.
    The robots rule is the only ticket that matters until it is lifted.
  - If the project itself looks wrong (far fewer pages crawled than the site has, no finished
    crawl), stop and name `seobility-setup-check`. Tickets from a broken setup are busywork.
  - `pages-broken` rows with `statuscode: null`, on a report that was empty in the previous crawl
    (`delta == count`): the crawler got no answer, which is usually a server timing out during
    that crawl. No tickets for them; a new crawl first. Same rule as `seobility-audit-triage`.
  - Response-time reports (`pages-with-slow-server-response-times`,
    `pages-with-medium-server-response-times`) are **judged as a pair**. When at least half the
    count of either one is new in this crawl (`delta >= count / 2`), both go to re-measure: a busy
    server during one crawl as often as a slow site, and the two reports measure the same server in
    the same crawl. Verified on a wiki: 90 of 98 slow pages new, 100 of 239 medium ones, site
    average 0.37 s. Judged one by one, slow went to re-measure and medium became a ticket for the
    same server. No ticket; a new crawl first, and a ticket only if it confirms the slow pages.
    Same rule as `seobility-audit-triage` (`RE-MEASURE FIRST`).
- **Ask the pre-flight questions, in one message:**
  - **Who does the work?** Just them with no developer, an in-house team, an agency handing
    work to a client's IT, or the reader is the developer and edits the code themselves. This is
    the question that decides the output (step 4). Always ask it. If it cannot be answered (no
    reply, a non-interactive run), assume **in-house team**: someone who asks for tickets usually
    has a developer. Say so in the first line of the output, as an assumption the reader can
    overturn, for example: "I assumed a developer in your team picks these up. If you do the work
    yourself, or it goes to a client's IT, tell me and I will re-route." Whatever the answer,
    wording changes (titles, descriptions, text) are never developer tickets (step 4).
  - **In which language do tickets go?** People often work in German and file tickets in English.
    Ask; do not infer it from the conversation. If unanswered, use the language of the request.
  - **Format:** Markdown unless they named a tracker or format (JSON, CSV or ready-to-run
    `gh issue create` commands on request). Do not ask.

## Method

### 1. Take the triaged plan, or build the shortlist yourself

If the user brings a fix plan from `seobility-audit-triage`, work from it and go to step 2. It
already carries the groups, the effort classes and the order; re-deriving them only produces a
second opinion on the same data. Its lists map like this:

| Triage list or class | What it becomes here |
|---|---|
| plan groups (`config`, `template`, `bulk`, `page`, `editorial`) | candidates, routed in step 4 |
| `CHECK THESE FIRST`, class `inspect` | route **check**: one question and one page to look at |
| `RE-MEASURE FIRST` | no ticket yet: a new crawl first, then a ticket only if it confirms the finding |
| `UNWEIGHTED` | usually an own edit; a ticket only if it leaves the reader's hands |
| `READ THE ROWS` (block counts) | read the rows first: repeated bios, credit lines and teasers are not work; the same paragraphs across several articles become own edits or editor tickets, one per article |
| `NO SENSIBLE FIX`, class `none` | never a ticket. Say what Seobility flags and why changing it now is not worth it |
| `EXCLUDED` | not work: coverage rows, minichecks |

**If the plan ends with a handoff block**, an HTML comment (invisible when rendered) that starts
`<!-- seobility-handoff v1`, read it instead of inferring from prose. Its first line gives
`project` and `crawl`; each `job=` line, in plan order, gives `report` (the slug), `defect` (the
defect key, `-` when the report is the unit), `class` and `rows`. Lines that share a job number
are one job. Take slugs, defect keys and classes from it. A job whose class is not one of step 3's seven words maps by its plan list, as in
the table above. The block carries no thresholds, current values, URLs or `total_impact`: pull them
with one `get_report` call per ticketed unit. **Without the block**, map from the plan's own
wording (its section names and the effort it states in prose), not from the labels in the table: a
customer-facing plan does not print them. Re-pull what a plan never carries (`special_checks`,
thresholds, current values, full URLs, `total_impact`): the overview plus one row fetch per
ticketed unit.

Ticketing `NO SENSIBLE FIX` discredits the whole set: 216 "page too deep" findings that are author
archives behaving as designed are the first ticket the developer opens and the reason they stop
reading.

Without a plan, two calls: `get_site_audit_overview` (which reports have findings) and
`get_site_audit_problems` (weight and `analysis` slug per report; the slug is the argument for
`get_report`). Order by `total_impact / count` and stop where the user has as many tickets as they
can schedule. **Ten tickets that get done beat forty the developer has to triage again.**
`get_site_audit_problems` returns about 60 rows with `count: 0` (roughly 8,000 tokens): the
overview's counts already say which reports have findings, so read them first and narrow the
problems call with `categories`.

Drop before you look: `type: "minicheck"` and `type: "hint"` rows, anything with `count: 0`,
reports with a large count and `total_impact: 0` (they count pages checked; `schema-validation` gets
the check under "What never becomes a ticket" first), and any report whose
count exceeds `indexed_pages` (its rows are text blocks, not pages). `references/tool-notes.md`
has the verified cases.

### 2. Split the report into the defects it contains

**A report is not a ticket.** `title-problems: 113` was 91 too long, 17 with a repeated word, 7 too
short: three fixes. A missing title is a template bug, a title 3 pixels too long is a copy edit.

`get_report` returns the full `filters` map on every call, including one filtered to a key with no
hits, so the split costs one cheap call:

```
get_report(project_id, analysis="heading-h1-problems", problems=["h1_missing"])
→ rows: [], filters: {h1_toshort: 284, h1_onlyoneword: 137, h1_genericword: 1, ...}
```

Use a key from the same family: an unknown key is an error. The tool notes list verified keys.
`limit: 1` keeps even an unfiltered probe to one row.

- **Never sum the counts.** One row can carry several defects, so the same page legitimately sits
  in two tickets. Say which tickets overlap, so nobody fixes the same line twice.
- **An empty `filters` (`[]`) does not mean one defect.** Some reports carry the sub-type in each
  row's `problems[]` instead. On an empty `filters`, pull the rows.

### 3. Fix type, owner, and with them the unit

**Fix type is the effort class, and it comes from audit triage**:
`seobility-audit-triage/references/impact-effort.md`. Seven classes: five you ticket, two you
route away.

| Class | Meaning | Here |
|---|---|---|
| `config` | one setting: server, robots.txt, sitemap generator, SEO plugin | fix type |
| `template` | one change in a layout, theme or component fixes every affected page | fix type |
| `bulk` | mechanical per instance, the new value is derivable | fix type |
| `page` | one short edit per page, someone decides what it says | fix type |
| `editorial` | writing or a judgement call per page | fix type |
| `inspect` | cost unknowable from the API | route **check** |
| `none` | a true finding with no sensible fix | never a ticket |

The reference is a sibling skill's file: `../seobility-audit-triage/references/impact-effort.md`,
relative to this skill's folder. If seobility-audit-triage is not installed, pick the class from
the table above by the fix itself, and say in one line that it is not the report's default.

Take the class of the report, or of its sub-type where the reference splits it. Use no other words.
The class is a default, not a verdict: when you find evidence triage did not have (the only link
to a 404 is a sitemap entry, so the fix is a sitemap setting), use the class of the fix you found
and say in one line why it differs from the report's default.

**Owner is who does it**: `dev`, `editor`, `ops`, `external`. Write it even when `dev` and `ops` are
one person: the ticket may travel to a client's IT, where they are not.

**Resolve `template` against `page` yourself. Never ask the user.** Most people did not build
their theme, and "is your H1 generated?" hands back the work they came to hand off. The evidence,
in triage's order:

1. **Reach.** `get_report_meta` gives `affected_pages.count` and `indexed_pages`. Above roughly
   half the indexable set, the defect is what the page type does: one ticket about the template.
   **Only where the defect can live in a template.** Values a person writes per instance (alt
   texts, anchor texts, every `editorial` report) stay page work at any reach, unless the element
   repeats on every page (a logo, an icon).
2. **Path clusters.** Affected URLs under one path pattern mean that section's template.
3. **The flagged values.** A shared constant frame means one template expression. Distinct values
   prove nothing: a template with a variable slot writes a different value on every page.
4. **Two pages.** Compare two affected pages and one unaffected page of the same type.
5. **Only then assume, and take the expensive branch.** Put one line into the ticket:
   *"Planned as 92 page edits. If these intros come from one template, it is one change."*

**Unresolved site-dependent rows default to `page`.** `title-duplicates`, `description-duplicates`
and `pages-with-high-page-depth` carry a rule, not a class. Resolved, they become `config`
(paginated variants of one listing) or `none` (author archives). Unresolved, they are `page`: that
neither dismisses a real problem nor prices a big job as one setting.

**Image-alt findings are grouped by image, not by page.** The rows do not say which image (step 5).
On one flagged page, `get_page_media_files(project_id, url)` lists the images with missing alt;
check a second page too. An image that sits on nearly every page (a header logo or icon:
`affected_pages` close to `indexed_pages` in `get_report_meta`) is **one template edit**, however
many pages report it: fix type `template`, effort low, "give the logo a descriptive alt, for
example the brand name". An empty `alt` counts as missing here: Seobility audits for SEO. Keeping
`aria-hidden="true"` on the image is fine, screen readers still skip it, so there is no
accessibility trade-off. Images that differ per page stay `page` work.

**`internal-link-targets-on-redirects` is resolved by the targets' pattern, not by reach.** A row's
`page` is the redirecting URL, so its count is targets, not affected pages. `tickets.py` prints the
targets by path pattern and says `ONE RULE` when one pattern dominates. Then the links are
generated, and each pattern is one ticket about where they are built (fix type `template` or
`config`): "Article images link to `/en/glossary/images/…`, which redirects to
`/media/glossary/…`; point the image links at the final path." Name a few linking pages
as examples, never a repoint list. Verified on a wiki: 375 targets were two patterns, the home
link with a trailing slash and the article images, so two tickets. `MIXED TARGETS` stays `bulk`:
one search-and-replace pair per target. Same rule as `seobility-audit-triage`.

**Merge defect keys that share fix type, owner and acceptance criterion.** `title_short` and
`title_long` break one rule and are one ticket; `title_wordrepeats` is a different rule. The same
merge applies across reports on one URL: a 404 that also carries a broken canonical is one ticket.

**Title and description limits are the SERP cutoff, in pixels.** A row over `pixel_length_max` is a
real finding even by 1 px: no tolerance band. Rate the effort low (usually one word), quote the
pixel limit from the row, not the Help Center's character guide (a 60-character title can still be
over in pixels), and group descriptions generated from one template as one edit (point 3 above).

Two tests before a unit becomes a ticket: **one PR** (one person, one change), and **the
developer's vocabulary**. "H1 too short" names a metric. "Wiki article template renders only the term
as H1; needs the full headline, 20-120 characters" names a change and a place. Write the second.

### 4. Route it: ticket, own edit, or check

| Route | When | What the user gets |
|---|---|---|
| **ticket** | the work leaves the reader's hands: a deploy, server or DNS, a template, another team | a ticket in their format |
| **own edit** | the reader can do it where they already work | a checklist: URL, current value, change, limit |
| **check** | the fix depends on something the crawl cannot see (`inspect`) | one question, one page to look at |

Decide in this order:

1. **Who does the work?** The pre-flight answer sets the baseline:
   - **Agency → client IT:** everything is a ticket, the small stuff too. Nothing they do not
     write down will happen. Editor work gets owner `editor` and goes into the set.
   - **In-house team:** tickets for dev and ops, own edits for what the reader does in the CMS.
   - **Solo, no developer:** almost everything is an own edit. A setting in the CMS or SEO plugin
     is theirs too. What needs code they cannot change becomes a **hand-over ticket**: the same
     ticket body, marked as the one to give a freelancer. Usually one or two.
   - **The reader is the developer:** the same split as in-house, but the tickets are their own
     work items: keep Change, Done when and the URL file, leave out hand-over wording. What they
     do in the CMS is an own edit.
2. **Does it need a deploy or access the reader lacks?** `config` and `template` usually do,
   `page` and `editorial` in a CMS almost never.
3. **Is it smaller than its own overhead?** Two titles are an own edit. 90 pages are a bulk job.
4. **Is it a judgement about wording?** Then it is an editor's, whatever its size; a developer
   ticket would bounce back.

**Keep an own-edit list workable in one sitting**, roughly 20 rows. Above that, give the rows that
break the limit most (or sit on the most important pages) and put the rest in a file: 78 long
titles are not a checklist.

**Say the routing out loud.** "You can do three of these yourself, two go to your developers" is the
most useful sentence in the set, and the one a list of tickets can never say. Never drop a finding
quietly because it did not deserve a ticket: move it, visibly.

### 5. Pull the rows, and know what you did not get

Only for the units you ticket, filtered to the defect:
`get_report(project_id, analysis="title-problems", problems=["title_long"])`.

- **Page through the rows.** `get_report` returns 100 rows by default; `limit` and `offset` reach
  the rest (`offset` a multiple of `limit`). Pull every page of a unit you ticket and stop on a
  short page (on grouped reports `total` is not a row count). Rows of grouped reports list at most
  4 pages each; the full set comes from `get_sublist(analysis: duplicate-text-paragraphs, item:
  <hash>)` (its `limit` is ignored). If you stop early, the list is a sample and the ticket says so: *"78 of 91 findings
  retrieved (crawl of 20.09.2026); the full list is in the report in Seobility."* Never put a
  partial list under a heading that implies it is complete.
- **Findings are not pages.** Three broken outbound links sat on two pages. A developer schedules by
  pages: write "3 broken links on 2 pages".
- **Some rows do not say which element.** `link-anchor-text-problems` and image-alt rows flag a
  page, not the link or image: `get_page_outgoing_links(project_id, url)` and
  `get_page_media_files(project_id, url)` on one flagged page name it.

If a result arrived inline instead of as a saved file, write it to a file first (or pipe it to the script and pass `-` as the path). If the host tells you to read an oversized result in full, don't: run the script on the saved file instead.

Large reports overflow the tool result into a file. Do not read it into context; run the script:

```bash
python3 scripts/tickets.py <saved-report.json> --analysis <slug> --limit 10
python3 scripts/tickets.py <saved-report.json> --analysis <slug> --defect title_long \
    --id SEO-03 --crawl 2026-09-20 --out-dir tickets/
```

Always pass `--analysis`: the script needs it to resolve the URL role. Pass every page of a
paged report as its own path, and `--anchor "<text>"` to pick one anchor group on an
anchor-duplicate report (each anchor text is its own unit there). It groups rows by defect
key, resolves the role, deduplicates, prints findings and URLs separately, prints the threshold
only where the rows break it, and with `--id` writes `tickets/SEO-03-urls.txt`.

### 6. Resolve which URL the ticket is about

**On several reports the row's URL is not the page to fix.** This is the error that makes a set
worthless, and it is invisible unless you look:

```json
{"page": "https://www.microsoft.com/en-us/microsoft-365/copilot",
 "items": [{"type": "page", "page": "https://www.example.com/wiki/ChatGPT"}],
 "problems": [{"name": "linkissue_down"}]}
```

The ticket is "the link to Microsoft on our ChatGPT page is dead", not "fix microsoft.com".

| Report | The URL the ticket names |
|---|---|
| On-page (title, description, H1, headings, text, images) | `rows[].page` |
| `external-link-target-problems` | `items[].page`, the own page carrying the link |
| `internal-link-targets-on-redirects`, `redirect-target-problems` | `pages[]`, the pages containing the link |
| `canonical-link-target-problems` | `rows[].page`, the page carrying the canonical |
| `title-duplicates`, `description-duplicates` | `pages[]`, the pages sharing the text |
| `link-anchor-text-duplicates-for-different-pages` | **not in the payload.** `pages[]` are the link targets |
| `pages-broken` | not in the payload: see below |

The last two have the same row shape as the duplicates reports (a text and a `pages[]` list, no
`page`) and the opposite meaning. **The shape does not tell you the role; the report does.** For
any report not in the table, look at one row before writing a ticket.

Where the payload names the target but not the page to edit, `get_page_incoming_links(project_id,
url=<target>)` closes the gap. For a 404, it lists every page linking to it with its anchor text;
for an anchor-text group, keep the linking pages whose anchor matches. Verified outcomes: a 404
linked only from the XML sitemap (a sitemap setting, not a broken navigation link), and a 404
linked only from a subdomain the project also crawls (owner `external` if another team runs it).
Spend the call on broken, redirecting and anchor-text targets, never on on-page defects. On an
anchor-text report it is one call per target (about 80 on a mid-sized site): resolve one example
for the ticket, and resolve the rest only when the user asks for it.

`problems[].value` carries the detail (the HTTP status, the new host). Put it in the ticket.

### 7. Write the ticket

```markdown
### [SEO] Wiki article template: H1 renders only the term
**Fix type:** template · **Owner:** dev · **Severity:** 10 per finding (Seobility's weight for one
finding of this kind, not a percentage or a forecast)
**Where:** the wiki article template, 284 of 335 indexed pages
**What is wrong:** the H1 is the bare term ("Backlinks", 9 characters). Seobility's H1 check
expects 20-120 characters: h1_toshort on 284 pages, h1_onlyoneword on 137 (mostly the same pages).
**Change:** render the full article headline in the H1 instead of the term alone.
**Done when:** every affected page has an H1 of 20-120 characters, and the next crawl reports 0
under Site Audit → heading-h1-problems → h1_toshort.
**Scope:** 284 findings on 284 pages, 284 URLs retrieved (crawl of 18.09.2026),
full list in tickets/SEO-01-urls.txt.
**Labels:** seo, template
**Source:** project 12345 · heading-h1-problems / h1_toshort · crawl 2026-09-18
```

- **Title:** the change and where it lives.
- **Fix type:** one class word. `bulk`, `page` and `editorial` carry the count: `page (4)`.
  **Never hours or story points**: you do not know their codebase, and a made-up estimate is the
  fastest way to lose the person who has to deliver it. An assumption from step 3 goes in as one
  line under the fix type.
- **Done when:** the tool's own threshold, plus report and defect key to re-check after the next
  crawl. That clause makes the ticket closable by someone who does not do SEO. If the defect
  carries no threshold (a repeated word), the criterion is "the next crawl reports 0 under
  <report> / <key>" and nothing more.
- **No promises.** Not "this will improve rankings". The audit measures a defect against a rule;
  whether fixing it moves a position is not in this data.
- **Scope:** retrieved against total whenever they differ, findings and pages separately.
- **Labels:** `seo` and the fix type, nothing else. The audit category (`technique_and_meta`,
  `structure`, `content`) is a Seobility slug a developer cannot use, and the report slug is
  already in `Source`. Labels must exist in the tracker; the user adds more if their team uses them.
- **Source:** project, report, defect key, crawl date. It makes the ticket auditable in six weeks.
- **Background:** the report's Seobility Help Center article, in the reader's language, from
  `../seobility-audit-triage/references/help-center.md` (the sibling skill's folder; without that
  skill, leave the line out rather than guess a link). The ticket's explanation and fix follow that
  article; the link lets whoever picks it up read the full reasoning without an SEO on hand.

### 8. Check live, show the set, then export

**Check one example page per ticket live** before the set goes out: every ticket on a crawl older
than 30 days, the top units (three at most) on a fresh one, where it is the step that exposes
sitewide template images and outside links that are alive. `seo_check(website=<url>, detail_level="full")`
fetches the page now and returns its title, headings and every link on it (without
`detail_level: "full"` the link list is missing). Verified on a wiki with a nine-month-old crawl: the H1 and the image-link tickets were
still true live, the home-link ticket was already fixed (all 112 links on the example page pointed
at the final URL), and one suspicion from the rows (a literal `&amp;` in titles) was confirmed.
One ticket fewer and one own edit more, for one call. A plain `curl` is no substitute: sites
behind Cloudflare answer it with a 403 page. The payload is large (~56,000 characters) and
may overflow into a file; read it with a short script, never into context. A ticket the live page
contradicts moves to a line "already fixed", with the page that showed it. It never goes quietly.

**Never open tickets.** Print the set, let the user strike what they do not want, then produce
the export. For GitHub, the deliverable is `gh issue create` commands **for them to run**.
`references/export-formats.md` has Markdown, JSON, CSV, `gh`, and what Jira, Linear and Asana take.
Full URL lists go into one file per ticket, referenced in `Scope`: nobody reads a ticket body with
284 URLs in it.

## What never becomes a ticket

Each of these was a real row in a real audit, and each would have produced a confident, wrong
ticket.

- **A flagged outside link you have not re-requested.** 403, 202, 503, `down` and even a 404 were
  alive in a browser (in a sample of 18 flagged URLs, 13 were). Re-request every flagged external URL
  with a browser user agent before it becomes work. Only a live 404 or 410, or a DNS failure, is
  dead; a 301 is a link update; a link still blocked is one line, "worth a manual click".
- **`http://` → `https://` redirects.** The site working as designed. If there is a ticket, it is
  about the internal links still pointing at `http://`, and those pages are in `pages[]`.
- **A measurement or a coverage count.** An average links-per-page figure, `schema-validation`
  at `indexed_pages` with `total_impact: 0`. Pull one `schema-validation` row with `limit: 1` and
  read `filters` first: it is coverage only when every non-zero key is
  `schema_recommended_missing`. Any other key is a real report with its own row severities
  (`critical`, `tip`): pull the rows. An unresolved `@id` reference is a warning, never critical.
- **Pagination by design.** "show more" linking to /blog/page/2/ … /page/7/ is one "load more"
  button per listing page, flagged as one anchor text for six targets. Not work.
- **A descriptive keyword whose target depends on the section.** "Recycling" links to
  `/disposal/recycling/` from one section and to `/containers/recycling/` from another: each page
  is consistent and the two targets are different intents, so it is by design. A generic label
  reused for different targets ("Read more →" on 8 pages, 6 targets) is the real defect: one
  template ticket.
- **`/cdn-cgi/l/email-protection` as a 404.** Cloudflare's email obfuscation rewrites addresses
  in the text into that link. Route **check**: keep or switch off the obfuscation, a decision
  and not a repair.
- **An index or hub page doing its job.** A wiki's A-Z main page came up in three reports at
  once: 335 internal links, too many headings, too few text blocks. That is what an index is.
  Route it as one line under "not worth changing" with the reason, and name the alternative
  (splitting it by letter) as a rebuild, not a fix. The same holds for an HTML sitemap: the Help
  Center's own exception is noindex, not fewer links.
- **On-page defects on a site blocked from search.** See the pre-flight check.
- **Anything you could not attribute to a page the user controls.** Say the finding exists and
  that the affected page could not be resolved. Do not guess.

## The one number you may add

If the user wants tickets ordered by business value rather than by the audit's weight,
`get_rankings_landingpages(project_id)` lists the pages that hold rankings: a template defect on
ranking pages outranks the same defect on pages nobody reaches. Only on request, once, and named
for what it is: a re-ordering by ranking pages, not a prediction. There is no Search Console
connection in this data; traffic figures have to come from the user's own export.

## Output

**1. What this comes to**, as a sentence: findings in the audit, tickets, own edits, checks, what
was left out. "940 findings: 1 ticket for your developers, 6 text changes for you,
the rest needs no work" tells them more than any table below it. Above it, one line each and
only when true: a crawl that stopped early, a site blocked from indexing, a stale crawl.

**2. The tickets:** the short list first, then the bodies, then the export. **The bodies go into
the answer itself**, not only into a file: the tickets are the deliverable, and a summary table
with "details in the file" leaves the reader without the thing they asked for. Files are for the
URL lists and for own-edit lists above ~20 rows.

| # | Ticket | Fix type | Owner | Pages | Severity |
|---|---|---|---|---|---|

**3. Your own edits:** a checklist with URL, current value, change, limit. No id, no owner, no
labels, no severity: the reader is the owner and is not scheduling this against anything.

**4. Checks**, only if there are any: one question each, with the one page to look at.

A set where everything landed in block 2 is usually a routing failure, not a broken site. Unless
the answer was "agency": then it is correct.

The conversation runs in the user's language, the tickets in the language they named.

## Guardrails

- **Never open, file or close anything.** Hands-off against the tracker: print commands, never
  run them. Read-only against Seobility, with one exception: `start_crawl`, and only after the
  user answered yes to the crawl-age question in this conversation.
- **Never invent an acceptance criterion.** The threshold is in the payload, or the criterion is
  "0 under <report> / <key>".
- **Never estimate in hours**, and use triage's class words and no others.
- **Never promise a ranking or traffic effect.**
- **Never present a partial list as complete.**
- **Never name a URL without resolving its role from the report**, not from the row shape.
- **Never order by `importance` or `priority`**, and never build a ranking of your own.
- **Never ask the user whether pages share a template.** Resolve it, or assume the expensive
  branch in one line.
- **Never write a ticket smaller than its overhead**, and never drop a finding silently.
- **Never route by size alone.** A one-line change that needs a deploy is a ticket; a 90-page
  rewrite the owner does themselves is their own list.
- **Calls scale with the reports that have findings, not with the findings.** Fixed: `list_projects`
  and the two audit calls. Then one row fetch per report that becomes a ticket or an own edit (own
  edits need their rows too: URL, current value, limit; more where a unit spans several pages of
  100 rows), one split call where `filters` has
  several keys, `get_report_meta` only where reach decides the class, `get_page_incoming_links`
  only for broken, redirecting and anchor-text targets, and one `seo_check` per live-checked ticket
  (step 8). A tidy site with five reports is six to twelve calls; the wiki in the tests, with 18
  reports, took about 20. Coverage rows and other reports dropped in step 1 need no fetch. On a project with thousands of findings, narrow
  `get_site_audit_problems` with `categories`.
