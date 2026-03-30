# Architecture

## Design Goals

1. **Minimal required functionality** — Only essential features; quiz system, IDE dashboard deferred
2. **Decoupled visualizations** — Visualizations consume data via a Log Client interface, not direct `fetch` calls
3. **Clean architecture** — `core/` (pure logic), `api/` (thin HTTP routers), `middleware/`, `client/`
4. **Stable data contract** — Log schema is documented; visualizations depend on the contract, not the transport
5. **URL-scoped experiments** — No server-side "active" experiment; the URL path is the source of truth

## Decoupling Layer

The key architectural improvement over LEAP. Instead of visualizations calling `fetch("/logs?...")` directly:

```
Visualization → LogClient.getLogs() → HTTP API → Storage
```

The Log Client provides a stable interface (`getLogs`, `getLogOptions`, `getAllLogs`). Visualizations depend on the client, not the transport. This means:
- Visualizations can work against any backend (HTTP, file, mock)
- No hardcoded URLs or origin assumptions
- Schema changes are isolated to the client layer

## Separation of Concerns

- **Core** (`leap/core/`) — Pure logic, no HTTP: `rpc.py`, `storage.py`, `auth.py`, `experiment.py`
- **API** (`leap/api/`) — Thin FastAPI routers that call core functions
- **Middleware** — `require_admin` dependency checks session for `/exp/<name>/admin/*`
- **CLI** — Shared `_fn()` functions importable by both CLI and API; no logic duplication
- **UI** — `shared/` (cross-experiment), `landing/`, per-experiment `ui/`; login is handled via modal overlay

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
│   │   ├── rpc.py           # Client / RPCClient (student-facing)
│   │   └── logclient.py     # LogClient (log queries)
│   └── middleware/          # Auth dependency (require_admin)
├── ui/
│   ├── shared/              # theme.css, logclient.js, rpcclient.js, adminclient.js, navbar.js, footer.js, admin-modal.js, functions.html, students.html, logs.html, readme.html
│   ├── landing/             # Landing page (index.html)
│   └── 404.html             # Styled 404 page
├── clients/                 # Non-Python clients
│   ├── julia/               # Julia client
│   └── c/                   # C/C++ client
├── experiments/
│   ├── graph-search/        # BFS/DFS graph exploration
│   └── default/             # Bundled demo experiment
├── config/                  # admin_credentials.json (gitignored)
├── docs/                    # Documentation
├── tests/                   # pytest suite
└── pyproject.toml
```
