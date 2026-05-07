// Verify the markdown renderer escapes via DOMPurify and is idempotent.

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { renderMarkdown } from './markdown.js';

beforeEach(() => {
  document.body.innerHTML = '';
  // Stub the marked + DOMPurify globals the module reads. The DOMPurify
  // mock is realistic enough to exercise the addHook/afterSanitizeAttributes
  // path (#267): it walks the parsed elements and applies registered hooks
  // before serialising back to HTML.
  globalThis.marked = {
    parse: (s) => {
      // Minimal markdown-link substitution so tests can exercise the
      // DOMPurify link hook (#267) without pulling in real marked.
      const link = /^\[(.+?)\]\((.+?)\)$/.exec(s);
      if (link) return `<a href="${link[2]}">${link[1]}</a>`;
      return `<p>${s}</p>`;
    },
    setOptions: () => {},
  };
  const hooks = { afterSanitizeAttributes: [] };
  globalThis.DOMPurify = {
    sanitize(s) {
      const stripped = s.replaceAll(/<script[\s\S]*?<\/script>/gi, '');
      const tmp = document.createElement('div');
      tmp.innerHTML = stripped;
      for (const node of tmp.querySelectorAll('*')) {
        for (const fn of hooks.afterSanitizeAttributes) fn(node);
      }
      return tmp.innerHTML;
    },
    addHook(event, fn) {
      hooks[event] ||= [];
      hooks[event].push(fn);
    },
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

  // #267: every link inside a rendered task description must open in a new
  // tab so the user doesn't navigate away from the current board.
  it('opens links in a new tab with rel="noopener noreferrer"', () => {
    document.body.innerHTML = '<div class="task-desc">[click](https://example.com)</div>';
    renderMarkdown();
    const a = document.querySelector('.task-desc a');
    expect(a).not.toBeNull();
    expect(a.getAttribute('href')).toBe('https://example.com');
    expect(a.getAttribute('target')).toBe('_blank');
    expect(a.getAttribute('rel')).toBe('noopener noreferrer');
  });
});
