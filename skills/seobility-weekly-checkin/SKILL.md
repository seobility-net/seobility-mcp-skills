---
name: seobility-weekly-checkin
description: >-
  Report what changed on a site since last week and turn it into three jobs for this week.
  Collects the deltas a Seobility project already stores (ranking movement, new and lost
  backlinks, new and resolved crawl issues, uptime events), filters out the noise, and names
  the few changes worth acting on. Use when someone asks "what changed this week", "what
  happened since last week", "give me the deltas", "what should I work on this week" (the
  default owner of this open question), "my weekly SEO check", or the same in any other language;
  also for a short standing update for a client or team channel, or what moved after a release.
  Do NOT trigger for finding ranking opportunities (seobility-ranking-opportunities), working through the full issue
  backlog (seobility-audit-triage), checking whether the project is set up well enough to
  trust (seobility-setup-check), or diagnosing one ranking drop in depth.
---

# Weekly check-in — what changed, and the three jobs that follow

Seobility already stores the deltas. This skill collects them, drops the noise, and ends with
three jobs — each naming the URL or keyword it came from.

The whole report fits on one screen. A quiet week is allowed to read as a quiet week.

## What this reads, and what it cannot see

Four data sets, each with its own collection rhythm and its own window:

| Section | Source | Window it actually covers |
|---|---|---|
| Rankings | Ranking Monitoring | the timescale you ask for (use `weeks`) |
| Crawl issues | the last two crawls | the gap between them — often **not** 7 days |
| Backlinks | the backlink index | the newest page of found/lost links, a few days behind |
| Uptime | Website Health | the monitor's own checks |

They are collected separately and they age separately. Never present them as one timeline, and
never say a change in one caused a change in another — see "No causal chains" below.

There are no impressions, no clicks and no CTR anywhere in this data. Seobility has no Search
Console connection. Anything about traffic has to come from the user's own export.

## Before you spend a call

The helper scripts named below live in this skill's folder (`${CLAUDE_SKILL_DIR}` in Claude Code).
Run them as `python3 <that folder>/scripts/<script>.py`, wherever the current directory is.

0. **Read the previous run.** The check-in has a memory: one small file per project per run,
   under `~/.seobility-checkin/<project_id>/<date>.json` (another folder: the
   `SEOBILITY_CHECKIN_HOME` environment variable or `--home`). Read it before anything else,
   because the job bar in step 7 is defined against it.

   ```bash
   python3 scripts/checkin_state.py previous <project_id>
   ```

   No file means this is the first check-in for this project. Say so once in the report, and
   treat every ranking finding as a watch item — nothing can be persistent against nothing.
   A `history/` folder inside the skill, from an older version, is read once and copied on the
   first `save`; the script says so and never deletes it.

   Note the gap. Two runs eleven weeks apart are not "last week", and the script says so when
   the gap is large. `compare` only uses a run at least five days older than this one, so a
   re-run on the same day says there is nothing to compare instead of matching itself.

1. **Resolve the project.** `list_projects` — one call, but it returns every project of the
   account (~40k characters, and `limit` is ignored), and it already carries the week's shape:
   `page_score {current, delta}`, `problems {current, delta}`, `backlinks {current, delta}`,
   `health_status`, `finished_date`, `is_scheduled_crawl`. Read it before deciding what else to
   pull.

   Accounts routinely hold several projects with the **identical name** for different scopes of
   one site. Disambiguate with `url`, `pages_crawled` and `finished_date`, never by name alone.

