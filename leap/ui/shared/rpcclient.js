/**
 * LEAP2 RPC Client — call experiment functions from the browser.
 *
 * Mirrors the Python RPCClient API: call(), dynamic dispatch, help(),
 * isRegistered(), fetchLogs(), listFunctions().
 *
 * Works in browser and standalone JS (Node 18+, Deno).
 * Uses native fetch and Proxy (available in all modern environments).
 *
 * Usage (browser, ES module):
 *   import { RPCClient } from "/static/rpcclient.js";
 *   const client = RPCClient.fromCurrentPage({ studentId: "s001" });
 *   await client.ready();
 *   console.log(await client.square(7));  // 49
 *
 * Usage (standalone):
 *   import { RPCClient } from "./rpcclient.js";
 *   const client = new RPCClient({
 *     baseUrl: "http://localhost:9000",
 *     experiment: "default",
 *     studentId: "s001",
 *   });
 *   console.log(await client.call("square", 7));  // 49
 *
 * @module rpcclient
 */

// ── Exception hierarchy ──

export class RPCError extends Error {
  constructor(message) {
    super(message);
    this.name = "RPCError";
  }
}

export class RPCServerError extends RPCError {
  constructor(message, status) {
    super(message);
    this.name = "RPCServerError";
    this.status = status;
  }
}

export class RPCNotRegisteredError extends RPCServerError {
  constructor(message, status = 403) {
    super(message, status);
    this.name = "RPCNotRegisteredError";
  }
}

export class RPCNetworkError extends RPCError {
  constructor(message) {
    super(message);
    this.name = "RPCNetworkError";
  }
}

export class RPCProtocolError extends RPCError {
  constructor(message) {
    super(message);
    this.name = "RPCProtocolError";
  }
}

// ── Client ──

export class RPCClient {
  /**
   * @param {object} opts
   * @param {string} [opts.baseUrl] - Server origin (e.g. "http://localhost:9000").
   *   Browser default: window.location.origin. Standalone: required.
   * @param {string} opts.experiment - Experiment name.
   * @param {string} opts.studentId - Student identifier.
   * @param {string} [opts.trial] - Default trial name for all calls.
   */
  constructor({ baseUrl, experiment, studentId, trial } = {}) {
    if (!experiment) {
      throw new RPCError("RPCClient: experiment is required");
    }
    if (!studentId) {
      throw new RPCError("RPCClient: studentId is required");
    }
    if (!baseUrl) {
      if (typeof window !== "undefined" && window.location) {
        baseUrl = window.location.origin;
      } else {
        throw new RPCError("RPCClient: baseUrl is required in non-browser environments");
      }
    }
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.experiment = experiment;
    this.studentId = studentId;
    this.trial = trial || null;
    this._apiBase = this.baseUrl + "/exp/" + this.experiment;
    this._functions = null;
    this._discoverPromise = null;

    return new Proxy(this, {
      get(target, prop, receiver) {
        if (prop in target || typeof prop === "symbol") {
          return Reflect.get(target, prop, receiver);
        }
        // Check prototype methods (call, help, etc.)
        if (prop in Object.getPrototypeOf(target)) {
          return Reflect.get(target, prop, receiver);
        }
        // Dynamic dispatch — lazy-discover via call() if functions not yet loaded
        if (target._functions) {
          if (prop in target._functions) {
            return (...args) => target.call(prop, ...args);
          }
          return undefined;
        }
        // Not yet discovered — return lazy caller (call() auto-discovers)
        // Exclude "then" to avoid breaking await/Promise detection
        if (prop === "then") return undefined;
        return (...args) => target.call(prop, ...args);
      },
    });
  }

  /**
   * Create an RPCClient from the current page context.
   * Detects experiment from URL path (/exp/<name>/...) or ?exp=<name> query param.
   * @param {object} opts
   * @param {string} opts.studentId - Student identifier (required).
   * @param {string} [opts.trial] - Default trial name.
   * @param {string} [opts.baseUrl] - Override server origin.
   * @param {string} [opts.experiment] - Override experiment name.
   * @returns {RPCClient}
   */
  static fromCurrentPage(opts = {}) {
    if (typeof window === "undefined") {
      throw new RPCError("RPCClient.fromCurrentPage() is only available in browser environments");
    }

    const baseUrl = opts.baseUrl || window.location.origin;
    let experiment = opts.experiment;

    if (!experiment) {
      const pathMatch = window.location.pathname.match(/\/exp\/([^/]+)/);
      if (pathMatch) {
        experiment = pathMatch[1];
      }
    }

    if (!experiment) {
      experiment = new URLSearchParams(window.location.search).get("exp");
    }

    if (!experiment) {
      throw new RPCError(
        "RPCClient.fromCurrentPage(): cannot determine experiment from URL path or ?exp= query param"
      );
    }

    return new RPCClient({
      baseUrl,
      experiment,
      studentId: opts.studentId,
      trial: opts.trial,
    });
  }

  /**
   * Eagerly discover functions so dynamic dispatch works immediately.
   * @returns {Promise<RPCClient>} this client (for chaining).
   */
  async ready() {
    await this._discover();
    return this;
  }

