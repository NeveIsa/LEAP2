# LeapLive Registry — Design & Implementation Plan

## Overview

**leaplive** is the new name for the LEAP2 framework (previously LEAP).
- PyPI package: `leaplive`
- GitHub org: `github.com/leaplive`
- CLI command: `leaplive` (replaces `leap`)
- Internal Python package stays as `leap` (i.e. `from leap.client import Client` unchanged)
- Registry repo: `github.com/leaplive/registry`

---

## Goal

A decentralized, community-contributed directory of LEAP labs (experiments) that anyone can discover and install via:

```bash
leaplive discover        # browse available labs
leaplive install <name>  # install a lab
leaplive publish         # submit your lab to the registry
```

---

## Registry Format

The registry is a single `registry.yaml` file in `github.com/leaplive/registry`.

### `registry.yaml`

```yaml
- name: gradient-descent
  display_name: Gradient Descent Lab
  description: 2D gradient descent visualization with live student trajectories
  author: sampad
  url: https://github.com/neveisa/leap2
  tags:
    - optimization
    - ml
    - numerical

- name: graph-search
  display_name: Graph Search Lab
  description: BFS/DFS exploration on grids, trees, and custom graphs
  author: neveisa
  url: https://gitlab.com/someone/bfs-lab
  tags:
    - algorithms
    - graphs
```

### Why YAML over JSON?
- More human-readable, easier to write PRs for
- Supports comments
- Less punctuation noise (no quotes, brackets, commas)
- Python reads it trivially with `pyyaml`
- Registry is primarily edited by humans (via PRs), so YAML wins

---

## Discovery

### `leaplive discover`

Fetches `registry.yaml` from `github.com/leaplive/registry` and displays available labs:

```python
import httpx
import yaml

REGISTRY_URL = "https://raw.githubusercontent.com/leaplive/registry/main/registry.yaml"

def discover():
    r = httpx.get(REGISTRY_URL)
    labs = yaml.safe_load(r.text)
    for lab in labs:
        print(f"{lab['name']} — {lab['description']}")
        print(f"  tags: {', '.join(lab.get('tags', []))}")
        print(f"  {lab['url']}")
```

### Why not GitHub Topics?
GitHub topics were considered (`topic:leaplive-lab`) but rejected because:
- Locks discovery to GitHub only
- Labs hosted on GitLab, Codeberg, or university servers would be invisible
- Registry file is platform-agnostic

GitHub topics can be used as a **secondary** discoverability mechanism but the registry is the canonical source.

---

## Publishing — `leaplive publish`

### Full flow

```bash
cd my-bfs-lab
leaplive publish
# → Reading metadata from README.md frontmatter...
# → Found git remote: https://github.com/someone/bfs-lab
# → Adding url to README.md frontmatter...
# → Committing url to git...
# → Is this correct? [Y/n]:
# → Opening issue on leaplive/registry...
# → Done! PR will be created automatically.
# → Track it at: github.com/leaplive/registry/issues/42
```

### Step-by-step implementation

#### 1. Read metadata from README.md frontmatter

LEAP2 already enforces YAML frontmatter in every lab's `README.md`:

```yaml
---
name: bfs-lab
display_name: Graph Search Lab
description: BFS/DFS exploration on grids and trees
version: "1.0.0"
tags: [algorithms, graphs]
---
```

Parse this with `python-frontmatter` or `pyyaml`.

#### 2. Infer git remote URL

```python
import subprocess

def get_git_remote():
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True, text=True
    )
    return result.stdout.strip()
```

#### 3. Write URL back to README.md frontmatter

If `url` is not already in frontmatter, add it automatically and commit:

```python
import re

def update_frontmatter_url(readme_path, url):
    content = open(readme_path).read()
    if "url:" in content:
        return  # already set
    updated = re.sub(
        r'(name:.*\n)',
        f'\\1url: {url}\n',
        content
    )
    open(readme_path, "w").write(updated)

def commit_url(url):
    subprocess.run(["git", "add", "README.md"])
    subprocess.run(["git", "commit", "-m", "chore: add repo url to frontmatter"])
    subprocess.run(["git", "push"])
```