2. **Check that this project can produce a check-in at all.** Four things have to be on, and
   they are on independently:

   - **Scheduled crawls.** `is_scheduled_crawl: false` means the audit half has no delta —
     the "previous crawl" may be from last December. Say so and offer a fresh crawl.
   - **Monitored keywords.** `get_keyword_count(project_id)` returns `{"count": n}` for almost
     nothing. Under roughly 20 keywords there is no meaningful ranking week: a verified project
     with 4 keywords produced 2 movers, which is a coin flip, not a trend.
   - **Uptime monitoring.** `health_status: "inactive"` means nobody is watching. That is not
     "no downtime".
   - **Backlink monitoring.** `get_backlinks_overview(project_id)` with `domain.count: 0` means
     there is no backlink profile, which is not a quiet week. Say so and skip the two backlink
     calls.

   **"Not monitored" and "nothing happened" are different sentences.** Write the one that is
   true. A user who reads "no backlinks lost" when backlink monitoring never ran has been told
   something false by omission.

   **The delta tools cannot tell you which of the two it is.** Verified on a project with
   nothing set up: `get_rankings_winners_and_losers` returned `{"winners": [], "losers": [],
   "figures": {"winning_keywords": 0, …}}` — byte for byte what a genuinely quiet week returns.
   `get_backlinks_new` returned `{"data": [], "total": 0}`, the same as a week without new
   links. The checks above are what separates them, and they cost one call each. Run them
   before the delta calls, not after.

   If two or more of them fail, the project is not set up for a weekly check-in. Report what is
   off in one line each and name **`seobility-setup-check`** as the next step, rather than
   writing a week's report on data that cannot show one.

3. **State the window before the findings, not after.** Every section names its own dates.

## Method

### 1. Fix the audit window — `list_crawls`

The audit delta is "since the previous crawl", and the previous crawl is usually not seven days
ago. A verified project ran **every three days**: its `delta` covered three days, not a week.
Another project in the same account had its newest crawl finish nine months ago, with nothing
since — there its `delta` is meaningless whatever the report says.

Take `end_time` of the two newest `status: "done"` crawls and say the real gap in the report:
"crawl of 17.09. against 14.09." — not "this week".

**Check the crawl is complete and the baseline is comparable.** A crawl with `completion_reason: "stopped"` or `is_stopped: true` is partial, even though it reports `status: "done"` and 100%: do not build a plan on it; say so and hand off to seobility-setup-check. For deltas, compare against the last *regular, completed* crawl — skip crawls that were stopped or fetched 0 pages — and say which crawl you compared against. Skip `data_removed` crawls where you need their rows; their summary counts survive, so the audit delta against one still holds. The audit call computes its delta against its own previous crawl and cannot be pointed at another one: when that crawl was stopped or fetched 0 pages, say the audit delta is not comparable and do not report it.

**If there is only one crawl, there is no audit delta — and the rows will not say so.** On a
project with a single crawl, `get_site_audit_problems` returned `delta: 0` on every row while
`overview.problems_found.delta` was `null`. Reading the rows alone produces "nothing changed in
the audit this week", stated with confidence, about a crawl from 2023 that has never been
compared to anything. `overview…delta: null` is the only signal in the payload. Check it first,
and when it is null, write that the project has no second crawl to compare against and offer
one.

The deltas cannot be stretched to a week. `previous_crawl: true` looks like it would give you
the crawl before that, but on `get_site_audit_problems` it **returns the same numbers as the
current crawl**, verified side by side. Do not build a longer window on it.

`list_crawls` returns up to 100 crawl rows by default — pass `limit: 10` (newest first with
`sort_column: "end_time"`, `sort_direction: "desc"`). Once per run; do not call it twice.

### 2. Rankings — two calls

```
get_rankings_overview(project_id, timescale="weeks")
get_rankings_winners_and_losers(project_id, timescale="weeks")
```

The overview is tiny and gives desktop and mobile visibility with their deltas. It is the
headline number for the week.

Its `delta` arrives as a string and is a **percentage change**, not a change in visibility
points — verified by arithmetic on two projects. `"51.8"` means +51.8%, and reporting it as
points overstates a small week by a factor of fifteen. It can also carry a thousands
separator (`"10,366.7"`), so `float()` on it fails: run
`python3 scripts/weekly_deltas.py overview <file>` (or `-` for stdin), which parses it and
suppresses a percentage whose base is under 1 visibility point. Do not quote a percentage
for a project whose keywords were added inside the window either.

