// Generic modal dismissal: backdrop click + Escape, with the data-no-dismiss
// opt-out used by the API-key reveal modal.

import { afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { bindModalDismissal, dismissModal } from './modals.js';

// bindModalDismissal adds a document-level keydown listener; we can't remove
// it from JS, so call it exactly once per file to avoid duplicate firings
// across tests in this file.
beforeAll(() => {
  bindModalDismissal();
});

beforeEach(() => {
  document.body.innerHTML = '';
});

afterEach(() => {
  document.body.innerHTML = '';
});

function makeModal(id, { noDismiss = false } = {}) {
  const m = document.createElement('div');
  m.className = 'project-add-modal';
  m.id = id;
  m.style.display = 'flex';
  if (noDismiss) m.dataset.noDismiss = '1';
  document.body.appendChild(m);
  return m;
}

describe('dismissModal', () => {
  it('hides the modal', () => {
    const m = makeModal('m1');
    dismissModal(m);
    expect(m.style.display).toBe('none');
  });

  it('re-opens a stashed parent modal (used by confirmDelete)', () => {
    const parent = makeModal('parent');
    parent.style.display = 'none';
    const child = makeModal('child');
    child._reopenParent = parent;
    dismissModal(child);
    expect(child.style.display).toBe('none');
    expect(parent.style.display).toBe('flex');
    expect(child._reopenParent).toBeNull();
  });
});

describe('bindModalDismissal', () => {
  it('closes the topmost open modal on Escape', () => {
    const m1 = makeModal('m1');
    const m2 = makeModal('m2');
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(m1.style.display).toBe('flex');
    expect(m2.style.display).toBe('none');
  });

  it('skips data-no-dismiss modals on Escape', () => {
    const m = makeModal('m1', { noDismiss: true });
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(m.style.display).toBe('flex');
  });
});

// The backdrop-click listener is attached to each modal at the time
// bindModalDismissal runs, so we need to call it AFTER constructing the
// modals (separate suite to keep it apart from the Escape suite which
// uses the global beforeAll).
describe('bindModalDismissal: click-outside', () => {
  it('closes a modal when the backdrop is clicked', () => {
    const m = makeModal('m1');
    bindModalDismissal();
    m.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(m.style.display).toBe('none');
  });

  it('does not close the modal when an inner element is clicked', () => {
    const m = makeModal('m2');
    const inner = document.createElement('div');
    m.appendChild(inner);
    bindModalDismissal();
    inner.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(m.style.display).toBe('flex');
  });

  it('skips data-no-dismiss modals on backdrop click', () => {
    const m = makeModal('m3', { noDismiss: true });
    bindModalDismissal();
    m.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(m.style.display).toBe('flex');
  });
});
