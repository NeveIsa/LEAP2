# API Reference

## Experiment-Scoped Endpoints

All under `/exp/<name>/`:

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

## Root-Level Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Landing page (or redirect if `DEFAULT_EXPERIMENT` set) |
| `/api/experiments` | GET | List experiments with metadata (name, version, student_count, function_count) |
| `/api/health` | GET | Health check (`{ok, version}`) |
| `/api/auth-status` | GET | Check admin login (`{admin: true/false}`) |
| `/login` | GET/POST | Authenticate (JSON body; rate-limited to 5/min); GET redirects to landing |
| `/api/admin/change-password` | POST | Change admin password (requires current + new) |
| `/api/admin/rediscover` | POST | Re-scan experiments directory (add new, remove deleted) |
| `/logout` | POST | Clear session |

## RPC Payload

```json
POST /exp/default/call
{ "student_id": "s001", "func_name": "square", "args": [7], "trial": "run-1" }

Response: { "result": 49 }
Error:    { "detail": "..." }
```

## Function Discovery

`GET /exp/<name>/functions` returns:

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