**`device` splits the tracked set in two.** Desktop and mobile are separate keyword rows with
separate ids — in a verified project the desktop and mobile winner/loser sets had **zero**
keywords in common, and the two visibility figures moved at very different rates in the same
week (+40.7% desktop, +3.1% mobile). Report both numbers from the overview, then detail one
device and say which. Do not merge the two lists. Pass `device` (`desktop` or `mobile`) to the
winners/losers call and name it: the payload has no device field, and the default is desktop.

The two headline numbers are also **not comparable with each other**. They measure different
keyword sets, so "desktop did better than mobile" is not a statement this data supports. Put
them side by side, say they are separate sets, and leave it there.

**Never mix timescales.** The same keyword came back `+1` over `weeks` and `-1` over `days`.
Both are true for their window. Pick `weeks`, say so, and use it for every ranking figure in the
report.

**The winners/losers payload overflows the tool result** on any real project (~170 movers ≈ 74k
characters). It gets written to a file. Do not read that file — run the script:

```bash
python3 scripts/weekly_deltas.py rankings <saved-file> --limit 8
```

If a result arrived inline instead of as a saved file, write it to a file first (or pipe it to the script and pass `-` as the path). If the host tells you to read an oversized result in full, don't: run the script on the saved file instead.

**Check the ranking data before you use it.** Mark a keyword as suspect, and do not base an action on it, when any of these holds: the own URL appears more than once in the same SERP; a contiguous block at the top of the SERP is all "new" (`rank_change` 1000); `list_keywords` and the keyword's own SERP snapshot (`get_keyword_rankings`) disagree on the own URL's position (never compare with `get_keyword_ranked_pages`: it returns the best-ever position, not the current one); the keyword moved 30 or more places in one check; it was added (`date_added`) inside the comparison window; or the percentage change rests on a base under 1 visibility point. One `get_keyword_overview` call (~500 characters) is a cheap cross-check. Name suspect rows as "not confirmed", never as findings. Note that the weekly view compares Monday to Monday, so a run on another weekday can legitimately differ from the latest-vs-previous view.

The script marks what the payload itself shows with `?` (a move of 30+ places, or a mass new/out block) and names the top mover's `keyword_id` for the cross-check. The rest needs the call.

### 3. Order by visibility, never by positions

This is the rule the whole section stands on. `visibility` is search-volume-weighted and
weighted towards the top positions; `rank_change` is not weighted by anything.

From one real week on a 335-keyword project:

| Keyword | Position change | Visibility change |
|---|---|---|
| user generated content | **-46** (to 64) | -7 |
| pagination | **-1** (to 2) | **-327** |

The 46-position collapse is a page nobody reaches either way. The one-position slip off the top
spot is the largest loss of the week. A report ordered by `rank_change` opens with the wrong row
and buries the right one.

The payload has **no `search_volume` field** — unlike `list_keywords`. `visibility_delta` is the
only impact measure you have here, so use it and do not go fetch volumes for a weekly run.

**Most movement is noise.** In that same week, 69 of 172 movers changed visibility by less than
one point. The script drops them and reports how many it dropped. Never list a keyword that
moved by nothing; the count alone is the honest summary of them.

Two row types are worth pulling out whatever their size, and the script does:

- **`rank_change: "out"`** with `rank: "-/-"` — the keyword left the tracked range entirely.
- **`rank_change: "new"`** — a first-time ranking.

Both are strings in a field that is otherwise an integer. Any formatting that assumes a number
breaks on exactly the rows a check-in wants to show.

Report drop-outs as **one sentence: how many, how much in total, and how concentrated** — never
as a list. The script prints the group total whatever `--limit` you pass, because the total is
what decides whether the group is a finding at all: 33 drop-outs worth -748 points together, four
of them carrying -574, is a job. Nine drop-outs worth less than one keyword's single-position
slip is a clause.

