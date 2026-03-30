# Client Reference

LEAP provides clients in multiple languages. All clients share the same protocol: HTTP/JSON REST against the LEAP server.

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

## Python Log Client

Visualizations use the Log Client instead of calling the API directly.

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

## JavaScript Log Client (Browser)

```javascript
import { LogClient } from "/static/logclient.js";

const client = LogClient.fromCurrentPage();  // auto-detects experiment from URL
const { logs } = await client.getLogs({ funcName: "square", n: 50 });
const options = await client.getLogOptions();
const allLogs = await client.getAllLogs({ studentId: "s001" });  // auto-paginate
```

Works in browser and standalone JS (Node 18+, Deno) — zero dependencies, uses native `fetch`. The LogClient is read-only (logs and options). To **call** experiment functions from the browser, use the RPCClient.

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

## Julia Client

```julia
using LEAPClient

c = RPCClient("http://localhost:9000", "s001"; experiment="my-lab")
c.df(1.0, 2.0)          # dynamic dispatch
call(c, "df", 1.0, 2.0) # explicit call
help(c)                  # list available functions
is_registered(c)         # true/false
```

Location: `clients/julia/LEAPClient.jl`. Requires `HTTP.jl` and `JSON.jl` (`] add HTTP JSON`).

## C/C++ Client

See [`clients/c/README.md`](../clients/c/README.md) for full documentation.

**C** — one-line calls via `LEAP()` macro:
```c
#include "leap_client.h"
LEAPClient* c = leap_create("http://localhost:9000", "s001", "my-lab", NULL);
double r = LEAP(c, "df", 1.0, 2.0);
leap_destroy(c);
```

**C++** — variadic templates, implicit conversion, function handles:
```cpp
#include "leap_client.hpp"
leap::Client c("http://localhost:9000", "s001", "my-lab");
double r = c("df", 1.0, 2.0);
auto df = c.func("df");
```

Requires libcurl. Build with `make` in `clients/c/`.
