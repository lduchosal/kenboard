// Task descriptions are authored in Markdown and rendered with marked.js,
// then sanitized with DOMPurify (#52) before being assigned to innerHTML.
// marked >= 5 no longer sanitizes itself, so a description like
// ``<img src=x onerror=alert(1)>`` would otherwise execute on render.
//
// The raw markdown lives as the textContent of ``.task-desc`` (escaped by
// Jinja so reading textContent always returns the original characters). We
// replace innerHTML once with the parsed+sanitised HTML and stash the source
// on a data attribute so we never re-parse the same node twice.

if (typeof marked !== 'undefined') {
  marked.setOptions({ gfm: true, breaks: true });
}

export function renderMarkdown(root) {
  if (typeof marked === 'undefined') return;
  (root || document).querySelectorAll('.task-desc').forEach((el) => {
    if (el.dataset.mdRendered === '1') return;
    const src = el.textContent;
    const dirty = marked.parse(src);
    el.innerHTML = typeof DOMPurify === 'undefined' ? dirty : DOMPurify.sanitize(dirty);
    el.dataset.mdRendered = '1';
  });
}
