---
name: leap2
type: lab
display_name: LEAP2
description: "Live Experiments for Active Pedagogy — an interactive learning platform."
author: "Sampad Mohanty"
organization: "University of Southern California"
tags: [education, interactive, rpc, experiments]
---

<div align="center">
  <img src="./banner.svg" alt="LEAP2 Banner" width="800">
</div>

# LEAP2

**Live Experiments for Active Pedagogy** — An interactive learning platform that exposes Python functions as RPC endpoints, logs every call, and serves per-experiment UIs for analysis and visualization.

LEAP2 is a clean-room reimplementation of LEAP, fixing tight coupling problems (visualizations calling API directly, hardcoded origins, active-experiment state) with a decoupled Log Client architecture and URL-scoped experiments.

## Features

- **RPC Server** — Drop Python functions into `experiments/<name>/funcs/` and they're automatically exposed as HTTP endpoints
- **Per-Experiment Isolation** — Each experiment has its own functions, UI, and DuckDB database
- **URL-Scoped** — All APIs live under `/exp/<name>/`; no hidden server state, fully bookmarkable
- **Automatic Logging** — Every RPC call is logged with args, result, timestamp, student ID, and trial
- **Student Registration** — Per-experiment registration with admin management; bulk CSV import via CLI, API, and UI
- **Per-Function Rate Limiting** — Default 120 calls/minute per student; override with `@ratelimit("10/minute")` or disable with `@ratelimit(False)`
- **Flexible Decorators** — `@nolog` for high-frequency calls, `@noregcheck` for open functions, `@ratelimit` for rate control, `@adminonly` for restricted functions, `@withctx` for implicit request context
- **Decoupled Visualizations** — JS + Python Log Clients abstract log queries; visualizations depend on the client interface, not raw API calls
- **Rich Client** — Python RPCClient with `is_registered()`, `help()`, `fetch_logs()`, structured exception hierarchy (`RPCError`, `RPCNotRegisteredError`, etc.); matching JavaScript RPCClient for browser use
- **Admin Client** — Browser-side student management, log deletion, and function reloading via `adminclient.js`
- **Admin Log Management** — Delete individual log entries or clear all logs for a trial from the Logs page (admin only; with confirmation prompt)
- **Polished UI** — Glassmorphism navbar, dark/light themes, sparklines, inline counts, experiment version badges, grouped nav (experiment vs shared links), academic fonts for README/docs, syntax highlighting, floating TOC
- **CLI + Web** — Same logic powers both the `leap` CLI and the FastAPI web API
- **Filtered Log Queries** — Filter by student, function, trial, time range; cursor pagination
- **Export** — `leap export` to JSON Lines or CSV
- **CORS** — Configurable cross-origin support via `CORS_ORIGINS` env

## Quick Start

**Prerequisites:** Python 3.10+

```bash
# Install
pip install -e .

# Set admin password
leap set-password

# Start server (auto-creates project structure on first run)
leap run
```

Open http://localhost:9000 — the landing page lists available experiments.

## Concepts

LEAP organizes work into two levels: **labs** and **experiments**.

- **Experiment** — A self-contained unit of interactive content. Each experiment lives in its own directory under `experiments/` and has its own Python functions, UI, database, and `README.md` with frontmatter (`type: experiment`). Experiments can have their own `requirements.txt` for dependencies. An experiment can exist standalone (its own git repo) or inside a lab.

- **Lab** — A project root that contains one or more experiments. A lab has a root `README.md` with frontmatter (`type: lab`) that lists its experiments. Labs provide the shared infrastructure: config, admin credentials, and the LEAP server. Clone a lab, run `leap init`, and all experiments are ready.

```
my-lab/                      ← lab (type: lab)
├── README.md                # Lab metadata + experiments list
├── assets/                  # Static files served at /assets/ (icons, images)
├── config/
└── experiments/
    ├── sorting-viz/         ← experiment (type: experiment)
    │   ├── README.md
    │   ├── funcs/
    │   ├── ui/
    │   └── requirements.txt
    └── graph-search/        ← experiment (type: experiment)
        ├── README.md
        ├── funcs/
        └── ui/
```

The `assets/` directory is optional. If present, its contents are served at `/assets/` — useful for lab icons, images, or other static files. For example, set `icon: /assets/icon.png` in the lab frontmatter to display a lab icon in the UI.

