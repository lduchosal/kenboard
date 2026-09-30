// @ts-check
// HTML of the task detail webview. Mirrors the kenboard site's fullscreen
// task view: same vendored marked + DOMPurify run inside the webview, same
// markup and `.fullscreen-*` styles. Pure — testable with `node --test`.

/**
 * @param {string} text
 * @returns {string}
 */
function escapeHtml(text) {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

/**
 * JSON safe to inline in a <script> element (no `</script>` breakout).
 * @param {unknown} value
 * @returns {string}
 */
function inlineJson(value) {
  return JSON.stringify(value)
    .replaceAll('<', '\\u003c')
    .replaceAll('>', '\\u003e')
    .replaceAll('&', '\\u0026');
}

// Copied from src/dashboard/static/style.css (:root palette, global reset,
// body font, `.fullscreen-*` rules) and templates/modals/task_fullscreen.html
// so the panel reads like the site's fullscreen task view (#155).
const SITE_CSS = `
:root {
  --bg: #f0f2f5; --card: #ffffff; --border: #d0d7de; --accent: #0969da;
  --dimmed: #656d76; --text: #1f2328;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 13px; padding: 24px 16px;
}
.fullscreen-card {
  background: var(--card); border-radius: 10px; box-shadow: 0 12px 48px rgba(0, 0, 0, 0.2);
  padding: 32px 36px; max-width: 860px; margin: 0 auto; position: relative;
}
.fullscreen-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.fullscreen-id { font-size: 12px; color: var(--dimmed); font-weight: 600; }
.fullscreen-status {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--dimmed);
  background: var(--bg); border-radius: 4px; padding: 2px 8px;
}
.fullscreen-title { font-size: 22px; font-weight: 700; margin-bottom: 16px; line-height: 1.3; }
.fullscreen-meta { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; font-size: 13px; }
.task-avatar {
  width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; color: white; font-weight: 700; background: var(--dimmed);
}
.fullscreen-desc {
  font-size: 14px; line-height: 1.7; color: var(--text);
  border-top: 1px solid var(--border); padding-top: 16px; min-height: 120px;
}
.fullscreen-desc h1, .fullscreen-desc h2, .fullscreen-desc h3 { margin-top: 16px; margin-bottom: 8px; }
.fullscreen-desc pre { background: var(--bg); border-radius: 4px; padding: 12px; overflow-x: auto; font-size: 12px; }
.fullscreen-desc code { background: var(--bg); border-radius: 3px; padding: 1px 4px; font-size: 12px; }
.fullscreen-desc pre code { padding: 0; }
.fullscreen-desc ul, .fullscreen-desc ol { padding-left: 20px; }
.fullscreen-desc img { max-width: 100%; }
.empty { color: var(--dimmed); }
/* Extension-only: kenboard icon above the "open on the site" button. */
.kb-open {
  position: absolute; top: 24px; right: 28px;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
}
.kb-open img {
  width: 48px; height: 48px; border-radius: 8px; image-rendering: pixelated;
  box-shadow: 0 2px 8px rgba(0,0,0,0.22), 0 0 0 1px rgba(0,0,0,0.08);
}
.btn {
  border: none; border-radius: 4px; padding: 5px 14px; font-size: 11px; font-weight: 600;
  background: var(--accent); color: #fff; text-decoration: none; white-space: nowrap;
}
.btn:hover { opacity: 0.9; }
.fullscreen-header, .fullscreen-title, .fullscreen-meta { margin-right: 150px; }
`;

/**
 * Full webview document.
 * @param {object} args
 * @param {import('./api').Task} args.task
 * @param {string} args.url web URL of the task on the board
 * @param {string} args.cspSource `webview.cspSource`
 * @param {string} args.nonce per-render nonce for the scripts
 * @param {string} args.iconUri webview URI of the kenboard icon
 * @param {string[]} args.scriptUris webview URIs of marked, DOMPurify, render.js (in order)
 * @returns {string}
 */
function detailHtml({ task, url, cspSource, nonce, iconUri, scriptUris }) {
  const csp = [
    "default-src 'none'",
    `style-src 'unsafe-inline'`,
    `img-src ${cspSource} https: data:`,
    `script-src 'nonce-${nonce}'`,
  ].join('; ');
  const scripts = scriptUris
    .map((src) => `<script nonce="${nonce}" src="${escapeHtml(src)}"></script>`)
    .join('\n');
  const who = task.who || '—';
  return `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>${SITE_CSS}</style>
</head>
<body>
<div class="fullscreen-card">
  <div class="kb-open">
    <img src="${escapeHtml(iconUri)}" alt="kenboard">
    <a class="btn" href="${escapeHtml(url)}">Ouvrir sur kenboard</a>
  </div>
  <div class="fullscreen-header">
    <span class="fullscreen-id">#${task.id}</span>
    <span class="fullscreen-status">${escapeHtml(task.status)}</span>
  </div>
  <h2 class="fullscreen-title">${escapeHtml(task.title)}</h2>
  <div class="fullscreen-meta">
    <div class="task-avatar">${escapeHtml(who[0].toUpperCase())}</div>
    <span style="font-weight:600">${escapeHtml(who)}</span>
    <span style="color:var(--dimmed)">${escapeHtml(task.due_date ?? '')}</span>
  </div>
  <div class="fullscreen-desc" id="desc">${task.description ? '' : '<span class="empty">(pas de description)</span>'}</div>
</div>
<script type="application/json" id="md">${inlineJson(task.description || '')}</script>
${scripts}
</body>
</html>`;
}

module.exports = { escapeHtml, inlineJson, detailHtml };
