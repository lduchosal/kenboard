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

// Open every link inside a markdown-rendered description in a new tab so the
// user doesn't navigate away from the current board (#267). Hooked into
// DOMPurify rather than the marked renderer because it catches every kind
// of link uniformly (markdown ``[text](url)``, autolinks ``<https://...>``,
// raw HTML ``<a href>``) and runs after sanitization, so the URL is already
// validated. ``rel="noopener noreferrer"`` neutralises ``window.opener`` /
// referrer leaks on the new tab.
//
// The registration is lazy + idempotent per DOMPurify instance: a marker
// on the object itself prevents re-adding the hook on each render call,
// and registering at the first ``renderMarkdown`` call (rather than at
// module load) lets test mocks of DOMPurify set themselves up first.
function _ensureLinkOpensNewTab() {
  if (typeof DOMPurify === 'undefined') return;
  if (typeof DOMPurify.addHook !== 'function') return; // shimmed mock
  if (DOMPurify._kenboardLinkHook) return;
  DOMPurify.addHook('afterSanitizeAttributes', (node) => {
    if (node.tagName === 'A') {
      node.setAttribute('target', '_blank');
      node.setAttribute('rel', 'noopener noreferrer');
    }
  });
  DOMPurify._kenboardLinkHook = true;
}

export function renderMarkdown(root) {
  if (typeof marked === 'undefined') return;
  _ensureLinkOpensNewTab();
  (root || document).querySelectorAll('.task-desc').forEach((el) => {
    if (el.dataset.mdRendered === '1') return;
    const src = el.textContent;
    const dirty = marked.parse(src);
    el.innerHTML = typeof DOMPurify === 'undefined' ? dirty : DOMPurify.sanitize(dirty);
    el.dataset.mdRendered = '1';
  });
}
