// Verify the markdown renderer escapes via DOMPurify and is idempotent.

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { renderMarkdown } from './markdown.js';

beforeEach(() => {
  document.body.innerHTML = '';
  // Stub the marked + DOMPurify globals the module reads. Our module only
  // calls ``marked.parse`` and ``DOMPurify.sanitize`` so trivial passthroughs
  // are enough to exercise the gating + idempotency logic.
  globalThis.marked = {
    parse: (s) => `<p>${s}</p>`,
    setOptions: () => {},
  };
  globalThis.DOMPurify = {
    sanitize: (s) => s.replaceAll(/<script[\s\S]*?<\/script>/gi, ''),
  };
});

afterEach(() => {
  globalThis.marked = undefined;
  globalThis.DOMPurify = undefined;
});

describe('renderMarkdown', () => {
  it('parses textContent into innerHTML and marks the node done', () => {
    document.body.innerHTML = '<div class="task-desc">**hi**</div>';
    renderMarkdown();
    const el = document.querySelector('.task-desc');
    expect(el.innerHTML).toBe('<p>**hi**</p>');
    expect(el.dataset.mdRendered).toBe('1');
  });

  it('strips <script> tags via DOMPurify', () => {
    document.body.innerHTML = '<div class="task-desc"><script>alert(1)</script>safe</div>';
    renderMarkdown();
    const el = document.querySelector('.task-desc');
    expect(el.innerHTML).not.toContain('<script>');
    expect(el.innerHTML).toContain('safe');
  });

  it('is idempotent: a second pass does not re-render', () => {
    document.body.innerHTML = '<div class="task-desc">x</div>';
    renderMarkdown();
    const el = document.querySelector('.task-desc');
    el.innerHTML = '<span>changed</span>';
    el.dataset.mdRendered = '1';
    renderMarkdown();
    expect(el.innerHTML).toBe('<span>changed</span>');
  });

  it('scopes to the given root when supplied', () => {
    document.body.innerHTML =
      '<div class="task-desc">a</div><section><div class="task-desc">b</div></section>';
    const section = document.querySelector('section');
    renderMarkdown(section);
    const all = document.querySelectorAll('.task-desc');
    expect(all[0].dataset.mdRendered).toBeUndefined();
    expect(all[1].dataset.mdRendered).toBe('1');
  });
});
