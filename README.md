# Apolix Skill Library website

A catalog of every Claude skill in the [apolix-skill-library-sandbox](https://github.com/apolix-skill-library-sandbox) organization, with an icon, a description, a GitHub link and a "Use in Claude" button for each one.

## How it works

`build.py` scans every public repo in the org for top-level `<skill>/SKILL.md` folders, reads the `name` and `description` frontmatter, and writes a static site to `dist/`:

- `index.html`: the catalog with search and department filters
- `zips/<skill>.zip`: the skill packaged for upload to claude.ai
- `skills.json`: the same data, machine-readable

A GitHub Action rebuilds and deploys to GitHub Pages on every push, every 30 minutes, and on demand.

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
python3 build.py --local ../skills     # local clones, one folder per repo
GITHUB_TOKEN=$(gh auth token) python3 build.py   # live from GitHub
python3 -m http.server 8765 --directory dist
```
