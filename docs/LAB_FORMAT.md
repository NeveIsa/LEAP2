# Lab README Format

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

The `assets/` directory is optional. If present, its contents are served at `/assets/` — useful for lab icons, images, or other static files.

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
