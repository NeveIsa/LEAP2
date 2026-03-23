/**
 * LEAP2 Log Client — read-only access to experiment logs.
 *
 * Works in browser and standalone JS (Node 18+, Deno).
 * Uses native fetch (available in modern browsers and Node 18+).
 *
 * Usage (browser, ES module):
 *   import { LogClient } from "/static/logclient.js";
 *   const client = LogClient.fromCurrentPage();
 *   const { logs } = await client.getLogs({ n: 50 });
 *
 * Usage (standalone):
 *   import { LogClient } from "./logclient.js";
 *   const client = new LogClient({ baseUrl: "http://localhost:9000", experiment: "default" });
 *   const { logs } = await client.getLogs();
 *
 * @module logclient
 */

export class LogClient {
  /**
   * @param {object} opts
   * @param {string} [opts.baseUrl] - Server origin (e.g. "http://localhost:9000").
   *   Browser default: window.location.origin. Standalone: required.
   * @param {string} opts.experiment - Experiment name.
   */
  constructor({ baseUrl, experiment } = {}) {
    if (!experiment) {
      throw new Error("LogClient: experiment is required");
    }
    if (!baseUrl) {
      if (typeof window !== "undefined" && window.location) {
        baseUrl = window.location.origin;
      } else {
        throw new Error("LogClient: baseUrl is required in non-browser environments");
      }
    }
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.experiment = experiment;
    this._apiBase = this.baseUrl + "/exp/" + this.experiment;
  }

  /**
   * Create a LogClient from the current page context.
   * Detects experiment from URL path (/exp/<name>/...) or query param (?exp=<name>).
   * @param {object} [opts] - Override options (baseUrl).
   * @returns {LogClient}
   */
  static fromCurrentPage(opts = {}) {
    if (typeof window === "undefined") {
      throw new Error("LogClient.fromCurrentPage() is only available in browser environments");
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
      throw new Error(
        "LogClient.fromCurrentPage(): cannot determine experiment from URL path or ?exp= query param"
      );
    }

    return new LogClient({ baseUrl, experiment });
  }

  /**
   * Query logs with optional filters.
   * @param {object} [filters]
   * @param {string} [filters.studentId] - Filter by student ID.
   * @param {string} [filters.trial] - Filter by trial name.
   * @param {string} [filters.funcName] - Filter by function name.
   * @param {string} [filters.startTime] - ISO 8601 lower bound.
   * @param {string} [filters.endTime] - ISO 8601 upper bound.
   * @param {number} [filters.n=100] - Max results (1–10000).
   * @param {string} [filters.order="latest"] - "latest" or "earliest".
   * @param {number} [filters.afterId] - Cursor for pagination.
   * @returns {Promise<{logs: Array}>}
   */
  async getLogs(filters = {}) {
    const params = new URLSearchParams();
    if (filters.studentId) params.set("student_id", filters.studentId);
    if (filters.trial) params.set("trial_name", filters.trial);
    if (filters.funcName) params.set("func_name", filters.funcName);
    if (filters.startTime) params.set("start_time", filters.startTime);
    if (filters.endTime) params.set("end_time", filters.endTime);
    if (filters.n != null) params.set("n", String(filters.n));
    if (filters.order) params.set("order", filters.order);
    if (filters.afterId != null) params.set("after_id", String(filters.afterId));

    const qs = params.toString();
    const url = this._apiBase + "/logs" + (qs ? "?" + qs : "");
    return this._fetch(url);
  }

  /**
   * Get filter options (students, trials) for the experiment.
   * @returns {Promise<{students: Array, trials: Array}>}
   */
  async getLogOptions() {
    return this._fetch(this._apiBase + "/log-options");
  }

  /**
   * Fetch all logs matching filters by auto-paginating with cursor.
   * Iterates until a page returns fewer than `pageSize` results.
   * @param {object} [filters] - Same as getLogs, minus afterId.
   * @param {number} [pageSize=1000] - Page size per request.
   * @returns {Promise<Array>} - All matching log entries.
   */
  async getAllLogs(filters = {}, pageSize = 1000) {
    const allLogs = [];
    let afterId = undefined;
    const order = filters.order || "latest";

    while (true) {
      const opts = { ...filters, n: pageSize, order, afterId };
      const { logs } = await this.getLogs(opts);
      if (!logs || logs.length === 0) break;
      allLogs.push(...logs);
      if (logs.length < pageSize) break;
      afterId = logs[logs.length - 1].id;
    }

    return allLogs;
  }

  /** @private */
  async _fetch(url) {
    const res = await fetch(url);
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const body = await res.json();
        if (body.detail) detail = body.detail;
      } catch (_) {}
      throw new Error(`LogClient: ${detail}`);
    }
    return res.json();
  }
}

export default LogClient;
