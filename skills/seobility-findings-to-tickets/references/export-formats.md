# Export formats

Four shapes, one rule: **the skill produces the export, the user runs it.** Nothing here creates,
edits or closes anything in a tracker.

All formats carry the same fields, so a set exported as Markdown and as JSON says the same thing:

| Field | Values |
|---|---|
| `id` | `SEO-01`, `SEO-02`, … stable within one run |
| `title` | the change and where it lives, in the developer's words |
| `fix_type` | `config` · `template` · `bulk` · `page` · `editorial`, audit triage's five scored classes. `inspect` and `none` never reach an export |
| `owner` | `dev` · `editor` · `ops` · `external` |
| `route` | `ticket` · `hand-over` · `own-edit` · `check`. Only `ticket` and `hand-over` rows go into a tracker; `hand-over` is the solo owner's ticket for a freelancer |
| `assumption` | optional: one line, when the class was assumed rather than resolved (the expensive branch) |
| `severity` | `total_impact / count`, Seobility's weight for one finding of this kind |
| `problem` | what is wrong, with the measured value |
| `change` | the concrete change |
| `acceptance` | the tool's threshold + the report/defect key to re-check |
| `scope` | affected pages, retrieved count, crawl date, URL-list filename |
| `urls` | list in the body, full list in a file |
| `labels` | `seo` and the fix type. Not the audit category: `technique_and_meta` is a Seobility slug that means nothing to a developer |
| `source` | `analysis` slug + defect key + project id + crawl date |

`source` is what makes a ticket auditable six weeks later. Always include it.

## Markdown — the default

One `###` block per ticket, in the shape shown in `SKILL.md`. Paste-able into Jira, Asana, Linear,
Notion or an email. If the user did not ask for anything else, this is what they get.

## JSON — for anything scripted

```json
[
  {
    "id": "SEO-01",
    "title": "Wiki article template: H1 renders only the term",
    "fix_type": "template",
    "owner": "dev",
    "route": "ticket",
    "assumption": null,
    "severity": 10,
    "problem": "H1 is the bare term (\"Backlinks\", 9 characters); the check expects 20-120.",
    "change": "Render the full article headline in the H1 instead of the term alone.",
    "acceptance": "Every affected page has an H1 of 20-120 characters; heading-h1-problems / h1_toshort reports 0 after the next crawl.",
    "scope": {"findings": 284, "pages": 284, "urls_retrieved": 284, "crawl_date": "2026-09-18",
              "url_file": "tickets/SEO-01-urls.txt"},
    "urls": ["https://…/wiki/Backlinks", "…"],
    "labels": ["seo", "template"],
    "source": {"project_id": 12345, "analysis": "heading-h1-problems", "defect": "h1_toshort"}
  }
]
```

`urls` holds what was retrieved (all pages of the report, unless you stopped early). `scope.findings` is the report's
count of findings and `scope.pages` the number of distinct pages behind them — on link reports
those differ (3 broken links on 2 pages). Never collapse the three into one number.

## CSV — for a Jira or Asana import

One row per ticket, semicolon-separated, UTF-8 with BOM if it is going into Excel:

```
id;title;route;fix_type;assumption;owner;severity;findings;pages;urls_retrieved;crawl_date;acceptance;labels;analysis;defect;url_file
```

Keep the URL list out of the CSV — put the filename in a `url_file` column. Importers truncate
long cells silently, and a truncated URL list is worse than none.

## `gh issue create` — commands, not actions

Write one Markdown file per ticket and one command per ticket. **Use `--body-file`, never an
inline `--body`:** ticket bodies contain newlines, quotes and backticks, and inline quoting breaks
differently in bash, PowerShell and cmd.

```bash
gh issue create \
  --repo <owner>/<repo> \
  --title "[SEO] Wiki article template: H1 renders only the term" \
  --body-file tickets/SEO-01.md \
  --label seo --label template
```

Before handing these over, say three things once:

- Labels must exist in the repo or the command fails. `gh label list` shows what is there.
- The commands are for the user to run; you do not run them.
- If they want all of them at once, they can loop the files themselves — do not write a script
  that fires a batch of issue creations unattended.

## The own-edit checklist — for everything that is not a ticket

Not an export format so much as the other half of the output. It is a table the reader works
through in one sitting, and it carries no ticket furniture at all — no id, no owner, no labels,
because they are the owner:

```markdown
### What you can do yourself — 5 titles, about 20 minutes

| Page | Current | Change to | Limit |
|---|---|---|---|
| /de/wiki/Image_Map | Image Map – Example (199 px) | Add a descriptive phrase to the title | 200-580 px |
```

Same rules as a ticket for everything that matters: the current value, the change, and the limit
that decides when it is done. No effort class, no severity — the reader is not scheduling this
against anything.

**Keep it to roughly 20 rows.** A checklist of 78 long titles is a backlog, not a sitting. Show
the rows that break the limit most, or sit on the pages that matter most, and put the rest into a
file with the same columns. Say how many are in the file.

## The hand-over ticket — for a solo owner

A solo owner with no developer gets almost everything as own edits. What needs code they cannot
change (a theme template, a server rule) still gets a full ticket body, with `route: hand-over`
and one line on top: *"This one needs someone who can edit your theme. Give it to a freelancer
as it is."* Usually one or two per set. Same fields as a ticket, because the freelancer is exactly
the reader who does not have the SEO tool open.

## Jira, Linear, Asana

None of them take a `gh`-style one-liner, and the skill does not have their APIs. Give Markdown,
plus a CSV if they are doing a bulk import. If the user asks for direct creation, say plainly that
this skill does not write into trackers, and hand them the two formats their importer takes.

## The URL list files

One file per ticket, plain text, one URL per line, named after the ticket id:
`tickets/SEO-01-urls.txt`. The script writes it:

```bash
python3 scripts/tickets.py <saved-report.json> --analysis heading-h1-problems     --defect h1_toshort --id SEO-01 --crawl 2026-09-18 --out-dir tickets/
```

Without `--id` the file is named after report and defect instead, which no ticket references, so
pass it. The header comment carries the source:

```
# SEO-01 · heading-h1-problems / h1_toshort · crawl 2026-09-18
# 284 findings, 284 URLs retrieved
https://www.example.com/de/wiki/Backlinks
…
```
