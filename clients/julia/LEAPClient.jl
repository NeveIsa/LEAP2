"""
    LEAPClient

Julia RPC client for LEAP2 — call experiment functions from Julia.

Mirrors the Python RPCClient API: `call()`, dynamic dispatch, `help()`,
`is_registered()`, `fetch_logs()`, `list_functions()`.

# Quick start
```julia
using LEAPClient

c = RPCClient("http://localhost:9000", "s001"; experiment="gradient-descent-2d")
c.df(1.0, 2.0)          # dynamic dispatch
call(c, "df", 1.0, 2.0) # explicit call
help(c)                  # list available functions
```

Requires: `HTTP.jl`, `JSON.jl` — install with `] add HTTP JSON`.
"""
module LEAPClient

using HTTP, JSON

export RPCClient, call, list_functions, is_registered, fetch_logs,
       RPCError, RPCServerError, RPCNetworkError, RPCProtocolError, RPCNotRegisteredError


# ── Exception hierarchy ──

abstract type RPCError <: Exception end

struct RPCServerError <: RPCError
    message::String
    status::Int
end

struct RPCNotRegisteredError <: RPCError
    message::String
end

struct RPCNetworkError <: RPCError
    message::String
end

struct RPCProtocolError <: RPCError
    message::String
end

Base.showerror(io::IO, e::RPCServerError) = print(io, "RPCServerError($(e.status)): $(e.message)")
Base.showerror(io::IO, e::RPCNotRegisteredError) = print(io, "RPCNotRegisteredError: $(e.message)")
Base.showerror(io::IO, e::RPCNetworkError) = print(io, "RPCNetworkError: $(e.message)")
Base.showerror(io::IO, e::RPCProtocolError) = print(io, "RPCProtocolError: $(e.message)")


# ── Client ──

mutable struct RPCClient
    server_url::String
    student_id::String
    experiment::String
    trial::Union{String,Nothing}
    _base::String
    functions::Union{Dict{String,Any},Nothing}
end

"""
    RPCClient(server_url, student_id; experiment=nothing, trial=nothing)

Create a LEAP2 RPC client. Connects to the server and discovers available functions.

# Arguments
- `server_url`: Base URL of the LEAP server (e.g. `"http://localhost:9000"`)
- `student_id`: Your student identifier
- `experiment`: Experiment name (required unless `ENV["DEFAULT_EXPERIMENT"]` is set)
- `trial`: Optional default trial name for all calls
"""
function RPCClient(server_url::String, student_id::String;
                   experiment::Union{String,Nothing}=nothing,
                   trial::Union{String,Nothing}=nothing)
    exp = something(experiment, get(ENV, "DEFAULT_EXPERIMENT", nothing))
    if exp === nothing
        error("experiment must be provided or DEFAULT_EXPERIMENT env must be set")
    end
    url = rstrip(server_url, '/')
    base = "$url/exp/$exp"
    client = RPCClient(url, student_id, exp, trial, base, nothing)
    _discover!(client)
    client
end


# ── Discovery ──

function _discover!(c::RPCClient)
    local resp
    try
        resp = HTTP.get("$(c._base)/functions"; readtimeout=10,
                        status_exception=false)
    catch e
        throw(RPCNetworkError("Error discovering functions: $e"))
    end
    if resp.status != 200
        throw(RPCServerError("Server error discovering functions: HTTP $(resp.status)",
                             resp.status))
    end
    try
        c.functions = JSON.parse(String(resp.body))
    catch e
        throw(RPCProtocolError("Invalid JSON from /functions: $e"))
    end
end


# ── RPC call ──

"""
    call(c::RPCClient, func_name, args...; trial=nothing, kwargs...)

Call a remote experiment function. Returns the function's result.
"""
function call(c::RPCClient, func_name::String, args...; trial=nothing, kwargs...)
    payload = Dict{String,Any}(
        "student_id" => c.student_id,
        "func_name"  => func_name,
        "args"       => collect(Any, args),
        "trial"      => something(trial, c.trial, Some(nothing)),
    )
    if !isempty(kwargs)
        payload["kwargs"] = Dict{String,Any}(String(k) => v for (k, v) in kwargs)
    end

    local resp
    try
        resp = HTTP.post("$(c._base)/call",
                         ["Content-Type" => "application/json"],
                         JSON.json(payload);
                         readtimeout=15, status_exception=false)
    catch e
        throw(RPCNetworkError("Network error calling '$func_name': $e"))
    end

    if resp.status != 200
        detail = nothing
        try
            body = JSON.parse(String(resp.body))
            detail = get(body, "detail", nothing)
        catch; end
        detail = something(detail, "unknown")

        if resp.status == 403
            throw(RPCNotRegisteredError(
                "Student '$(c.student_id)' is not registered. " *
                "Register via the Admin UI ($(c.server_url)/static/students.html" *
                "?exp=$(c.experiment)) or the admin API."))
        end
        throw(RPCServerError(
            "Server error calling '$func_name': $detail (HTTP $(resp.status))",
            resp.status))
    end

    local data
    try
        data = JSON.parse(String(resp.body))
    catch e
        throw(RPCProtocolError("Invalid JSON response for '$func_name': $e"))
    end

    if !haskey(data, "result")
        throw(RPCProtocolError("Missing 'result' in server response for '$func_name'."))
    end

    data["result"]
