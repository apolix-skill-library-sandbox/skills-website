#!/usr/bin/env python3
"""Build the Apolix skills catalog.

Collects every skill (a top-level folder containing SKILL.md) from the
repositories of a GitHub organization and renders a static site into dist/.

    python3 build.py                     # read from GitHub (set GITHUB_TOKEN to avoid rate limits)
    python3 build.py --local ../skills   # read from local clones, one folder per repo
    python3 build.py --local fixtures    # demo data

Standard library only, Python 3.9+.
"""

import argparse
import html
import json
import os
import re
import shutil
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ORG = "apolix-skill-library-sandbox"
SITE_REPO = "skills-website"  # this repo; never scanned for skills

# Display name per repo. Repos not listed fall back to their name without the "skills-" prefix.
DEPARTMENTS = {
    "claude-skill-library": "Shared",
    "skills-finance": "Finance",
    "skills-hr": "HR",
    "skills-management": "Management",
    "skills-office": "Office",
    "skills-operations": "Operations",
    "skills-sales": "Sales",
}

ICON_NAMES = ("icon.svg", "icon.png")
ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"


def department_for(repo):
    if repo in DEPARTMENTS:
        return DEPARTMENTS[repo]
    return repo.replace("skills-", "").replace("-", " ").title()


def parse_frontmatter(text):
    """Return the key/value pairs of a SKILL.md frontmatter block.

    Handles plain, quoted and folded (> or |) scalar values, which is all
    SKILL.md frontmatter uses in practice.
    """
    match = re.match(r"^﻿?---\s*\n(.*?)\n---\s*(\n|$)", text, re.S)
    if not match:
        return {}
    fields, key, block = {}, None, []
    for line in match.group(1).splitlines():
        top = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if top:
            if key and block:
                fields[key] = " ".join(block)
            key, value = top.group(1), top.group(2).strip()
            block = []
            if value in (">", "|", ">-", "|-"):
                continue
            fields[key] = value.strip("\"'")
            key = None
        elif key and line.strip():
            block.append(line.strip())
    if key and block:
        fields[key] = " ".join(block)
    return fields


# --- GitHub source -----------------------------------------------------------

def gh_get(url, raw=False):
    headers = {"User-Agent": "apolix-skills-website"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    if not raw:
        headers["Accept"] = "application/vnd.github+json"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as resp:
        body = resp.read()
    return body.decode("utf-8") if raw else json.loads(body)


def gh_get_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "apolix-skills-website"})
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def skills_from_github():
    repos = gh_get("https://api.github.com/orgs/%s/repos?per_page=100&type=public" % ORG)
    skills = []
    for repo in sorted(repos, key=lambda r: r["name"]):
        if repo["name"] == SITE_REPO or repo["archived"]:
            continue
        name, branch = repo["name"], repo["default_branch"]
        try:
            tree = gh_get("https://api.github.com/repos/%s/%s/git/trees/%s?recursive=1" % (ORG, name, branch))
        except urllib.error.HTTPError as err:
            if err.code == 409:  # empty repository
                continue
            raise
        paths = {item["path"] for item in tree["tree"] if item["type"] == "blob"}
        for path in sorted(paths):
            folder, _, filename = path.partition("/")
            if filename != "SKILL.md":
                continue
            raw_base = "https://raw.githubusercontent.com/%s/%s/%s/%s/" % (
                ORG, name, branch, urllib.parse.quote(folder))
            icon = next((raw_base + n for n in ICON_NAMES if "%s/%s" % (folder, n) in paths), None)
            files = {p[len(folder) + 1:]: raw_base + urllib.parse.quote(p[len(folder) + 1:])
                     for p in paths if p.startswith(folder + "/")}
            with zip_writer(folder) as zf:
                for rel, url in sorted(files.items()):
                    zf.writestr("%s/%s" % (folder, rel), gh_get_bytes(url))
            skills.append(make_skill(name, branch, folder, gh_get(raw_base + "SKILL.md", raw=True), icon))
    return skills


# --- Local source ------------------------------------------------------------

def skills_from_local(base):
    skills = []
    icons_dir = DIST / "icons"
    for repo_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        if repo_dir.name == SITE_REPO:
            continue
        for skill_md in sorted(repo_dir.glob("*/SKILL.md")):
            folder = skill_md.parent
            icon = None
            for n in ICON_NAMES:
                if (folder / n).exists():
                    icons_dir.mkdir(parents=True, exist_ok=True)
                    target = "%s--%s%s" % (repo_dir.name, folder.name, Path(n).suffix)
                    shutil.copy(folder / n, icons_dir / target)
                    icon = "icons/" + target
                    break
            with zip_writer(folder.name) as zf:
                for f in sorted(folder.rglob("*")):
                    if f.is_file() and f.name != ".DS_Store":
                        zf.write(f, "%s/%s" % (folder.name, f.relative_to(folder)))
            skills.append(make_skill(repo_dir.name, "main", folder.name,
                                     skill_md.read_text(encoding="utf-8"), icon))
    return skills


# --- Shared ------------------------------------------------------------------

def zip_writer(folder):
    """ZIP for claude.ai's skill upload: the skill folder at the root of the archive."""
    (DIST / "zips").mkdir(parents=True, exist_ok=True)
    return zipfile.ZipFile(DIST / "zips" / (folder + ".zip"), "w", zipfile.ZIP_DEFLATED)


def make_skill(repo, branch, folder, skill_md, icon):
    meta = parse_frontmatter(skill_md)
    name = meta.get("name") or folder
    if name != folder:
        print("warning: %s/%s: frontmatter name %r does not match folder" % (repo, folder, name), file=sys.stderr)
    if not meta.get("description"):
        print("warning: %s/%s: missing description" % (repo, folder), file=sys.stderr)
    return {
        "name": name,
        "title": name.replace("-", " ").title(),
        "description": meta.get("description", ""),
        "department": department_for(repo),
        "repo": repo,
        "folder": folder,
        "icon": icon,
        "github_url": "https://github.com/%s/%s/tree/%s/%s" % (ORG, repo, branch, urllib.parse.quote(folder)),
        "zip_url": "zips/%s.zip" % urllib.parse.quote(folder),
    }


def render(skills):
    template = (ROOT / "template.html").read_text(encoding="utf-8")
    data = json.dumps({"org": ORG, "skills": skills}, ensure_ascii=False)
    # Keep "</script>" inside descriptions from closing the data block.
    data = data.replace("</", "<\\/")
    page = template.replace("{{ORG}}", html.escape(ORG)).replace("{{DATA}}", data)
    (DIST / "index.html").write_text(page, encoding="utf-8")
    contribute = (ROOT / "contribute.html").read_text(encoding="utf-8")
    (DIST / "contribute.html").write_text(contribute.replace("{{ORG}}", html.escape(ORG)), encoding="utf-8")
    shutil.copy(ROOT / "style.css", DIST / "style.css")
    (DIST / "skills.json").write_text(json.dumps(skills, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--local", type=Path, help="folder with one subfolder per repo, instead of GitHub")
    args = parser.parse_args()

    shutil.rmtree(DIST, ignore_errors=True)
    DIST.mkdir()
    skills = skills_from_local(args.local.resolve()) if args.local else skills_from_github()
    render(skills)
    print("built %d skills into %s" % (len(skills), DIST))


if __name__ == "__main__":
    main()
