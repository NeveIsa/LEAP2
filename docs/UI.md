# UI Reference

## Shared Pages

- **Functions** — `/static/functions.html?exp=<name>` — Function cards with syntax-highlighted signatures, docstrings (serif font), and decorator badges (`@nolog`, `@noregcheck`, `@adminonly`, rate limit)
- **Students** — `/static/students.html?exp=<name>` — Add, list, delete students with optional email field; search by ID/name, pagination, bulk CSV import with preview (admin required; shows auth gate when not logged in)
- **Logs** — `/static/logs.html?exp=<name>` — Real-time log viewer with auto-refresh, sparkline visualization, student/function/trial filters; admin users see per-row delete buttons and a "Clear Trial Logs" button when a trial is selected
- **README** — `/static/readme.html?exp=<name>` — Rendered experiment README with academic fonts, syntax highlighting (highlight.js), line numbers, floating table of contents, and frontmatter banner

Shared pages receive the experiment name via the `?exp=` query parameter. Links from experiment UIs and the landing page include this parameter automatically.

## Navbar

Experiment pages use a grouped navbar with a visual divider separating experiment-provided links from shared/static links:

```
[ Lab ]  |  Students (12)  Logs (347)  Functions (5)  README  All Experiments
 ↑ experiment  ↑ divider   ↑ shared (smaller, muted)
```

The navbar is rendered by `navbar.js` — a single shared script included by all pages. It reads `data-page` from `<body>` to highlight the current link, resolves the experiment name from the URL, and enriches link text with live counts from the API.

## Footer

The footer (`footer.js`) is included on every page. It shows server health status, version, and experiment count. When an admin is logged in, additional actions appear:

| Button | Scope | What it does |
|---|---|---|
| **Reload Experiment** | Current experiment | Hot-reloads Python functions from `funcs/` and re-parses README frontmatter — pick up code changes without restarting the server. Only shown on experiment pages. |
| **Rediscover** | All experiments | Re-scans the `experiments/` directory for new or deleted folders. New experiments get their UI routes mounted; removed ones are unmounted. |
| **Change Password** | Global | Opens the password change modal. |
| **Logout** | Global | Ends the admin session. |

## Landing Page Cards

Each experiment card shows:
- **Title** with version badge (from frontmatter `version` field) and README link
- **Description** and "Open" badge (if `require_registration: false`)
- **Sparkline** — 14-day activity chart from recent log data
- **Buttons** — Students (N), Logs (N), Functions (N), Open — with counts inline

## Login Modal

Any page that includes `<script src="/static/footer.js"></script>` automatically gains access to the global admin modal interface. Trigger it from any button:

```html
<button onclick="if(window.LEAP) window.LEAP.showLogin(() => window.location.reload())">Sign In</button>
```