Always confirm with the user before committing to their repo.

#### 4. Submit via `gh` CLI

Use the `gh` CLI to create an issue on `leaplive/registry`. `gh` handles auth transparently — no tokens, no OAuth app needed. User just needs `gh` installed and `gh auth login` run once.

```python
import shutil, subprocess, json

def publish():
    if not shutil.which("gh"):
        print("gh CLI not found. Install: https://cli.github.com")
        print("Or submit manually: https://github.com/leaplive/registry/issues/new")
        return

    # read frontmatter
    meta = read_frontmatter("README.md")
    url = meta.get("url") or get_git_remote()

    # confirm with user
    print(f"Publishing '{meta['name']}' from {url}")
    confirm = input("Proceed? [Y/n]: ")
    if confirm.lower() == "n":
        return

    # update frontmatter if url was missing
    if not meta.get("url"):
        update_frontmatter_url("README.md", url)
        commit_url(url)

    # create issue on registry repo
    body = json.dumps({
        "name": meta["name"],
        "display_name": meta.get("display_name", meta["name"]),
        "description": meta.get("description", ""),
        "url": url,
        "tags": meta.get("tags", [])
    }, indent=2)

    subprocess.run([
        "gh", "issue", "create",
        "--repo", "leaplive/registry",
        "--title", f"Add lab: {meta['name']}",
        "--body", body
    ])
```

---

## Automation — GitHub Action

A GitHub Action on `leaplive/registry` listens for new issues and automatically creates a PR adding the entry to `registry.yaml`. The maintainer (you) just reviews and merges — one click, no manual YAML editing.

### `.github/workflows/add-lab.yml`

```yaml
name: Add Lab from Issue

on:
  issues:
    types: [opened]

jobs:
  add-lab:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Parse issue and add to registry
        uses: actions/github-script@v7
        with:
          script: |
            const body = context.payload.issue.body;
            const meta = JSON.parse(body);

            const fs = require('fs');
            const yaml = require('js-yaml');

            const registry = yaml.load(fs.readFileSync('registry.yaml', 'utf8')) || [];
            registry.push(meta);
            fs.writeFileSync('registry.yaml', yaml.dump(registry));

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v6
        with:
          commit-message: "Add lab: ${{ github.event.issue.title }}"
          title: "Add lab: ${{ github.event.issue.title }}"
          body: "Closes #${{ github.event.issue.number }}"
          branch: "add-lab-${{ github.event.issue.number }}"
```

---

## Manual Submission (fallback)

For users without `gh` CLI, document a manual path:

1. Go to `github.com/leaplive/registry/issues/new`
2. Fill in the issue template with lab metadata
3. GitHub Action creates the PR automatically
4. Maintainer reviews and merges

This requires zero tooling from the submitter — just a GitHub account.

---

## Static Registry Website (future)

Host a searchable lab directory on **GitHub Pages** — reads `registry.yaml` directly, renders a searchable UI. Zero backend, zero hosting cost.

- `github.com/leaplive/registry` — the YAML file + GitHub Actions (free)
- GitHub Pages — static site rendering the directory (free)
- Everything runs on GitHub infrastructure

---

## Summary of Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Registry format | YAML | Human-readable, supports comments, easier PRs |
| Discovery mechanism | Registry file | Platform-agnostic, works for GitLab/Codeberg too |
| Auth for publish | `gh` CLI | No token management, transparent auth |
| URL inference | git remote | Already available, zero config |
| URL persistence | Write back to frontmatter | Lab is self-contained and complete |
| Submission automation | GitHub Action | Maintainer just reviews and merges |
| Hosting | GitHub Pages | Free, zero maintenance |
| Repo name | `registry` | Standard name for this pattern |
