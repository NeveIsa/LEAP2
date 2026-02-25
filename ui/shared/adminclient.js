/**
 * LEAP2 Admin Client — browser-only admin operations for experiments.
 *
 * Requires an active admin session (cookie set by /login).
 * All methods throw on 401 (not authenticated) or other HTTP errors.
 *
 * Usage (from experiment UI, e.g. /exp/default/ui/dashboard.html):
 *   import { AdminClient } from "/static/adminclient.js";
 *   const admin = AdminClient.fromCurrentPage();
 *   const students = await admin.listStudents();
 *
 * Usage (from shared page, e.g. /static/students.html?exp=default):
 *   import { AdminClient } from "/static/adminclient.js";
 *   const exp = new URLSearchParams(location.search).get("exp");
 *   const admin = new AdminClient({ experiment: exp });
 *
 * @module adminclient
 */

export class AdminClient {
  /**
   * @param {object} opts
   * @param {string} [opts.baseUrl] - Server origin. Default: window.location.origin.
   * @param {string} opts.experiment - Experiment name.
   */
  constructor({ baseUrl, experiment } = {}) {
    if (!experiment) {
      throw new Error("AdminClient: experiment is required");
    }
    this.baseUrl = (baseUrl || window.location.origin).replace(/\/+$/, "");
    this.experiment = experiment;
    this._apiBase = this.baseUrl + "/exp/" + this.experiment;
  }

  /**
   * Create an AdminClient from the current page context.
   * Detects experiment from URL path (/exp/<name>/...) or query param (?exp=<name>).
   * @param {object} [opts] - Override options.
   * @returns {AdminClient}
   */
  static fromCurrentPage(opts = {}) {
    const baseUrl = opts.baseUrl || window.location.origin;
    let experiment = opts.experiment;

    if (!experiment) {
      const pathMatch = window.location.pathname.match(/\/exp\/([^/]+)/);
      if (pathMatch) experiment = pathMatch[1];
    }

    if (!experiment) {
      experiment = new URLSearchParams(window.location.search).get("exp");
    }

    if (!experiment) {
      throw new Error(
        "AdminClient.fromCurrentPage(): cannot determine experiment from URL path or ?exp= query param"
      );
    }

    return new AdminClient({ baseUrl, experiment });
  }

  /**
   * Add a student to the experiment.
   * @param {string} studentId
   * @param {string} [name] - Display name (defaults to studentId on server).
   * @returns {Promise<object>} - Created student object.
   */
  async addStudent(studentId, name, email) {
    const body = { student_id: studentId };
    if (name) body.name = name;
    if (email) body.email = email;
    return this._post(this._apiBase + "/admin/add-student", body);
  }

  /**
   * List all students in the experiment.
   * @returns {Promise<Array>}
   */
  async listStudents() {
    return this._fetch(this._apiBase + "/admin/students");
  }

  /**
   * Delete a student (cascades to their logs).
   * @param {string} studentId
   * @returns {Promise<object>}
   */
  async deleteStudent(studentId) {
    return this._post(this._apiBase + "/admin/delete-student", { student_id: studentId });
  }

  /**
   * Reload experiment functions from disk.
   * @returns {Promise<object>} - { reloaded: count }
   */
  async reloadFunctions() {
    return this._post(this._apiBase + "/admin/reload-functions");
  }

  /** @private */
  async _fetch(url) {
    const res = await fetch(url, { credentials: "same-origin" });
    return this._handleResponse(res);
  }

  /** @private */
  async _post(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: body ? JSON.stringify(body) : undefined,
    });
    return this._handleResponse(res);
  }

  /** @private */
  async _handleResponse(res) {
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const body = await res.json();
        if (body.detail) detail = body.detail;
      } catch (_) {}
      if (res.status === 401) {
        throw new Error("AdminClient: not authenticated — please log in first");
      }
      throw new Error(`AdminClient: ${detail}`);
    }
    return res.json();
  }
}

export default AdminClient;
