# Lab & Experiment README Format

## Lab README

The root `README.md` of a lab has YAML frontmatter:

```markdown
---
name: starterlab
type: lab
display_name: LEAP Starter Lab
description: Example experiments demonstrating LEAP2 features
icon: /assets/icon.png
author: Sampad Mohanty
organization: University of Southern California
repository: https://github.com/leaplive/starterlab
tags:
- leap
- example
experiments:
- name: default
- name: graph-search
---
```

| Field | Required | Description |
|---|---|---|
| `name` | yes | Machine-readable lab identifier |
| `type` | yes | Must be `lab` |
| `display_name` | no | Human-readable name (shown in navbar badge and info modal) |
| `description` | no | Short description |
| `icon` | no | URL or local path (e.g. `/assets/icon.png`) — shown in navbar badge and info modal |
| `author` | no | Lab creator |
| `organization` | no | Institution or company |
| `repository` | no | Git URL (used by `leap publish`) |
| `tags` | no | List of tags (used by `leap discover`) |
| `experiments` | no | List of `{name}` entries for experiments in the lab |

## Experiment README

Each experiment has a `README.md` with YAML frontmatter:

```markdown
---
name: default
display_name: Default Lab
description: Basic RPC lab with square, cubic, Rosenbrock.
version: "1.0.0"
entry_point: readme
leap_version: ">=1.0"
require_registration: true
pages:
  - {name: "Scores", file: "scores.html", admin: true}
---

# Instructions

1. Register your student ID.
2. Use the RPC client to call functions.
```

| Field | Default | Description |
|---|---|---|
| `name` | folder name | Identifier (folder name is source of truth for routing) |
| `display_name` | folder name | Human-readable name |
| `description` | `""` | Short description |
| `version` | `""` | Experiment version (shown on landing page card) |
| `entry_point` | `readme` | `readme` = experiment README page; or a UI file in `ui/` (e.g. `dashboard.html`) |
| `leap_version` | _(none)_ | Minimum LEAP2 version required (enforced; `>=1.0`, `==1.0.0`, or bare `1.0`) |
| `require_registration` | `true` | Require student registration for RPC |
| `pages` | `[]` | Extra navbar links: `[{name, file, admin}]`. Admin-only pages hidden for non-admins. |

> **Note:** Experiment names must be lowercase. Folder names must match `[a-z0-9][a-z0-9_-]*` — only lowercase letters, digits, hyphens, and underscores are allowed. Folders with uppercase characters are silently skipped at discovery. Use `display_name` in frontmatter for human-readable names.

## Student CSV Format

The CSV file for `leap import-students` must have a header row with a `student_id` column. The `name` and `email` columns are optional.

```csv
student_id,name,email
s001,Alice,alice@example.edu
s002,Bob,bob@example.edu
s003,Charlie,
```

- **`student_id`** (required) — Unique identifier for the student.
- **`name`** (optional) — Defaults to the `student_id` if not provided or empty.
- **`email`** (optional) — Can be left blank.

Duplicates (students whose `student_id` already exists) are skipped, not overwritten. The same format is accepted by the API (`POST /exp/<name>/admin/import-students` with a JSON array) and the Students UI page (file upload or paste).
