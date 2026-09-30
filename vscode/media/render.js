// Webview side of the task detail: same pipeline as the site's fullscreen
// view (src/dashboard/static/js/fullscreen.js) — marked with the options
// markdown.js sets globally on the site (gfm + breaks), then DOMPurify.
(() => {
  const src = JSON.parse(document.getElementById('md').textContent || '""');
  if (!src || typeof marked === 'undefined') return;
  marked.setOptions({ gfm: true, breaks: true });
  const dirty = marked.parse(src);
  document.getElementById('desc').innerHTML =
    typeof DOMPurify === 'undefined' ? '' : DOMPurify.sanitize(dirty);
})();
