// Detail mode (in-card expansion) and URL <-> task hash sync (#109).
// The URL fragment doubles as task-detail state: ``#ID-<task-id>`` puts the
// matching card into detail mode. Cards expose the id via ``data-task-id``
// (not a real DOM ``id``) so the browser does not auto-scroll on hash
// changes — we control scrolling explicitly.

import { API_BASE } from './api.js';
import { renderMarkdown } from './markdown.js';

const TASK_HASH_RE = /^#?ID-(\d+)$/;

export function taskHashId() {
  const m = TASK_HASH_RE.exec(globalThis.location.hash);
  return m ? m[1] : null;
}

export function setTaskHash(taskId) {
  // replaceState avoids polluting the history with one entry per click.
  // hashchange does not fire on replaceState, but toggleDetail already
  // updated the DOM directly, so no extra work is needed here.
  if (taskHashId() === String(taskId)) return;
  const url = new URL(globalThis.location.href);
  url.hash = `ID-${taskId}`;
  globalThis.history.replaceState(null, '', url);
}

export function clearTaskHash() {
  if (taskHashId() === null) return;
  const url = new URL(globalThis.location.href);
  globalThis.history.replaceState(null, '', url.pathname + url.search);
}

export async function lazyLoadDesc(el, taskId) {
  if (!taskId || el.dataset.descLoaded) return;
  // Validate taskId is a positive integer before interpolating into the URL
  // so a tampered ``data-task-id`` can't compose an unexpected request path
  // (Sonar javascript:S5852: tainted data in client-side request). Convert
  // to a number explicitly — Sonar's taint tracker recognises numeric
  // coercion as sanitisation; a regex+template literal still flags.
  const id = Number(taskId);
  if (!Number.isInteger(id) || id <= 0) return;
  try {
    const r = await fetch(`${API_BASE}/tasks/${id}`);
    if (!r.ok) return;
    const t = await r.json();
    if (t.description) {
      let descEl = el.querySelector('.task-desc');
      if (!descEl) {
        descEl = document.createElement('div');
        descEl.className = 'task-desc';
        el.querySelector('.task-body').appendChild(descEl);
      }
      descEl.textContent = t.description;
      renderMarkdown(el);
    }
    el.dataset.descLoaded = '1';
  } catch (e) {
    console.debug('lazyLoadDesc: fetch failed', e);
  }
}

export async function toggleDetail(el, event) {
  // The 2nd click of a double-click reaches us with ``event.detail === 2``
  // (browser-set click count). Bail so the matching ``dblclick`` handler can
  // open the edit modal without us toggling the detail view back off
  // underneath it (#111).
  if (event && event.detail > 1) return;
  const taskId = el.dataset.taskId;
  const wasDetail = el.classList.contains('detail-mode');
  document
    .querySelectorAll('.kanban-task.detail-mode')
    .forEach((t) => t.classList.remove('detail-mode'));
  if (wasDetail) {
    if (taskHashId() === taskId) clearTaskHash();
    return;
  }
  el.classList.add('detail-mode');
  if (taskId) setTaskHash(taskId);
  await lazyLoadDesc(el, taskId);
}

export async function applyTaskHash() {
  const id = taskHashId();
  document.querySelectorAll('.kanban-task.detail-mode').forEach((t) => {
    if (t.dataset.taskId !== id) t.classList.remove('detail-mode');
  });
  if (!id) return;
  const card = document.querySelector(`.kanban-task[data-task-id="${id}"]`);
  if (!card) return; // Stale link: task no longer on this page.
  card.classList.add('detail-mode');
  card.scrollIntoView({ block: 'center', behavior: 'auto' });
  await lazyLoadDesc(card, id);
}

// React to back/forward and direct edits of the URL fragment. We don't fire
// this from ``toggleDetail`` (that path uses replaceState) so the listener
// only handles externally-driven changes.
export function bindHashSync() {
  globalThis.addEventListener('hashchange', applyTaskHash);
  // Initial pass: restore detail mode from the URL on load (incl. after the
  // 60s auto-refresh, which preserves the fragment).
  applyTaskHash();
}
