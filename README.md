# Apolix Skill Library website

A catalog of every Claude skill in the [apolix-skill-library-sandbox](https://github.com/apolix-skill-library-sandbox) organization, with an icon, a description, a GitHub link and a "Use in Claude" button for each one.

## How it works

`build.py` scans every public repo in the org for top-level `<skill>/SKILL.md` folders, reads the `name` and `description` frontmatter, and writes a static site to `dist/`:

- `index.html`: the catalog with search and department filters (from `template.html`)
- `contribute.html`: how to add a skill and how leads review it
- `style.css`: shared styles for both pages
- `zips/<skill>.zip`: the skill packaged for upload to claude.ai
- `skills.json`: the same data, machine-readable

`.github/workflows/deploy.yml` builds the site and deploys it to the Azure Static Web App **ApolixInternalHub** (resource group *Internal*) on every push, every 30 minutes, and on demand. It needs the repo secret `AZURE_STATIC_WEB_APPS_API_TOKEN` (the Static Web App's deployment token).

## Adding a skill

Add a folder to your department's repo, following the convention in the [claude-skill-library README](https://github.com/apolix-skill-library-sandbox/claude-skill-library#naming-convention). It appears on the site after the next build. Add an `icon.svg` or `icon.png` to the folder for a custom icon; otherwise the site shows the skill's initials.

New department repo? Add its display name to `DEPARTMENTS` in `build.py`. Without it, `skills-legal` shows as "Legal".

## "Use in Claude"

There is no official link that turns a skill on directly, so the button:

1. offers the skill as a ZIP, with the steps to upload it under **Customize → Skills** in Claude, and
2. opens Claude (`claude://claude.ai/new?q=…` for the app, `claude.ai/new?q=…` for the web) with "Use the <skill> skill." typed in.

To skip step 1 for everyone, an org owner can provision the skills org-wide under **Organization settings → Plugins & skills**.

## Run locally

Python 3.9+ with no dependencies.

```bash
./serve.sh            # latest skills from GitHub, then serve on http://localhost:8765
./serve.sh --local    # use the local clones in ../skills instead
```

`serve.sh` uses your `gh` login to avoid GitHub's rate limit. Stop it with Ctrl+C.

## PR email notifications

`.github/workflows/notify-leads.yml` emails a repo's leads through Outlook (Microsoft Graph) when a pull request is opened, reopened or marked ready for review. Each skill repo calls it from `.github/workflows/notify-leads.yml`:

```yaml
on:
  pull_request_target:
    types: [opened, reopened, ready_for_review]
jobs:
  notify:
    uses: apolix-skill-library-sandbox/skills-website/.github/workflows/notify-leads.yml@main
    secrets: inherit
```

It needs five **organization secrets** (Settings → Secrets and variables → Actions), shared with the skill repos. Until they exist, the workflow skips without failing.

| Secret | Value |
|---|---|
| `MAIL_TENANT_ID` | Apolix Entra ID tenant ID |
| `MAIL_CLIENT_ID` | App registration's client ID |
| `MAIL_CLIENT_SECRET` | App registration's client secret |
| `MAIL_SENDER` | Mailbox the mail is sent from, e.g. `skills@apolix.nl` |
| `LEAD_EMAILS` | JSON: repo → lead addresses, e.g. `{"skills-sales": ["a@apolix.nl"]}` |

The app registration needs the **Mail.Send** application permission with admin consent, ideally limited to the sender mailbox with an Exchange application access policy.

The workflow never checks out or runs code from the pull request; PR text is only HTML-escaped into the email.