Name individual keywords only for the few that carry the loss, or when they share a page, a topic
or a market. The drop-out rows carry no URL, so a page-level cluster cannot be checked here —
that is a limit on **what you may claim**, not something to tell the reader. Say nothing about
clustering rather than saying it could not be checked.

**Several keywords dropping on one URL is a page-level event; one keyword is not.** The script
flags URLs carrying three or more drops. That cluster is worth a job. A single keyword moving
three places is worth a line at most.

Ignore `figures.delta_rank_winning` and `delta_rank_losing`. They do not reproduce from the rows
— not as a sum of `rank_change` (285 vs a reported 6285), not as a sum of `visibility_delta`
(7218 vs 6285). An unexplained number does not go in a report. The script's own totals do.

### 4. Crawl issues — one call

`get_site_audit_problems(project_id)` returns every issue report with `count` **and** `delta`,
plus `importance`, `priority`, `category` and `total_impact`. One call covers the whole audit
half. Narrow it with `categories` if you only need one area.

Read it in this order:

1. `overview.problems_found.delta` — the net number, and it hides things. A verified week showed
   a net **-43** made of `-29` content, `-23` technique and `+9` structure. "43 issues fewer"
   would have been true and would have hidden the only category that got worse.
2. Re-sort the `problems` rows by `delta` (or pass `sort_by: "delta_desc"`). The API sorts by importance and impact, which is the
   right order for a backlog and the wrong order for a check-in: everything that did not change
   sits at the top.
3. Weigh `delta` against `importance`, not against size. `+12` on medium server response times
   matters less than `+1` on broken pages.

**Exclude every row with `type: "minicheck"` from the delta.** Their `count` is a measurement,
not a number of issues: `minicheck_avglinks` reported `count: 56, delta: 56` (average links per
page, newly measured) and `minicheck_avgloadtimecheck` reported `count: 0.17` (seconds). Read as
issue counts they invent 56 new problems out of nothing. Only `type: "analysis"` rows carry
countable findings.

**`count` is the number of findings, not pages.** Duplicate text reported 384 on a 124-page
site (page–block pairs), so never write "pages" for a count unless the report counts pages.
Deltas also grow with the site: +36 crawled pages gave +412 issues. Take `pages_crawled` from
`list_crawls` and say when new pages account for the rise.

Two more rows lie about their size: `schema-validation` (count 1444) and
`pages-with-unsupported-file-type` (count 563) both carry `total_impact: 0`. They count pages
checked, not pages broken.

### 5. Backlinks — two calls, and they are domain-level

`get_backlinks_new` and `get_backlinks_lost` describe the **domain**, not the project. Every
project on the same domain returns the identical numbers — in a verified account, five projects
all reported `backlinks: 6006, delta: 10`. Say "the domain gained" and not "this project
gained".

Both overflow (~58k characters) and both return **one page of a larger total**: 100 rows of 499
new and 100 of 500 lost. `limit` and `offset` work (offset a multiple of limit); the script says
when the window may reach past the page you have. Page one holds the newest
rows, so on a busy domain it covers roughly the last week and on a quiet one it may span months.
Filter by date yourself and name the window:

```bash
python3 scripts/weekly_deltas.py backlinks <new-file> --lost <lost-file> --days 7
```

The dates to filter on differ between the two: `found_date` for new links, `lost_date` for lost
ones. The script handles both, and it sets the window from the newest date in the payload
rather than from today — backlink data ran four days behind the calendar in a verified run, so
"the last 7 days" counted from today would silently return four days of data.

**Report referring domains, not links.** In one verified week, 100 new links came from 47
domains, and four domains — a directory, a badge widget and two affiliate footers — accounted
for 39 of them. That is four decisions by four people, not 39 wins. The script flags any domain
contributing five or more links. The same pattern appears on the lost side, where one blog
removing a footer widget cost 18 links in one go.

Then read what is left with a sceptical eye: a `rel: "nofollow"` link is not a ranking win, and
the median `rating` of the new links in that week was 21 out of 100.