  /**
   * Call a remote function by name.
   *
   * The last positional argument can be an options object with:
   * - trial: per-call trial override
   * - kwargs: keyword arguments dict
   *
   * @param {string} funcName - Function name.
   * @param {...*} args - Positional arguments, optionally ending with an options object.
   * @returns {Promise<*>} The function result.
   */
  async call(funcName, ...args) {
    // Ensure functions are discovered (for error context)
    if (!this._functions) {
      await this._discover();
    }

    // Check if last arg is an options object (has trial or kwargs keys)
    let callTrial = this.trial;
    let callKwargs = null;
    if (args.length > 0) {
      const last = args[args.length - 1];
      if (last && typeof last === "object" && !Array.isArray(last) && ("trial" in last || "kwargs" in last)) {
        args = args.slice(0, -1);
        if (last.trial !== undefined) callTrial = last.trial;
        if (last.kwargs) callKwargs = last.kwargs;
      }
    }

    const payload = {
      student_id: this.studentId,
      func_name: funcName,
      args: args,
    };
    if (callTrial) payload.trial = callTrial;
    if (callKwargs) payload.kwargs = callKwargs;

    let res;
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000);
      res = await fetch(this._apiBase + "/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
    } catch (err) {
      if (err.name === "AbortError") {
        throw new RPCNetworkError("Request timed out calling '" + funcName + "'");
      }
      throw new RPCNetworkError("Network error calling '" + funcName + "': " + err.message);
    }

    if (!res.ok) {
      let detail = "HTTP " + res.status;
      try {
        const body = await res.json();
        if (body.detail) detail = body.detail;
      } catch (_) {}

      if (res.status === 403) {
        throw new RPCNotRegisteredError(
          "Student '" + this.studentId + "' is not registered. " +
          "Register via the Admin UI (" + this.baseUrl + "/static/students.html" +
          "?exp=" + this.experiment + ") or the admin API."
        );
      }
      throw new RPCServerError(
        "Server error calling '" + funcName + "': " + detail, res.status
      );
    }

    let data;
    try {
      data = await res.json();
    } catch (err) {
      throw new RPCProtocolError("Invalid JSON response for '" + funcName + "': " + err.message);
    }

    if (!("result" in data)) {
      throw new RPCProtocolError("Missing 'result' in server response for '" + funcName + "'.");
    }

    return data.result;
  }

  /**
   * Return discovered functions with signatures and docs.
   * @returns {Promise<object>} Map of function name → { signature, doc, nolog, noregcheck, ratelimit }.
   */
  async listFunctions() {
    if (!this._functions) {
      await this._discover();
    }
    return this._functions;
  }

  /**
   * Print available remote functions to console and return the formatted string.
   * @returns {Promise<string>} Formatted help text.
   */
  async help() {
    if (!this._functions) {
      await this._discover();
    }

    if (!this._functions || Object.keys(this._functions).length === 0) {
      const msg = "No functions discovered from the server.";
      console.log(msg);
      return msg;
    }

    const lines = ["Available functions for experiment '" + this.experiment + "':\n"];
    const names = Object.keys(this._functions).sort();

    for (const name of names) {
      const info = this._functions[name];
      const sig = info.signature || "()";
      const doc = info.doc || "";
      const badges = [];
      if (info.nolog) badges.push("@nolog");
      if (info.noregcheck) badges.push("@noregcheck");
      const badgeStr = badges.length ? "  [" + badges.join(", ") + "]" : "";
      lines.push("  " + name + sig + badgeStr);
      if (doc) {
        for (const line of doc.trim().split("\n")) {
          lines.push("      " + line);
        }
      }
      lines.push("");
    }

    const text = lines.join("\n");
    console.log(text);
    return text;
  }

  /**
   * Check whether this client's studentId is registered.
   * @returns {Promise<boolean>}
   */
  async isRegistered() {
    const url = this._apiBase + "/is-registered?student_id=" + encodeURIComponent(this.studentId);
    try {
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        if (typeof data === "object" && "registered" in data) {
          return !!data.registered;
        }
      }
      return false;
    } catch (_) {
      throw new RPCNetworkError("Network error checking registration.");
    }
  }

  /**
   * Fetch call logs for this experiment.
   * @param {object} [opts]
   * @param {number} [opts.n=100] - Max results.
   * @param {string} [opts.funcName] - Filter by function name.
   * @param {string} [opts.trial] - Filter by trial name.
   * @param {string} [opts.order="latest"] - "latest" or "earliest".
   * @returns {Promise<Array>} Array of log entry objects.
   */
  async fetchLogs(opts = {}) {
    const params = new URLSearchParams();
    params.set("student_id", this.studentId);
    if (opts.n != null) params.set("n", String(opts.n));
    if (opts.funcName) params.set("func_name", opts.funcName);
    if (opts.trial) params.set("trial_name", opts.trial);
    if (opts.order) params.set("order", opts.order);

    const url = this._apiBase + "/logs?" + params.toString();

    let res;
    try {
      res = await fetch(url);
    } catch (err) {
      throw new RPCNetworkError("Network error fetching logs: " + err.message);
    }

    if (!res.ok) {
      if (res.status === 403) {
        throw new RPCNotRegisteredError(
          "Student '" + this.studentId + "' is not registered."
        );
      }
      throw new RPCServerError("Server error fetching logs: HTTP " + res.status, res.status);
    }

    let data;
    try {
      data = await res.json();
    } catch (err) {
      throw new RPCProtocolError("Invalid JSON response from /logs: " + err.message);
    }

    return data.logs || [];
  }

  /** @private */
  async _discover() {
    if (this._discoverPromise) return this._discoverPromise;
    this._discoverPromise = (async () => {
      let res;
      try {
        res = await fetch(this._apiBase + "/functions");
      } catch (err) {
        throw new RPCNetworkError("Error discovering functions: " + err.message);
      }
      if (!res.ok) {
        throw new RPCServerError("Error discovering functions: HTTP " + res.status, res.status);
      }
      try {
        this._functions = await res.json();
      } catch (err) {
        throw new RPCProtocolError("Invalid JSON from /functions: " + err.message);
      }
    })();
    return this._discoverPromise;
  }
}

export default RPCClient;
