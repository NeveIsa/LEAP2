---
name: default
display_name: Default Lab
description: Starter experiment demonstrating LEAP2 features — RPC, logging, decorators, and registration.
version: "1.0.0"
entry_point: dashboard.html
leap_version: ">=1.0"
require_registration: true
---

# Default Lab

A starter experiment bundled with LEAP2 that exercises all core features: RPC calls, automatic logging, `@nolog` for high-frequency functions, `@noregcheck` for open functions, and student registration.

Use this experiment to verify your setup, learn the client API, and as a reference when building your own experiments.

## What's Included

- **`funcs/math_funcs.py`** — Standard logged functions (square, cubic, add, rosenbrock, bisect, gradient_step). Require registration.
- **`funcs/simulation.py`** — High-frequency functions marked `@nolog` (step, get_position) plus a logged `reset`. Demonstrates selective logging.
- **`funcs/open_funcs.py`** — Utility functions marked `@noregcheck` (echo, ping, server_time). Callable without registration, still logged.
- **`ui/dashboard.html`** — Experiment dashboard showing available functions and quick-start code.
- **`ui/call-log.html`** — Real-time call log viewer using the LogClient.

Browse all functions with their signatures, docs, and decorator flags at `/static/functions.html?exp=default`.

## Testing It

**1. Start the server:**

```bash
leap run
```

**2. Register a student:**

```bash
leap add-student default s001 --name "Alice"
```

**3. Try the Python client:**

```python
from leap.client import RPCClient

client = RPCClient("http://localhost:9000", student_id="s001", experiment="default")

# These calls are logged (require registration)
client.square(7)           # 49
client.gradient_step(5.0, 2.0, lr=0.1)  # 4.8

# Inspect a function
help(client.square)
# square(x: float)
#
# Return x squared.
```

**4. Try open functions (no registration needed):**

```python
# Use any student_id — @noregcheck skips the check
client2 = RPCClient("http://localhost:9000", student_id="guest", experiment="default")
client2.echo("hello")     # "hello"
client2.ping()             # "pong"
```

**5. View logs:**

Open http://localhost:9000/static/logs.html?exp=default in your browser, or use the Python LogClient:

```python
from leap.client import LogClient

logs = LogClient("http://localhost:9000", experiment="default")
print(logs.get_logs(student_id="s001", n=5))
```

**6. Export logs:**

```bash
leap export default                   # -> default.jsonl
leap export default --format csv      # -> default.csv
```

## Seed Data (Optional)

Add demo students and sample log entries in one go:

```bash
python experiments/default/scripts/seed.py
```

Or add students individually:

```bash
leap add-student default s001 --name "Alice"
leap add-student default s002 --name "Bob"
leap add-student default s003 --name "Charlie"
```