### 6. Uptime — check what "down" means before you write "outage"

`get_health_status(project_id, time_scale="weeks")` is the compact call: current status,
uptime percentage, and the last alert with a timestamp. `weeks` is 60 buckets of 36 hours,
about 90 days, so the percentage covers a quarter, not a week.

**`info` is the field that decides what happened.** A verified project reported
`status: "down"`, `uptime_percentage: 0` and an alert running since June — and every single
check said `info: "redirect"`. The site was never down. The monitored URL redirects somewhere
else, and the monitor has been reporting a three-month outage ever since. Writing "your site
has been down for three months" would have been the most alarming sentence in the report and
completely wrong.

So: `info: "available"` is up. `info: "redirect"` is a monitor pointed at a URL that redirects —
report it as a **monitoring setup problem**, and the job is to fix the monitored URL. Anything
else (`timeout`, `ssl`, `unknown`, `threshold`), name the value rather than paraphrasing it.

Do not trust `alert`: its time can equal a down check while `status` is up. Read `current`.

Note also that the top-level `status: "ok"` is the API call's status, not the site's. The site's
status is `current.status`.

To count this week's blips, call `get_health_downtimes(project_id, time_scale="days")`
(~8k characters); read the window from its first and last timestamps, name it, and count only
incidents inside the check-in window. The default window returns every 30-minute interval of the last 30 hours,
each with its individual checks, for a single ongoing event: very large.

### 7. One week of ranking movement is not a reason to do anything

Positions fluctuate. That is the normal state of a SERP, not a signal, and a check-in that
turns every weekly wobble into a task is the same failure as padding a quiet week — it just
looks more defensible because it cites a number.

So a ranking finding becomes **a job** only when one of these holds:

- **It persists.** The same keyword or page moved the same way in the previous check-in too.
  Do not eyeball this — `checkin_state.py compare --file <state.json>` (the file `build` wrote) reads the stored run and prints exactly which
  findings are in their second week, which reversed, and which are not confirmed (suspect data
  never persists into a job). Without a previous run, no single week clears this bar.
- **The site's own data shows something that could account for it** — the URL turned up broken,
  noindex, redirected or gone in this week's crawl, or it lost links. Then the job is that
  finding, and it would be a job even without the ranking move.
- **It is structural rather than a fluctuation** — a page dropped out of the index entirely, or
  a whole cluster of keywords on one URL moved together.

Everything else is **a watch item**: name it, say what would make it a real finding, and leave
it. "If X is still at Y next week, it's worth a look" is an honest sentence and
costs the reader nothing. A task they should not do yet costs them an afternoon.

**A job must not smuggle in a cause.** "Read the current top 3 and note what they cover that
your page does not" already assumes the cause is the content — and a one-position slip has a
dozen equally likely explanations, most of them off the page and outside anyone's control. The
"No causal chains" rule below applies to the jobs just as much as to the prose; a job that
presupposes a diagnosis is a causal claim wearing a to-do list.

**Keywords that leave the tracked range are still monitored.** `rank: "-/-"` with
`rank_change: "out"` means the keyword left the tracked range —
not that it was removed from Ranking Monitoring, and not that the site stopped ranking. The
keyword keeps its `keyword_id` and comes back into the payload by itself when it returns. So
there is nothing to look up manually and nothing to fix: next week's run answers it. Report the
group, and make it a watch item.

Note also that these rows carry `best_ranking_url: null` — the payload does not say which page
used to rank. Do not name one.

### 8. At most three jobs

Three is the ceiling, not the target. After the bar in step 7, most weeks produce one or two,
and a genuinely quiet week produces none — then the report says so and lists the watch items.

Each job has to survive being pasted into a task list on its own, with no surrounding paragraph:

- It names the **URL or keyword** it came from. For an audit job the audit call gives counts
  only: make one `get_report(project_id, analysis=<slug>, limit=10)` call per audit job to name
  the URLs. The report lists every affected URL, not only the new ones, so name a few.
