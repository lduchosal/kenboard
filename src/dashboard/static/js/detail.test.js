// Hash sync + detail-mode toggling. The lazy-load fetch path is exercised
// with a mocked ``globalThis.fetch``.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  applyTaskHash,
  clearTaskHash,
  lazyLoadDesc,
  setTaskHash,
  taskHashId,
  toggleDetail,
} from './detail.js';

function setHash(h) {
  globalThis.history.replaceState(null, '', h ? `#${h}` : globalThis.location.pathname);
}

beforeEach(() => {
  document.body.innerHTML = '';
  setHash('');
  globalThis.marked = { parse: (s) => s, setOptions: () => {} };
  globalThis.DOMPurify = { sanitize: (s) => s };
  Element.prototype.scrollIntoView = () => {};
});

afterEach(() => {
  vi.restoreAllMocks();
  globalThis.marked = undefined;
  globalThis.DOMPurify = undefined;
});

describe('hash helpers', () => {
  it('parses #ID-<n> via taskHashId', () => {
    setHash('ID-42');
    expect(taskHashId()).toBe('42');
  });

  it('returns null when the hash does not match', () => {
    setHash('something-else');
    expect(taskHashId()).toBeNull();
  });

  it('setTaskHash writes ID-<n> via replaceState', () => {
    setTaskHash(7);
    expect(globalThis.location.hash).toBe('#ID-7');
  });

  it('clearTaskHash strips the fragment', () => {
    setHash('ID-7');
    clearTaskHash();
    expect(globalThis.location.hash).toBe('');
  });
});

describe('toggleDetail', () => {
  it('flips a card into detail-mode and writes the hash', async () => {
    document.body.innerHTML = '<div class="kanban-task" data-task-id="5"></div>';
    const card = document.querySelector('.kanban-task');
    await toggleDetail(card, { detail: 1 });
    expect(card.classList.contains('detail-mode')).toBe(true);
    expect(taskHashId()).toBe('5');
  });

  it('toggles detail-mode back off and clears the hash', async () => {
    document.body.innerHTML = '<div class="kanban-task detail-mode" data-task-id="9"></div>';
    setHash('ID-9');
    const card = document.querySelector('.kanban-task');
    await toggleDetail(card, { detail: 1 });
    expect(card.classList.contains('detail-mode')).toBe(false);
    expect(taskHashId()).toBeNull();
  });

  it('bails when called for the second click of a double-click', async () => {
    document.body.innerHTML = '<div class="kanban-task" data-task-id="1"></div>';
    const card = document.querySelector('.kanban-task');
    await toggleDetail(card, { detail: 2 });
    expect(card.classList.contains('detail-mode')).toBe(false);
  });
});

describe('lazyLoadDesc', () => {
  it('rejects a non-numeric task id without fetching (taint guard, #253)', async () => {
    const fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy;
    const el = document.createElement('div');
    await lazyLoadDesc(el, '../../etc/passwd');
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('fetches and renders the description into .task-desc', async () => {
    document.body.innerHTML = '<div class="kanban-task"><div class="task-body"></div></div>';
    const el = document.querySelector('.kanban-task');
    globalThis.fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ description: 'hello' }), { status: 200 }));
    await lazyLoadDesc(el, '42');
    const desc = el.querySelector('.task-desc');
    expect(desc).not.toBeNull();
    expect(desc.textContent).toBe('hello');
    expect(el.dataset.descLoaded).toBe('1');
  });

  it('skips re-fetching when descLoaded is already set', async () => {
    const el = document.createElement('div');
    el.dataset.descLoaded = '1';
    const fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy;
    await lazyLoadDesc(el, '42');
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

describe('applyTaskHash', () => {
  it('puts the matching card into detail-mode on load', async () => {
    document.body.innerHTML = '<div class="kanban-task" data-task-id="3"></div>';
    setHash('ID-3');
    globalThis.fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ description: '' }), { status: 200 }));
    await applyTaskHash();
    const card = document.querySelector('.kanban-task');
    expect(card.classList.contains('detail-mode')).toBe(true);
  });

  it('is a no-op when the hash does not match a card', async () => {
    document.body.innerHTML = '<div class="kanban-task" data-task-id="3"></div>';
    setHash('ID-999');
    await applyTaskHash();
    const card = document.querySelector('.kanban-task');
    expect(card.classList.contains('detail-mode')).toBe(false);
  });
});
