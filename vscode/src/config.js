// @ts-check
// Resolve the kenboard connection the same way the `ken` CLI does
// (src/dashboard/ken/config.py): env (KEN_*) > .ken > ken.ini, both files
// found by walking up from the workspace folder. Pure Node — no `vscode`
// import — so it is testable with `node --test`.

const fs = require('node:fs');
const path = require('node:path');

const KEN_FILE = '.ken';
const KEN_INI_FILE = 'ken.ini';
const KEN_INI_SECTION = 'ken';
const DEFAULT_BASE_URL = 'http://localhost:9090';
const KEYS = [
  ['project_id', 'KEN_PROJECT_ID'],
  ['base_url', 'KEN_BASE_URL'],
  ['api_token', 'KEN_API_TOKEN'],
];

/**
 * Walk up from `start` looking for a file named `name`.
 * @param {string} start
 * @param {string} name
 * @returns {string | null}
 */
function findFileUpwards(start, name) {
  let cur = path.resolve(start);
  for (;;) {
    const candidate = path.join(cur, name);
    if (fs.existsSync(candidate)) return candidate;
    const parent = path.dirname(cur);
    if (parent === cur) return null;
    cur = parent;
  }
}

/**
 * Parse a `.ken` file: `key=value` lines, `#` comments allowed.
 * @param {string} text
 * @returns {Record<string, string>}
 */
function parseKenFile(text) {
  /** @type {Record<string, string>} */
  const result = {};
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const idx = line.indexOf('=');
    result[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
  }
  return result;
}

/**
 * Parse the `[ken]` section of a `ken.ini` file (configparser subset:
 * `key = value` or `key: value`, `#`/`;` comments, case-insensitive keys).
 * @param {string} text
 * @returns {Record<string, string>}
 */
function parseIniFile(text) {
  /** @type {Record<string, string>} */
  const result = {};
  let inSection = false;
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#') || line.startsWith(';')) continue;
    const section = /^\[(.+)\]$/.exec(line);
    if (section) {
      inSection = section[1].trim() === KEN_INI_SECTION;
      continue;
    }
    if (!inSection) continue;
    const m = /^([^=:]+)[=:](.*)$/.exec(line);
    if (m) result[m[1].trim().toLowerCase()] = m[2].trim();
  }
  return result;
}

/**
 * @typedef {object} KenConfig
 * @property {string | null} projectId
 * @property {string} baseUrl
 * @property {string | null} apiToken
 * @property {string | null} kenFile
 * @property {string | null} iniFile
 */

/**
 * Resolve the config from `startDir` (the workspace folder).
 * @param {string} startDir
 * @param {Record<string, string | undefined>} [env]
 * @returns {KenConfig}
 */
function resolveConfig(startDir, env = process.env) {
  const kenFile = findFileUpwards(startDir, KEN_FILE);
  const iniFile = findFileUpwards(startDir, KEN_INI_FILE);
  const fileData = kenFile ? parseKenFile(fs.readFileSync(kenFile, 'utf8')) : {};
  const iniData = iniFile ? parseIniFile(fs.readFileSync(iniFile, 'utf8')) : {};
  /** @type {Record<string, string | null>} */
  const values = {};
  for (const [key, envName] of KEYS) {
    values[key] = env[envName] || fileData[key] || iniData[key] || null;
  }
  return {
    projectId: values.project_id,
    baseUrl: (values.base_url || DEFAULT_BASE_URL).replace(/\/+$/, ''),
    apiToken: values.api_token,
    kenFile,
    iniFile,
  };
}

/**
 * Return a human-readable reason the config is unusable, or null if OK.
 * @param {KenConfig} cfg
 * @returns {string | null}
 */
function configProblem(cfg) {
  if (!cfg.kenFile && !cfg.iniFile) {
    return 'Aucun ken.ini ni .ken trouvé dans le workspace — lancer `ken init "<onboarding-url>"`.';
  }
  if (!cfg.projectId) return 'project_id manquant (ken.ini ou .ken).';
  if (!cfg.apiToken) return 'api_token manquant (.ken ou KEN_API_TOKEN).';
  return null;
}

module.exports = { findFileUpwards, parseKenFile, parseIniFile, resolveConfig, configProblem };