- It says **what to change**, not what to look at, and it does not presuppose why. "Check the
  Pagination page" is a topic. "Read the top 3 and see what your content is missing" is a
  diagnosis in disguise. "The wiki page /de/wiki/Pagination has returned a 404 since the crawl on
  18 September: redirect it to the new URL" is a task: it names the change, and the crawl,
  not a theory, says what is wrong.
- It comes from **this week's deltas**, not from the standing backlog. A hundred old image-alt
  findings did not happen this week and are not this week's job. That backlog belongs to audit
  triage, and offering it here is how a weekly check-in turns into the same report every week.

**Watch items go under the jobs, clearly separated**, one line each: what moved, and what would
turn it into a finding. They are not numbered and they are not tasks.

Rank the three by what the week actually did to the site, in this order when they compete:
something broke (pages broken, an outage, a page gone noindex) > a page lost real visibility >
a cluster of issues appeared > an opportunity opened.

### The quiet week

Most weeks nothing important happens. The report has to be able to say that.

> Quiet week. Visibility is up 1.2% on desktop and flat on mobile, no keyword moved more than
> two positions, the crawl found 43 issues fewer than on Sunday and nothing new in the
> very_important bands, and the domain gained 4 referring domains and lost 3. Nothing here
> needs a decision this week.

Then stop, or name **one** thing worth doing with the free week, clearly marked as optional.

Padding a quiet week with three invented jobs is the single failure that kills this skill:
the user runs it weekly, and a report that manufactures work every week stops being read by
week four. The count of movers below the noise floor is a finding. "No new issues in the two
highest importance bands" is a finding. Write those.

### No causal chains

The four data sets are collected on different days by different systems. Nothing here supports
a "because".

- Do not write that the fixed issues lifted the rankings. The crawl and the ranking check are
  days apart, there is no control group, and a core update or a competitor's change would look
  identical in this data.
- Do not write that the lost backlinks caused a position drop. You can report both and say they
  touched the same URL — that is a fact and it is useful. The causal step is not yours to take.
- Do not attribute a site-wide visibility move to anything at all without saying what would
  confirm it.

"Both happened, on the same page, in the same week" is a legitimate and useful sentence. "X
caused Y" is not, and a user who acts on a made-up cause loses a week.

## Output

The reader is not reading a data set. They are asking one question — *is anything wrong, and
what do I do today* — and the report answers it in that order.

**Open with the verdict, in one sentence.** Quiet week, or the one thing that broke. Not a
table, not a number. "Quiet week, one outlier" tells them more in four words than
four visibility figures do.

**Then the jobs.** They are the reason the report exists, so they come before the evidence, not
after it. Each names its URL or keyword and says what to change.

**Then the four sections, as short evidence for what you just claimed** — two or three sentences
each, and only for the sections that have something in them. A section with nothing to say gets
one line or none.

### Every number has to earn its place

This is the rule the readability of the whole report depends on. A number goes in only if the
reader would **do something different** depending on its value. Everything else is noise that
makes the rest harder to find.

Roughly one number per sentence. Concretely:

- **In:** the one or two keywords that moved enough to be worth a job, with their position and
  their visibility change. The net direction of the week. Anything that broke, with its count.
- **Out:** how many rows the noise floor removed. How many keywords moved by nothing. The exact
  counts of every category that did not change. Second-decimal precision anywhere.
- **Grouped, not listed:** a group of small movers is *one sentence with one total*, not a list.
  "33 keywords dropped out of the tracked range, -748 points in total; four of them
  account for -574" is the finding. The other 29 names are not.

### Never explain the tooling to the reader

Everything about how the data is collected — payload shapes, page limits, which fields a row
carries, what the script could or could not compute, how many rows came back — stays out of the
report. It governs **what you are allowed to write**, and then it is done. It is not content.

Three sentences from a real run, all of them true, all of them wrong to print:

