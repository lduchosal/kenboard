// @ts-check
// Thin client over the kenboard REST API (/api/v1), Bearer auth like `ken`.
// Uses the global `fetch` of the VS Code Node runtime — no runtime deps.

/**
 * @typedef {object} Task
 * @property {number} id
 * @property {string} project_id
 * @property {string} title
 * @property {string} description
 * @property {string} status
 * @property {string} who
 * @property {string | null} due_date
 * @property {number} position
 */

/**
 * @typedef {object} Project
 * @property {string} id
 * @property {string} cat_id
 * @property {string} name
 * @property {string} acronym
 */

class KenApi {
  /**
   * @param {import('./config').KenConfig} cfg
   * @param {typeof fetch} [fetchImpl]
   */
  constructor(cfg, fetchImpl = fetch) {
    this.cfg = cfg;
    this.fetch = fetchImpl;
  }

  /**
   * @param {string} method
   * @param {string} path
   * @param {unknown} [body]
   * @returns {Promise<any>}
   */
  async request(method, path, body) {
    /** @type {Record<string, string>} */
    const headers = {
      Authorization: `Bearer ${this.cfg.apiToken}`,
      Accept: 'application/json',
    };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const resp = await this.fetch(`${this.cfg.baseUrl}/api/v1${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!resp.ok) {
      let detail = '';
      try {
        detail = (await resp.json()).error || '';
      } catch {
        // non-JSON error body: status line is enough
      }
      throw new Error(`${method} ${path} → HTTP ${resp.status}${detail ? ` (${detail})` : ''}`);
    }
    return resp.json();
  }

  /** @returns {Promise<Task[]>} */
  listTasks() {
    return this.request('GET', `/tasks?project=${encodeURIComponent(this.cfg.projectId || '')}`);
  }

  /** @returns {Promise<Project>} */
  getProject() {
    return this.request('GET', `/projects/${encodeURIComponent(this.cfg.projectId || '')}`);
  }

  /**
   * @param {number} id
   * @param {string} status
   * @returns {Promise<Task>}
   */
  setStatus(id, status) {
    return this.request('PATCH', `/tasks/${id}`, { status });
  }
}

/**
 * Web URL of the board (category page), or of one task in it (#ID-<id>).
 * @param {string} baseUrl
 * @param {string} catId
 * @param {number} [taskId]
 * @returns {string}
 */
function boardUrl(baseUrl, catId, taskId) {
  const url = `${baseUrl}/cat/${encodeURIComponent(catId)}.html`;
  return taskId === undefined ? url : `${url}#ID-${taskId}`;
}

module.exports = { KenApi, boardUrl };