Labs and experiments are both publishable to the [community registry](https://github.com/leaplive/registry) via `leap publish`. Distribution is git — labs are cloned, experiments are installed into labs with `leap add <url>`.

## Project Structure

```
LEAP2/
├── leap/                    # Python package
│   ├── main.py              # FastAPI app, lifespan, CORS, static mounts
│   ├── config.py            # Root resolution, env vars
│   ├── cli.py               # Typer CLI (shared functions used by API too)
│   ├── core/                # Pure logic, no HTTP
│   │   ├── storage.py       # SQLAlchemy models, DuckDB CRUD
│   │   ├── rpc.py           # RPC execution, @nolog, @noregcheck, @ratelimit, @adminonly, @withctx/ctx
│   │   ├── auth.py          # PBKDF2 hashing, credentials I/O
│   │   └── experiment.py    # Discovery, README parsing, function loading
│   ├── api/                 # FastAPI routers (thin wrappers over core)
│   │   ├── call.py          # POST /exp/<name>/call
│   │   ├── logs.py          # GET /exp/<name>/logs, log-options
│   │   ├── admin.py         # Admin endpoints (auth required)
│   │   ├── experiments.py   # Metadata, health, login/logout
│   │   └── deps.py          # Shared dependencies (experiment lookup, DB session, rate limiter)
│   ├── client/              # Python clients
│   │   ├── rpc.py           # Client / RPCClient (student-facing, with is_registered, help, fetch_logs)
│   │   └── logclient.py     # LogClient (log queries)
│   └── middleware/          # Auth dependency (require_admin)
├── ui/
│   ├── shared/              # theme.css, logclient.js, rpcclient.js, adminclient.js, navbar.js, footer.js, admin-modal.js, functions.html, students.html, logs.html, readme.html
│   ├── landing/             # Landing page (index.html) — experiment cards with sparklines, counts, version badges
│   └── 404.html             # Styled 404 page
├── experiments/
│   ├── graph-search/        # BFS/DFS graph exploration (grids, trees, custom graphs)
│   └── default/             # Bundled demo experiment
│       ├── README.md        # YAML frontmatter + instructions
│       ├── funcs/           # Python functions (auto-discovered)
│       ├── ui/              # optional; entry_point can be "readme" or a file in ui/
│       └── db/              # DuckDB file (gitignored)
├── config/                  # admin_credentials.json (gitignored)
├── tests/                   # pytest suite (596 tests)
└── pyproject.toml
```

## Architecture

### Design Goals

1. **Minimal required functionality** — Only essential features; quiz system, IDE dashboard deferred
2. **Decoupled visualizations** — Visualizations consume data via a Log Client interface, not direct `fetch` calls
3. **Clean architecture** — `core/` (pure logic), `api/` (thin HTTP routers), `middleware/`, `client/`
4. **Stable data contract** — Log schema is documented; visualizations depend on the contract, not the transport
5. **URL-scoped experiments** — No server-side "active" experiment; the URL path is the source of truth

### Decoupling Layer

The key architectural improvement over LEAP. Instead of visualizations calling `fetch("/logs?...")` directly:

```
Visualization → LogClient.getLogs() → HTTP API → Storage
```

The Log Client provides a stable interface (`getLogs`, `getLogOptions`, `getAllLogs`). Visualizations depend on the client, not the transport. This means:
- Visualizations can work against any backend (HTTP, file, mock)
- No hardcoded URLs or origin assumptions
- Schema changes are isolated to the client layer

### Separation of Concerns

- **Core** (`leap/core/`) — Pure logic, no HTTP: `rpc.py`, `storage.py`, `auth.py`, `experiment.py`
- **API** (`leap/api/`) — Thin FastAPI routers that call core functions
- **Middleware** — `require_admin` dependency checks session for `/exp/<name>/admin/*`
- **CLI** — Shared `_fn()` functions importable by both CLI and API; no logic duplication
- **UI** — `shared/` (cross-experiment), `landing/`, per-experiment `ui/`; login is handled via modal overlay

## Creating Experiments

Initialize a **lab** (project root with `experiments/` and `config/`):

```bash
leap init [--password] [--skip-password]
```

This creates `experiments/`, `config/`, `ui/`, sets root `README.md` to `type: lab`, and prompts for an admin password unless credentials already exist or you pass `--skip-password`. Labs are just `git clone` — clone any lab repo and you're ready to go.

Add a **new experiment** (local scaffold or remote clone):

```bash
leap add my-experiment                          # scaffold a new local experiment
leap add https://github.com/user/cool-lab.git   # clone from Git
leap add https://github.com/user/cool-lab.git --name custom-name
```

The root README tracks experiments with their source:

```yaml
---
name: my-lab
type: lab
experiments:
  - name: my-experiment
    source: local
  - name: cool-lab
    source: https://github.com/user/cool-lab.git
---
```

`leap add` automatically updates this list. `leap doctor` detects mismatches between the list and the filesystem and prompts to resolve them (reinstall missing remote experiments, scaffold missing local ones, or remove stale entries).

LEAP discovers experiments from `experiments/` under the [resolved project root](leap/config.py) (`LEAP_ROOT`, or the current directory when it contains `experiments/`).

`leap add my-experiment` scaffolds `experiments/my-experiment/` with a README, stub function file, and dashboard. Edit `funcs/functions.py` to add your own:

```python
def square(x: float) -> float:
    """Return x squared."""
    return x * x

def gradient_step(x: float, lr: float = 0.1) -> float:
    """One gradient descent step on f(x) = (x-3)^2."""
    return x - lr * 2 * (x - 3)
```

Public functions (names not starting with `_`) are auto-discovered and exposed at `POST /exp/my-experiment/call`. If a module defines `__all__`, only those names are exported. Functions prefixed with `_` are private — they stay hidden from the API but can be used as helpers by your exposed functions. Imported names (e.g. `from leap import nolog`) are automatically filtered out — only functions defined in the module file are exposed:

```python
import numpy as np

def _compute_gradient(x, y):
    """Internal helper — not exposed as an RPC endpoint."""
    return 2 * (x - 3), 200 * (y - x**2)

def gradient_step(x: float, y: float, lr: float = 0.01) -> dict:
    """One gradient descent step on the Rosenbrock function."""
    gx, gy = _compute_gradient(x, y)
    return {"x": x - lr * gx, "y": y - lr * gy}

_cache = {}

def predict(model_id: str, x: float) -> float:
    """Run prediction using a cached model."""
    if model_id not in _cache:
        _cache[model_id] = np.load(f"models/{model_id}.npy")
    return float(_cache[model_id] @ [1, x])
```

Use `_` prefixed names for shared math, caching, file I/O, validation, or any logic you don't want students to call directly.

Each experiment must be self-contained — include its own `requirements.txt` with all Python dependencies it needs, independent of other experiments in the same lab. This ensures experiments can be installed, shared, and remixed individually. `leap add` and `leap init` automatically run `pip install -r requirements.txt` for each experiment.

Remove an experiment with:

```bash
leap remove my-experiment          # prompts for confirmation
leap remove my-experiment --yes    # skip confirmation
```

This deletes the experiment directory and removes its entry from the lab README.

## Sharing & Distribution

Distribution is git. LEAP never uploads anything — you push your code with git, and others pull it with git. LEAP provides management (installing experiments into a lab) and an optional discovery layer (the community registry).

### Distributing your work

**Experiments:** Push your experiment to GitHub/GitLab and share the URL. Others install it into their lab with `leap add <url>`. Ensure the experiment's `README.md` has frontmatter (`name`, `description`, `author`, `tags`) and include a `requirements.txt` for dependencies.

**Labs:** Push your entire lab repo to GitHub/GitLab. Others clone it and set it up:

```bash
git clone <url> && cd <name> && leap init
```

`leap init` is idempotent — it skips what's already there and sets up what's missing: installs experiment dependencies (`requirements.txt`), reinstalls remote experiments that were gitignored, and sets the admin password. After init, run `leap run` to start the server.

### Remixing experiments across labs

You can pull experiments from other labs into yours in two ways:

- **From a remote repo:** `leap add <url>` — if the experiment has its own git repo
- **From a local directory:** clone the other lab, then `leap add ./other-lab/experiments/cool-viz` — works for any experiment, even ones without their own repo

```bash
git clone https://github.com/someone/their-lab
leap add ./their-lab/experiments/cool-viz
```

The source must have a `README.md` with `type: experiment` frontmatter. The copy excludes the `.git/` directory and tracks the experiment as local in your lab's README.

### Installing experiments

```bash
leap add <url>                   # clone a remote experiment into your lab
leap add <path>                  # copy an experiment from a local directory
leap add <name>                  # scaffold a new local experiment
leap remove <name>               # remove an experiment
```

`leap add <url>` clones the experiment into `experiments/`, installs `requirements.txt` if present, tracks it in your lab's README, and adds it to `.gitignore` so the lab's git doesn't try to track the nested repo. Running `leap add <url>` again on an already-installed experiment prompts to pull updates. `leap remove` cleans up the `.gitignore` entry.

`leap add <path>` copies an experiment from a local directory (e.g. from another cloned lab). The source must have a `README.md` with `type: experiment` in its frontmatter. The `.git/` directory is excluded from the copy.

### Community registry (optional)

The [leaplive registry](https://github.com/leaplive/registry) is a discovery layer — it helps people find experiments, but is not required for distribution. You can always share experiment URLs directly.

```bash
leap discover                    # browse the registry
leap discover --tag optimization # filter by tag
leap publish my-experiment       # submit your experiment to the registry for review
```

`leap publish` creates a GitHub issue in the registry repo for review. It does not upload or distribute your code — your experiment must already be pushed to a git host. It runs `leap doctor` first and blocks if there are errors. The `repository` field is required — publish looks for it in the experiment's README frontmatter, then falls back to `git remote origin` on the experiment or project root. If no repository is found anywhere, publish fails with an error. Requires the `gh` CLI; otherwise provides a manual submission link.

## Decorators

```python
from leap import adminonly, nolog, noregcheck, ratelimit, withctx, ctx

@nolog
def step(dx):
    """Called at high frequency — not logged."""
    return dx * 2

@noregcheck
def echo(x):
    """Anyone can call this, no registration required. Still logged."""
    return x

@adminonly
def reset_data():
    """Wipe experiment data — admin only."""
    clear_all()
    return "done"

@ratelimit("10/minute")
def expensive_simulation(x):
    """Costly computation — limited to 10 calls/min per student."""
    return run_sim(x)

@ratelimit(False)
def ping():
    """Unrestricted — no rate limit."""
    return "pong"

@withctx
def start():
    """Read caller context implicitly — no extra parameters exposed to students."""
    graph = load_graph(ctx.trial)
    return {"start": graph["start"], "student": ctx.student_id}
```

`@nolog` — Skip logging for high-frequency calls (real-time UI updates, animation, polling). The function still executes and returns results; it just doesn't create a log entry.

`@noregcheck` — Skip registration check for that function regardless of experiment setting. Useful when only some functions should be open (e.g. `echo()` for quick tests, `train()` requires registration).

`@adminonly` — Restrict the function to admin sessions only. Non-admin callers receive a 403 error. Useful for data management, reset functions, or viewing all students' records. The check happens at the API layer before the function executes.

`@ratelimit` — Control per-student rate limiting. All functions have a default rate limit of 120/minute per student. `@ratelimit("N/period")` overrides (period: `second`, `minute`, `hour`, `day`). `@ratelimit(False)` disables rate limiting entirely. Keyed by `(experiment, function, student_id)` — different students are independently limited.

`@withctx` — Inject request context (`student_id`, `trial`, `experiment`) into the function via `ctx`. Import `ctx` from `leap` and access `ctx.student_id`, `ctx.trial`, `ctx.experiment` inside any `@withctx` function. The context is per-request (uses `contextvars`), so there are no race conditions. The `ctx` parameter does **not** appear in the function signature — students never see it.

Functions are reloaded at runtime via `POST /exp/<name>/admin/reload` or the admin UI.

## Python RPC Client

Students interact with experiments via the Python client:

```python
from leap.client import Client

client = Client("http://localhost:9000", student_id="s001", experiment="default")
print(client.square(7))       # 49
print(client.add(3, 5))       # 8
```

`Client` is the preferred import name. The legacy name `RPCClient` still works as an alias.

### Available Methods

```python
# List and explore functions
client.help()                       # Print all functions with sigs, docs, decorator badges
funcs = client.list_functions()     # Raw dict of function metadata

# Check registration
client.is_registered()              # True/False (uses /is-registered endpoint, zero side effects)

# Call functions (two styles)
client.square(7)                    # Dynamic dispatch
client.call("square", 7)           # Explicit

# Fetch logs
logs = client.fetch_logs(n=50)                          # Latest 50 logs
logs = client.fetch_logs(student_id="s001", trial="run-1")  # Filtered
logs = client.fetch_logs(func_name="square", order="earliest")
```

`help()` on any remote function shows its signature and docstring from the server:

```python
help(client.square)
# square(x: float)
#
# Return x squared.
```

The client discovers available functions at init via `GET /exp/<name>/functions`. The `trial_name` parameter tags all subsequent calls for log grouping:

```python
client = Client("http://localhost:9000", student_id="s001",
                 experiment="default", trial_name="bisection-run-1")
```

### Exception Hierarchy

The client raises structured exceptions for error handling:

```python
from leap.client import (
    RPCError,                # Base — catch-all
    RPCServerError,          # Non-2xx response
    RPCNetworkError,         # Connection/timeout failure
    RPCProtocolError,        # Invalid JSON or missing fields
    RPCNotRegisteredError,   # 403 — student not registered (subclass of RPCServerError)
)

try:
    result = client.square(7)
except RPCNotRegisteredError:
    print("Register first!")
except RPCNetworkError:
    print("Server unreachable")
except RPCError as e:
    print(f"Something went wrong: {e}")
```

Dynamic method access raises `AttributeError` with a hint to use `client.help()` when the function doesn't exist.

## Log Client (Decoupled Visualization)

Visualizations use the Log Client instead of calling the API directly.

**JavaScript** (browser, ES module):

```javascript
import { LogClient } from "/static/logclient.js";

const client = LogClient.fromCurrentPage();  // auto-detects experiment from URL
const { logs } = await client.getLogs({ funcName: "square", n: 50 });
const options = await client.getLogOptions();
const allLogs = await client.getAllLogs({ studentId: "s001" });  // auto-paginate
```

Works in browser and standalone JS (Node 18+, Deno) — zero dependencies, uses native `fetch`. The LogClient is read-only (logs and options). To **call** experiment functions from the browser, use the RPCClient (see below).

**Python** (notebooks, scripts):

```python
from leap.client import LogClient

client = LogClient("http://localhost:9000", experiment="default")
logs = client.get_logs(student_id="s001", func_name="square", n=50)
all_logs = client.get_all_logs(func_name="square")  # auto-paginate
options = client.get_log_options()
```

## JavaScript RPC Client (Browser)

Call experiment functions from JavaScript with the same API as the Python client:

```javascript
import { RPCClient } from "/static/rpcclient.js";

// Auto-detect experiment from URL
const client = RPCClient.fromCurrentPage({ studentId: "s001" });

// Dynamic dispatch (functions discovered lazily on first call)
const result = await client.square(7);  // 49
const sum = await client.add(3, 5);     // 8

// Explicit call with per-call trial override
await client.call("square", 7, { trial: "demo" });

// Eager init — discover functions upfront so dynamic dispatch works immediately
const client2 = await new RPCClient({
  baseUrl: "http://localhost:9000",
  experiment: "default",
  studentId: "s001",
  trial: "run-1",
}).ready();
```

### Methods

```javascript
// List and explore functions
const funcs = await client.listFunctions();  // { square: { signature, doc, ... }, ... }
await client.help();                          // Prints to console; returns formatted string

// Check registration
await client.isRegistered();  // true/false

// Fetch logs (filtered to this student)
const logs = await client.fetchLogs({ n: 50 });
const logs2 = await client.fetchLogs({ funcName: "square", trial: "run-1", order: "earliest" });
```

### Error Handling

```javascript
import { RPCClient, RPCError, RPCNotRegisteredError, RPCNetworkError } from "/static/rpcclient.js";

try {
  await client.square(7);
} catch (err) {
  if (err instanceof RPCNotRegisteredError) {
    console.log("Register first!");
  } else if (err instanceof RPCNetworkError) {
    console.log("Server unreachable");
  } else if (err instanceof RPCError) {
    console.log("Something went wrong:", err.message);
  }
}
```

Exported error classes: `RPCError` (base), `RPCServerError` (non-2xx, has `.status`), `RPCNotRegisteredError` (403), `RPCNetworkError` (connection/timeout), `RPCProtocolError` (bad JSON).

## Admin Client (Browser)

Manage students and reload functions from browser UIs:

```javascript
import { AdminClient } from "/static/adminclient.js";

const admin = AdminClient.fromCurrentPage();
await admin.addStudent("s001", "Alice");
const students = await admin.listStudents();
await admin.deleteStudent("s001");
await admin.reloadFunctions();
await admin.importStudents([{ student_id: "s002", name: "Bob" }]);
await admin.exportLogs("csv");                        // or "jsonlines"
await admin.changePassword("old-pass", "new-pass");
await admin.rediscoverExperiments();              // root-level, not experiment-scoped
```

Requires an active admin session (cookie set by the login page). `fromCurrentPage()` detects the experiment from the URL path (`/exp/<name>/...`) or query param (`?exp=<name>`).

## Shared UI Pages

- **Functions** — `/static/functions.html?exp=<name>` — Function cards with syntax-highlighted signatures, docstrings (serif font), and decorator badges (`@nolog`, `@noregcheck`, `@adminonly`, rate limit)
- **Students** — `/static/students.html?exp=<name>` — Add, list, delete students with optional email field; search by ID/name, pagination, bulk CSV import with preview (admin required; shows auth gate when not logged in)
- **Logs** — `/static/logs.html?exp=<name>` — Real-time log viewer with auto-refresh, sparkline visualization, student/function/trial filters; admin users see per-row delete buttons and a "Clear Trial Logs" button when a trial is selected
- **README** — `/static/readme.html?exp=<name>` — Rendered experiment README with academic fonts, syntax highlighting (highlight.js), line numbers, floating table of contents, and frontmatter banner

Shared pages receive the experiment name via the `?exp=` query parameter. Links from experiment UIs and the landing page include this parameter automatically.

### Navbar Structure

Experiment pages use a grouped navbar with a visual divider separating experiment-provided links from shared/static links:

```
[ Lab ]  |  Students (12)  Logs (347)  Functions (5)  README  All Experiments
 ↑ experiment  ↑ divider   ↑ shared (smaller, muted)
```

The navbar is rendered by `navbar.js` — a single shared script included by all pages. It reads `data-page` from `<body>` to highlight the current link, resolves the experiment name from the URL, and enriches link text with live counts from the API.

- **Left** — Experiment-specific links (Lab) at normal prominence
- **Divider** — Subtle vertical line (horizontal on mobile)
- **Right** — Shared links (`nav-shared` class) with inline counts fetched from `/api/experiments` and `/exp/<name>/log-options`

### Footer

The footer (`footer.js`) is included on every page. It shows server health status, version, and experiment count. When an admin is logged in, additional actions appear:

| Button | Scope | What it does |
|---|---|---|
| **Reload Experiment** | Current experiment | Hot-reloads Python functions from `funcs/` and re-parses README frontmatter — pick up code changes without restarting the server. Only shown on experiment pages. |
| **Rediscover** | All experiments | Re-scans the `experiments/` directory for new or deleted folders. New experiments get their UI routes mounted; removed ones are unmounted. Use after adding or deleting an experiment folder. |
| **Change Password** | Global | Opens the password change modal. |
| **Logout** | Global | Ends the admin session. |

These buttons call `POST /exp/{name}/admin/reload` and `POST /api/admin/rediscover` respectively. The page reloads automatically on success.

### Landing Page Cards

Each experiment card shows:
- **Title** with version badge (from frontmatter `version` field) and README link
- **Description** and "Open" badge (if `require_registration: false`)
- **Sparkline** — 14-day activity chart from recent log data
- **Buttons** — Students (N), Logs (N), Functions (N), Open — with counts inline; Students/Logs have orange hover to indicate admin-only

## Log Schema (Data Contract)

Every log entry returned by the API and Log Client follows this shape:

```json
{
  "id": 1,
  "ts": "2025-02-24T12:00:00Z",
  "student_id": "s001",
  "experiment": "default",
  "trial": "bisection-demo",
  "func_name": "square",
  "args": [7],
  "result": 49,
  "error": null
}
```

The DB stores raw JSON strings (`args_json`, `result_json` TEXT columns); the API parses them into `args` and `result` fields before returning.

## API Endpoints

**Experiment-scoped** (under `/exp/<name>/`):

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/exp/<name>/call` | POST | — | Execute a function |
| `/exp/<name>/functions` | GET | — | List functions (signature, doc, nolog, noregcheck) |
| `/exp/<name>/logs` | GET | — | Query logs (filtered, paginated) |
| `/exp/<name>/log-options` | GET | — | Filter dropdown data (students, trials, log_count) |
| `/exp/<name>/is-registered` | GET | — | Check student registration |
| `/exp/<name>/readme` | GET | — | Experiment README (frontmatter + body) |
| `/exp/<name>/admin/add-student` | POST | Admin | Add student |
| `/exp/<name>/admin/import-students` | POST | Admin | Bulk-import students (JSON array) |
| `/exp/<name>/admin/students` | GET | Admin | List students |
| `/exp/<name>/admin/delete-student` | POST | Admin | Delete student + their logs |
| `/exp/<name>/admin/delete-log` | POST | Admin | Delete a single log entry |
| `/exp/<name>/admin/delete-logs` | POST | Admin | Delete logs by student and/or trial |
| `/exp/<name>/admin/reload` | POST | Admin | Reload metadata and functions from disk |
| `/exp/<name>/admin/export-logs` | GET | Admin | Export all logs (JSON; `?format=jsonlines\|csv`) |

**Root-level:**

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Landing page (or redirect if `DEFAULT_EXPERIMENT` set) |
| `/api/experiments` | GET | List experiments with metadata (name, version, student_count, function_count) |
| `/api/health` | GET | Health check (`{ok, version}`) |
| `/api/auth-status` | GET | Check admin login (`{admin: true/false}`) |
| `/login` | GET/POST | Authenticate (JSON body; rate-limited to 5/min); GET redirects to landing |
| `/api/admin/change-password` | POST | Admin | Change admin password (requires current + new) |
| `/api/admin/rediscover` | POST | Admin | Re-scan experiments directory (add new, remove deleted) |
| `/logout` | POST | Clear session |

**RPC payload:**

```json
POST /exp/default/call
{ "student_id": "s001", "func_name": "square", "args": [7], "trial": "run-1" }

Response: { "result": 49 }
Error:    { "detail": "..." }
```

**Function discovery** (`GET /exp/<name>/functions`):

```json
{
  "square": {
    "signature": "(x: float)",
    "doc": "Return x squared.",
    "nolog": false,
    "noregcheck": false,
    "adminonly": false,
    "ratelimit": "default"
  },
  "step": {
    "signature": "(student_id: str, dx: float = 0.0, dy: float = 0.0)",
    "doc": "Move the agent by (dx, dy). Called at high frequency by UI — NOT logged.",
    "nolog": true,
    "noregcheck": false,
    "adminonly": false,
    "ratelimit": "default"
  },
  "echo": {
    "signature": "(x)",
    "doc": "Return input unchanged. Open to all — no registration required. Still logged.",
    "nolog": false,
    "noregcheck": true,
    "adminonly": false,
    "ratelimit": "default"
  }
}
```

## Log Query Filters

`GET /exp/<name>/logs` supports:

| Param | Description |
|---|---|
| `sid` / `student_id` | Filter by student |
| `trial` / `trial_name` | Filter by trial |
| `func_name` | Filter by function (validated against registered functions) |
| `start_time` | ISO 8601 lower bound |
| `end_time` | ISO 8601 upper bound |
| `n` | Limit (1–10,000; default 100) |
| `order` | `latest` (default) or `earliest` |
| `after_id` | Cursor for pagination |

## Database Schema

Per-experiment DuckDB file at `experiments/<name>/db/experiment.db`. SQLAlchemy 2.0 ORM.

**students:**

| Column | Type | Constraints |
|---|---|---|
| `student_id` | VARCHAR | PRIMARY KEY |
| `name` | VARCHAR | NOT NULL |
| `email` | VARCHAR | NULL |

**logs:**

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY (Sequence-based autoincrement) |
| `ts` | TIMESTAMP | NOT NULL, indexed |
| `student_id` | VARCHAR | NOT NULL, indexed |
| `experiment` | VARCHAR | NOT NULL, indexed |
| `trial` | VARCHAR | NULL |
| `func_name` | VARCHAR | NOT NULL, indexed |
| `args_json` | TEXT | NOT NULL |
| `result_json` | TEXT | NULL |
| `error` | TEXT | NULL |

The `experiment` column is redundant within a single per-experiment DB but kept for portability — enables merging DBs for cross-experiment analysis and exports.

## Authentication

- **Global** — One credentials file (`config/admin_credentials.json`); one login unlocks all experiments
- **Protected**: All `/exp/<name>/admin/*` endpoints
- **Public**: `/call`, `/functions`, `/logs`, `/log-options`, `/is-registered`, landing, login, health
- **Logs are public** — Anyone can query `/logs` (intentional for classroom visualizations); deleting logs requires admin

**Invoking the Login Modal in Custom UIs:**
Any page that includes `<script src="/static/footer.js"></script>` automatically gains access to the global admin modal interface. You can trigger it from any button by calling the exposed `LEAP` API:
```html
<button onclick="if(window.LEAP) window.LEAP.showLogin(() => window.location.reload())">Sign In</button>
```

Credentials use PBKDF2-SHA256 (240,000 iterations). First run: if no credentials exist, set via `leap set-password` or `ADMIN_PASSWORD` env. Sessions use `SESSION_SECRET_KEY` env (random per restart if not set).

## Registration

**Experiment-level** — `require_registration` in README frontmatter (default `true`):
- `true`: `student_id` must exist in students table; 403 if not registered
- `false`: any `student_id` accepted; useful for open demos; logging still happens

**Per-function** — `@noregcheck` on a function skips registration regardless of experiment setting.

## CLI Commands

| Command | Purpose |
|---|---|
| `leap run` | Start the server (auto-bootstraps project structure on first run) |
| `leap init` | Set up a lab — idempotent: creates structure, installs deps, reinstalls missing remote experiments |
| `leap add <name>` | Create a new experiment scaffold |
| `leap add <url>` | Clone experiment from Git; auto-installs `requirements.txt` if present |
| `leap add <path>` | Copy experiment from a local directory (must have `type: experiment` frontmatter) |
| `leap remove <name>` | Remove an experiment (deletes directory, updates README tracking) |
| `leap list` | List experiments |
| `leap validate <name>` | Validate experiment setup |
| `leap discover [--tag]` | Browse experiments in the leaplive registry |
| `leap publish <name>` | Publish an experiment to the leaplive registry |
| `leap export <exp> [--format]` | Export logs to `<exp>.jsonl` or `<exp>.csv` |
| `leap set-password` | Set admin password |
| `leap add-student <exp> <id>` | Add a student |
| `leap import-students <exp> <csv>` | Bulk-import students from CSV (see format below) |
| `leap list-students <exp>` | List students |
| `leap config` | Show resolved configuration |
| `leap doctor` | Validate full setup; interactively resolve experiment list mismatches |
| `leap version` | Show version |

### Student CSV Format

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

Duplicates (students whose `student_id` already exists) are skipped, not overwritten. The command reports how many were added, skipped, and errored.

The same format is accepted by the API (`POST /exp/<name>/admin/import-students` with a JSON array) and the Students UI page (file upload or paste).

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `LEAP_ROOT` | cwd | Project root directory |
| `DEFAULT_EXPERIMENT` | _(none)_ | Redirect `/` to this experiment's UI |
| `ADMIN_PASSWORD` | _(none)_ | Non-interactive password setup |
| `SESSION_SECRET_KEY` | _(random)_ | Stable session key for production |
| `CORS_ORIGINS` | _(none)_ | Comma-separated allowed origins (e.g. `http://localhost:3000,https://myapp.edu`) |
| `LEAP_RATE_LIMIT` | `1` (enabled) | Set to `0` to disable the global SlowAPI rate limiter (login throttling, etc.) |
| `LOG_LEVEL` | `INFO` | Python logging level |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests (561 tests)
pytest tests/

# Run with auto-reload
uvicorn leap.main:app --reload --port 9000
```

### Test Structure

```
tests/
├── conftest.py               # Shared fixtures (tmp_root, tmp_credentials)
├── core/                     # storage, auth, experiment, rpc, withctx (212 tests)
│   ├── test_withctx.py       # @withctx decorator + ctx proxy injection (10 tests)
│   └── test_function_discovery.py  # Import filtering in function loading (4 tests)
├── api/
│   ├── test_api.py           # Full API integration (89 tests)
│   ├── test_ui_serving.py    # Static mounts, landing, login (22 tests)
│   └── test_phase4.py        # Shared pages, CORS, function flags (16 tests)
├── client/
│   ├── test_rpcclient.py     # RPCClient: call, dispatch, help, is_registered, fetch_logs, exceptions (42 tests)
│   └── test_logclient.py     # Python LogClient (23 tests)
└── cli/
    ├── test_cli_phase2.py    # init, new, list, validate, config, doctor (83 tests)
    ├── test_cli_phase3.py    # install, copy, gitignore, pip deps (41 tests)
    ├── test_cli_phase4.py    # export (14 tests)
    └── test_cli_phase5.py    # discover, publish (19 tests)
```

All tests use isolated temp directories with per-test DuckDB instances. No shared state.

### Testing experiments in your lab

Experiment-specific tests live in the **lab repo**, not in LEAP2. Create a `tests/` directory in your lab root:

```
my-lab/
├── experiments/
│   ├── gradient-descent/
│   │   └── funcs/
│   │       └── optimize.py
│   └── graph-search/
│       └── funcs/
│           └── graph.py
└── tests/
    ├── test_gradient_descent.py
    └── test_graph_search.py
```

Since experiment names can contain hyphens (not valid Python identifiers), import the module manually:

```python
import importlib.util, sys
from pathlib import Path

_mod_path = Path(__file__).parent.parent / "experiments" / "graph-search" / "funcs" / "graph.py"
_spec = importlib.util.spec_from_file_location("graph_funcs", _mod_path)
mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = mod
_spec.loader.exec_module(mod)

def test_something():
    assert mod.get_graph("grid-3x3")["start"] == "0,0"
```

Run with `pytest tests/` from the lab root. Install `pytest` in your lab's environment (`pip install pytest`).

## Lab README Format

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

## Experiment README Format

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

> [!WARNING]
> **Experiment names must be lowercase.** Folder names must match `[a-z0-9][a-z0-9_-]*` — only lowercase letters, digits, hyphens, and underscores are allowed (e.g. `monte-carlo`, `gradient-descent-2d`). Folders with uppercase characters (like `My-Experiment`) are **silently skipped** at discovery. Use `display_name` in frontmatter for human-readable names.

## Planned

Not yet implemented — tracked for future work.

**Documentation (`docs/` folder):**

| Doc | Audience | Scope |
|---|---|---|
| `CLI.md` | Admins | Full command reference with examples |
| `LOG_CLIENT.md` | Viz authors | JS + Python API, baseUrl, browser + standalone |
| `ADMIN_CLIENT.md` | Admin UI authors | Methods, auth, baseUrl conventions |
| `RPC_CLIENT.md` | Students | RPCClient usage, trial, discovery |
| `DECORATORS.md` | Experiment authors | `@nolog`, `@noregcheck`, `@adminonly`, `@ratelimit`, when to use |
| `DATA_CONTRACT.md` | API consumers | Log schema, query params, stable contract |
| `RUNBOOK.md` | Ops | Start/stop, env vars, credentials, troubleshooting |

Currently the README covers all of this in condensed form.

**Features:**

- ~~**Graph search**~~ — Implemented: `graph-search` experiment with BFS/DFS exploration across grids, trees, and custom graphs; YAML graph definitions; shared SVG renderer; interactive dashboard; admin log-replay visualization
- **Algorithm visualizations** — Port gradient descent, Monte Carlo, power method from LEAP using the Log Client (experiment-specific, in `experiments/<name>/ui/`)
- ~~**Quiz system**~~ — Implemented: `quizlab` experiment with markdown quizzes, server-side grading, `@nolog` private storage, admin scores page with CSV export
- **Monaco/uPlot IDE dashboard** — Rich in-browser coding + plotting
- **DB migrations** — Schema versioning for future LEAP2 changes
- ~~**Experiment dependencies**~~ — Implemented: `leap add <url>` auto-runs `pip install -r requirements.txt` if present in the cloned experiment
- **WebSocket real-time** — Push log updates to browser instead of polling
- ~~**Admin Client extensions**~~ — Implemented: `changePassword` (`POST /api/admin/change-password`), `exportLogs` (`GET /admin/export-logs`)
- ~~**`leap_version` enforcement**~~ — Implemented: parsed from frontmatter and checked at discovery; `leap validate` reports version mismatches

## Citation

If you use LEAP in your work, please cite:

> Sumedh Karajagi, Sampad Bhusan Mohanty, and Bhaskar Krishnamachari. 2026. **LEAP -- Live Experiments for Active Pedagogy.** arXiv:2601.22534. DOI: [10.1145/3770761.3777313](https://doi.org/10.1145/3770761.3777313)

```bibtex
@misc{karajagi2026leapliveexperiments,
      title={LEAP -- Live Experiments for Active Pedagogy},
      author={Sumedh Karajagi and Sampad Bhusan Mohanty and Bhaskar Krishnamachari},
      year={2026},
      eprint={2601.22534},
      archivePrefix={arXiv},
      primaryClass={cs.HC},
      doi={https://doi.org/10.1145/3770761.3777313},
      url={https://arxiv.org/abs/2601.22534},
}
```

## License

MIT