> "The rows of the keywords that dropped out carry no URL, so a page cluster check is not
> possible here."
> "Only the newest 100 of about 500 rows can be reached for each."
> "59 of the 176 movements are below one visibility point. Not listed."

The reader cannot act on any of them and did not ask. When a check could not be made, either it
changes a job — then write the job — or it changes nothing, and then it does not get written.

The same goes for the desktop/mobile split. Give both headline figures, name which device the
detail covers, and stop. The reason they are not comparable is a rule for you, not a paragraph
for them.

### No standing disclaimer

Do not end with a fixed list of what the data cannot see. "No clicks, impressions or CTR —
Seobility has no Search Console connection" is true every single week, so by week two it is
furniture, and it makes a report that is already dense end on something nobody reads.

Name a gap **only when it is real for this project and changes what the reader should believe**:
rankings that are not monitored, a crawl with nothing to compare against, uptime that nobody is
watching. One line, in the section it belongs to, and usually it is a job rather than a caveat.

### Mechanics

Write in the language the user is writing to you in. Numbers keep one decimal at most, and every
visibility figure carries its unit: the project-level delta is a **percentage**, the per-keyword
`visibility_delta` is in **points**. Mixing them silently is the easiest way to make this report
wrong.

**Write the state file before you finish.** Not the report — the figures the next run needs.
Build it from the winners/losers payload, add the rest, then save it:

```bash
python3 scripts/checkin_state.py build <project_id> --winners <file> --overview <file> --device <desktop|mobile> --out <state.json>
python3 scripts/checkin_state.py save <project_id> --file <state.json>
```

`build` stores every mover above the noise floor and the drop-out group (pass the device the report details); you add windows,
headline, jobs and watch. Its shape is documented at the top of the script. Store every watch
item **with the condition that would turn it into a finding**, and give one that is not a
keyword (the drop-out group, the crawl problem count) its own `key` and `count`. That condition is the whole point: next week's
run reads it and can say "done" or "second week in a row" instead of starting from zero.

Beyond that, write nothing. The report itself is a message, not a file. If the user wants the
prose archived as well, write one dated Markdown file and say where it went.

Offer, at the end, to run the same check next week. Offer — do not schedule anything and do not
change any setting.

## Guardrails

- **Never invent a job to reach three.** The number of jobs is whatever the week produced, and
  on many weeks that is zero jobs and a watch item.
- **Never turn one week of ranking movement into a task.** It qualifies when it persists, when
  the site's own data accounts for it, or when it is structural. Otherwise it is a watch item.
- **Never write a job that assumes a cause.** "Look at the competitors' content" is a diagnosis,
  not a task.
- **Never merge the four windows into one sentence.** Each section's dates belong to that
  section — but state a window only where it differs from the week the reader assumes. A crawl
  gap of exactly seven days needs no explanation; one of nine months does.
- **Never explain the tooling.** Payload sizes, page limits, missing fields, what the script
  could not compute: these decide what you may write, and then they stay out of the report.
- **Never end with a standing disclaimer.** Name a gap only when it is real for this project and
  changes what the reader should believe.
- **Never claim a cause.** Report what moved and on which page. Stop there.
- **Never report "no problem" for something that is not monitored.** Say it is not monitored.
- **Never order rankings by position change.** Visibility decides what goes first.
- **Never change anything.** This skill is read-only: no crawl start, no keyword added, no
  setting touched. If a crawl is stale or a monitor is misconfigured, that is a job for the
  user, in the list.
- **Local pack stays off unless asked.** Local-pack positions are not organic positions.
- **Never skip the state file.** A run that does not store its figures leaves the next one
  blind, and the persistence bar quietly becomes unreachable.
- **Roughly ten to fifteen calls per run.** `list_projects`, `get_keyword_count`,
  `get_backlinks_overview`, `list_crawls`, two ranking calls, one audit call, two backlink calls,
  one health call, one `get_report` per audit job. Everything else needs a reason.