end


# ── Dynamic dispatch ──

function Base.getproperty(c::RPCClient, name::Symbol)
    # Return real fields directly
    name in fieldnames(RPCClient) && return getfield(c, name)

    funcs = getfield(c, :functions)
    fname = String(name)
    if funcs !== nothing && haskey(funcs, fname)
        return (args...; kwargs...) -> call(c, fname, args...; kwargs...)
    end
    error("No function '$fname' in experiment '$(getfield(c, :experiment))'. " *
          "Use help(c) to see available functions.")
end

# Allow tab-completion in the REPL
function Base.propertynames(c::RPCClient, private::Bool=false)
    base = fieldnames(RPCClient)
    funcs = getfield(c, :functions)
    funcs === nothing && return base
    (base..., Symbol.(keys(funcs))...)
end


# ── Convenience methods ──

"""
    list_functions(c::RPCClient) -> Dict

Return discovered functions with their signatures, docs, and decorator flags.
"""
function list_functions(c::RPCClient)
    if c.functions === nothing
        _discover!(c)
    end
    c.functions
end

"""
    help(c::RPCClient)

Print available remote functions with signatures and decorator badges.
"""
function Base.show(io::IO, ::MIME"text/plain", c::RPCClient)
    funcs = getfield(c, :functions)
    println(io, "RPCClient(\"$(c.server_url)\", \"$(c.student_id)\"; " *
                "experiment=\"$(c.experiment)\")")
    if funcs === nothing || isempty(funcs)
        println(io, "  No functions discovered.")
        return
    end
    println(io, "\nAvailable functions:")
    for name in sort(collect(keys(funcs)))
        info = funcs[name]
        sig = get(info, "signature", "()")
        doc = get(info, "doc", "")
        badges = String[]
        get(info, "nolog", false) && push!(badges, "@nolog")
        get(info, "noregcheck", false) && push!(badges, "@noregcheck")
        get(info, "adminonly", false) && push!(badges, "@adminonly")
        badge_str = isempty(badges) ? "" : "  [$(join(badges, ", "))]"
        println(io, "  $name$sig$badge_str")
        if doc != "" && doc !== nothing
            for line in split(strip(doc), '\n')
                println(io, "      $line")
            end
        end
    end
end

function help(c::RPCClient)
    show(stdout, MIME("text/plain"), c)
end

"""
    is_registered(c::RPCClient) -> Bool

Check whether this client's student_id is registered for the experiment.
"""
function is_registered(c::RPCClient)
    try
        resp = HTTP.get("$(c._base)/is-registered";
                        query=Dict("student_id" => c.student_id),
                        readtimeout=5, status_exception=false)
        if resp.status == 200
            data = JSON.parse(String(resp.body))
            if haskey(data, "registered")
                return Bool(data["registered"])
            end
        end
    catch; end

    # Fallback: probe via a real call
    funcs = getfield(c, :functions)
    (funcs === nothing || isempty(funcs)) &&
        error("Cannot determine registration: no callable functions available.")

    fname = first(keys(funcs))
    try
        call(c, fname)
        return true
    catch e
        e isa RPCNotRegisteredError && return false
        e isa RPCNetworkError && rethrow()
        return true  # other server errors mean we are registered
    end
end

"""
    fetch_logs(c::RPCClient; n=100, student_id=nothing, func_name=nothing,
               trial=nothing, order="latest") -> Vector

Fetch call logs for this experiment.
"""
function fetch_logs(c::RPCClient;
                    n::Int=100,
                    student_id::Union{String,Nothing}=nothing,
                    func_name::Union{String,Nothing}=nothing,
                    trial::Union{String,Nothing}=nothing,
                    order::String="latest")
    params = Dict{String,String}("n" => string(n), "order" => order)
    student_id !== nothing && (params["student_id"] = student_id)
    func_name  !== nothing && (params["func_name"] = func_name)
    trial      !== nothing && (params["trial_name"] = trial)

    local resp
    try
        resp = HTTP.get("$(c._base)/logs"; query=params,
                        readtimeout=10, status_exception=false)
    catch e
        throw(RPCNetworkError("Network error fetching logs: $e"))
    end

    if resp.status != 200
        if resp.status == 403
            sid = something(student_id, c.student_id)
            throw(RPCNotRegisteredError("Student '$sid' is not registered."))
        end
        throw(RPCServerError("Server error fetching logs: HTTP $(resp.status)",
                             resp.status))
    end

    local data
    try
        data = JSON.parse(String(resp.body))
    catch e
        throw(RPCProtocolError("Invalid JSON response from /logs: $e"))
    end

    get(data, "logs", [])
end

end # module
