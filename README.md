# Seobility MCP Skills

Skills that turn your Seobility data into clear next steps, right inside your AI assistant.

The [Seobility MCP](https://www.seobility.net/en/seo-mcp/) connects your AI assistant to your
Seobility projects. These skills teach the assistant what to do with that data. Ask "What should I
fix first?" and you get a short, prioritized plan with the reasons behind it, not a wall of numbers.

## The skills

| Skill | Ask it something like | What you get |
|---|---|---|
| [`seobility-setup-check`](skills/seobility-setup-check/) | "Is my project set up properly?" | The settings worth changing so your project shows the whole picture: crawl limits, tracked keywords, competitors, Uptime Monitoring. One fix each. |
| [`seobility-weekly-checkin`](skills/seobility-weekly-checkin/) | "What changed this week?" | The ranking, backlink, audit and uptime changes since last week, with the noise filtered out, and three jobs for this week. |
| [`seobility-ranking-opportunities`](skills/seobility-ranking-opportunities/) | "Which keywords am I close to winning?" | An overview of your keywords that are close to entering the top 3 or top 10 positions on Google, with hints on how to close the gap. |
| [`seobility-competitor-gap`](skills/seobility-competitor-gap/) | "Why do the pages above me rank better for this keyword?" | Your page compared with the pages that outrank it in six areas: type of page, on-page and technical, content, links to the page, strength of the website, and your own site. You see where your page is behind and where it isn't, then a ranked list of what you could improve, each with its evidence. |
| [`seobility-audit-triage`](skills/seobility-audit-triage/) | "I ran a crawl and got hundreds of issues. What do I fix first?" | Your Website Audit findings grouped by the one change that fixes them, ranked by impact against effort. |
| [`seobility-findings-to-tickets`](skills/seobility-findings-to-tickets/) | "Turn the audit into tickets for my developer." | Ready-to-paste tickets for the work that needs a developer, and a checklist for everything you can fix yourself. Markdown, JSON, CSV or GitHub issues. |

New to the Seobility MCP? Start with `seobility-setup-check`. The other skills can only be as good as
the project data behind them.

## What you need

- **A Seobility account with MCP access.** The Seobility MCP is available on our paid plans.
- **An AI assistant that supports skills and MCP servers**, for example Claude Code or the Claude
  desktop app. The skills were written and tested with Claude.
- **Python 3.** Some skills run a small helper script to sort through large result lists. The
  scripts use only the Python standard library, so there is nothing extra to install.

## Setup

### 1. Connect the Seobility MCP

The easiest way is to sign in with your Seobility account. There's no API key to create or store.

**Claude (web and desktop app):**

1. Customize → Connectors → + Add → Add custom connector.
2. Name `Seobility`, Remote MCP server URL `https://api.seobility.net/mcp`, then click Continue.
3. Keep the default settings, click Add, then click Connect.
4. Seobility opens in your browser. Click **Allow access**, and you're back in Claude.

**Claude Code:**

```bash
claude mcp add --transport http seobility-mcp https://api.seobility.net/mcp
```

Then start Claude Code, run `/mcp`, select `seobility-mcp` and choose Authenticate. Seobility opens in
your browser. Click **Allow access**, and you're connected.

**Prefer an API key?** Use this if your assistant doesn't support signing in. Create a personal API
key in Seobility under Account Settings → MCP and send it as a request header:

- **URL:** `https://api.seobility.net/mcp`
- **Header:** `X-Seobility-Authorization: <your API key>`

Enter the key on its own, without a `Bearer` prefix.

In Claude Code, for example, add this to the `mcpServers` section of your `~/.claude.json`:

```json
"seobility-mcp": {
  "type": "http",
  "url": "https://api.seobility.net/mcp",
  "headers": { "X-Seobility-Authorization": "<your API key>" }
}
```

Start a new session afterwards so the assistant picks up the server.

### 2. Install the skills

**Claude Code:** copy the folders from `skills/` into `~/.claude/skills/` to use them in every
project, or into `.claude/skills/` inside a single project.

```bash
git clone https://github.com/seobility-net/seobility-mcp-skills.git
cp -r seobility-mcp-skills/skills/* ~/.claude/skills/
```

**Claude desktop app and claude.ai:** download this repository (Code → Download ZIP) and unzip it.
Then zip the skill folder you want to use (for example `skills/seobility-audit-triage`) on its own
and upload it in your Claude settings under Skills.

### 3. Ask

Name the skill directly or ask your question the way you normally would, for example "What
changed on my site this week?", and the assistant picks the right skill.

## Good to know

- **The skills read, they don't change.** They never edit your project settings, keywords or
  competitors. They tell you which setting to change and leave the decision to you. The one
  exception: if your last crawl is more than 30 days old, `seobility-audit-triage` and
  `seobility-findings-to-tickets` ask whether you want a fresh one, and start it only if you say yes.
- **MCP calls use credits.** The skills work from the data Seobility has already stored for your
  project wherever they can, and keep expensive live checks to a minimum.
- **Seobility shows you what to fix. You make the change.** The skills don't fix issues on your
  website, and they don't guarantee ranking gains.
- **The Seobility MCP is in beta.** Tool responses can still change, and a skill may occasionally
  trip over one.

## Make them your own

Every skill is a plain `SKILL.md` file with a `references/` folder and, where needed, a `scripts/`
folder. You're welcome to adapt them to your workflow: change the output format, the language, or
the thresholds. The `references/tool-notes.md` files document how the Seobility MCP tools actually
behave, which is useful if you want to build skills of your own.

## Feedback

Found a bug or have an idea for a new skill? Contact us at support@seobility.net.
We'd love to hear how you use them.

## License

[MIT](LICENSE) © seobility GmbH
