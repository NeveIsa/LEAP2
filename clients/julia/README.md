# LEAP2 Julia Client

Julia RPC client for calling LEAP2 experiment functions. Mirrors the Python `RPCClient` API.

## Install dependencies

```julia
] add HTTP JSON
```

## Quick start

```julia
include("path/to/LEAPClient.jl")
using .LEAPClient

c = RPCClient("http://localhost:9000", "s001"; experiment="gradient-descent-2d")

# Call functions — dynamic dispatch
c.df(1.0, 2.0)          # → (gradient_x, gradient_y)

# Or explicit call
call(c, "df", 1.0, 2.0)

# See what's available
help(c)

# Check registration
is_registered(c)

# Fetch your logs
fetch_logs(c; n=20)
```

## Example: gradient descent

```julia
include("LEAPClient.jl")
using .LEAPClient
using LinearAlgebra

c = RPCClient("http://localhost:9000", "s001"; experiment="gradient-descent-2d")

function gradient_descent(c, x; lr=1e-3, iters=300)
    for _ in 1:iters
        gx, gy = c.df(x...)
        x = x .- lr .* [gx, gy]
    end
    x
end

result = gradient_descent(c, [10.0, 5.0])
println("Minimum at: $result")
```

## API

### Constructor

```julia
RPCClient(server_url, student_id; experiment=nothing, trial=nothing)
```

- `experiment` can also be set via `ENV["DEFAULT_EXPERIMENT"]`
- `trial` sets a default trial name for all calls (overridable per-call)

### Functions

| Function | Description |
|----------|-------------|
| `call(c, name, args...; kwargs...)` | Call a remote function |
| `c.func_name(args...)` | Dynamic dispatch (shorthand for `call`) |
| `list_functions(c)` | Get function metadata as a Dict |
| `help(c)` | Print available functions with signatures |
| `is_registered(c)` | Check if student_id is registered |
| `fetch_logs(c; n, func_name, trial, order)` | Fetch call logs |

### Exceptions

| Type | When |
|------|------|
| `RPCNetworkError` | Cannot reach the server |
| `RPCServerError` | Server returns non-2xx (includes status code) |
| `RPCNotRegisteredError` | Student not registered (HTTP 403) |
| `RPCProtocolError` | Invalid JSON response |
