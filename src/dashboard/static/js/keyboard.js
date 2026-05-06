// Keyboard shortcuts (#249, #253). Selection model: at most one element
// carries ``data-kb-selected="true"``. Navigation, actions, and the help
// modal route through that selection. Disabled while a form field has focus
// (so typing "edit" in a title doesn't open the edit modal); modal-aware
// (only Enter / Cmd+Enter / Esc fire when a task modal is open).
//
// Navigable items: any ``.kanban-task`` automatically, plus any element
// explicitly opted-in via ``data-kb-nav`` (used on the home page tiles to
// extend nav beyond the kanban context — #253).

import { clearTaskHash, toggleDetail } from './detail.js';
import { closeFullscreen, openFullscreen } from './fullscreen.js';
import { openEditTask, openTaskModal, saveTaskModal } from './tasks.js';

const KB_TASK_HASH_RE = /^#?ID-(\d+)$/;
const NAV_SELECTOR = '.kanban-task:not(.task-hidden), [data-kb-nav]:not(.task-hidden)';
let _kbGPrefix = false;
let _kbGTimer = null;

export function selected() {
  return document.querySelector('[data-kb-selected="true"]');
}

// Backwards-compat alias: callers (and tests) that only care about kanban
// cards can still use ``selectedCard()`` to get a narrowed result.
export function selectedCard() {
  const el = selected();
  return el?.classList.contains('kanban-task') ? el : null;
}

function visibleCardsInColumn(col) {
  return [...col.querySelectorAll('.kanban-task:not(.task-hidden)')];
}

function allNavItems() {
  return [...document.querySelectorAll(NAV_SELECTOR)];
}

export function selectCard(card, { scroll = true } = {}) {
  for (const c of document.querySelectorAll('[data-kb-selected]')) {
    if (c !== card) delete c.dataset.kbSelected;
  }
  if (!card) return;
  card.dataset.kbSelected = 'true';
  if (scroll) card.scrollIntoView({ block: 'center', behavior: 'auto' });
}

function deselect() {
  for (const c of document.querySelectorAll('[data-kb-selected]')) {
    delete c.dataset.kbSelected;
  }
}

function selectFirst() {
  const first = allNavItems()[0];
  if (first) selectCard(first);
  return first;
}

// Sibling kanban lookup: ``+1`` next ``.kanban`` in document order,
// ``-1`` previous. Used by moveVertical to spill over from the bottom
// of one project board to the top of the next (#253).
function adjacentKanban(currentKanban, delta) {
  const all = [...document.querySelectorAll('.kanban')];
  const idx = all.indexOf(currentKanban);
  if (idx === -1) return null;
  return all[idx + delta] || null;
}

// Flat document-order nav across every navigable item. Used outside the
// kanban context (e.g. home page tiles) where the 2D column model doesn't
// apply (#253).
function moveFlat(delta) {
  const current = selected();
  if (!current) return selectFirst();
  const items = allNavItems();
  const idx = items.indexOf(current);
  if (idx === -1) return selectFirst();
  const target = items[Math.max(0, Math.min(items.length - 1, idx + delta))];
  if (target && target !== current) selectCard(target);
  return target;
}

// Vertical nav (#259). Within a column: move ±1. At the bottom of a column:
// jump to the FIRST card of the next column in the same kanban; at the
// bottom of the LAST column, spill into the FIRST card of the next ``.kanban``
// (next project board). Symmetric going up: top of a column → last card of
// the previous column; top of the FIRST column → last card of the previous
// kanban. Outside any kanban (home-page tiles): flat document-order nav.
export function moveVertical(delta) {
  const current = selected();
  if (!current) return selectFirst();
  const col = current.closest('.kanban-tasks');
  if (!col) return moveFlat(delta);
  const siblings = visibleCardsInColumn(col);
  const idx = siblings.indexOf(current);
  if (idx === -1) return null;
  const targetIdx = idx + delta;
  if (targetIdx >= 0 && targetIdx < siblings.length) {
    const target = siblings[targetIdx];
    selectCard(target);
    return target;
  }
  // At the edge of the column — first try the next/previous column of the
  // same kanban, then fall through to the next/previous kanban.
  const kanban = current.closest('.kanban');
  if (!kanban) return current;
  const target = nextCardAcrossColumns(kanban, col, delta) || nextCardAcrossKanbans(kanban, delta);
  if (target) {
    selectCard(target);
    return target;
  }
  return current; // genuinely clamped (no further card in this direction)
}

// Walk through the kanban's other columns in the given direction looking for
// the first column with at least one visible card. Returns its first card
// (going down) or last card (going up), or null if no further column has
// cards.
function nextCardAcrossColumns(kanban, currentCol, delta) {
  const cols = [...kanban.querySelectorAll('.kanban-tasks')];
  const colIdx = cols.indexOf(currentCol);
  if (colIdx === -1) return null;
  for (let i = colIdx + delta; i >= 0 && i < cols.length; i += delta) {
    const cards = visibleCardsInColumn(cols[i]);
    if (cards.length === 0) continue;
    return delta > 0 ? cards[0] : cards.at(-1);
  }
  return null;
}

// Walk to the next/previous ``.kanban`` and return its first card (going
// down) or last card (going up). Returns null if the adjacent kanban has
// no visible cards (or doesn't exist).
function nextCardAcrossKanbans(kanban, delta) {
  const adjacent = adjacentKanban(kanban, delta);
  if (!adjacent) return null;
  const cards = [...adjacent.querySelectorAll('.kanban-task:not(.task-hidden)')];
  if (cards.length === 0) return null;
  return delta > 0 ? cards[0] : cards.at(-1);
}

// Horizontal nav. Inside a kanban: move between columns at the same
// position. Outside a kanban: flat document-order nav (mirrors
// ``moveVertical`` so home-page tiles remain reachable with ←/→ too).
export function moveHorizontal(delta) {
  const current = selected();
  if (!current) return selectFirst();
  const kanban = current.closest('.kanban');
  if (!kanban) return moveFlat(delta);
  const cols = [...kanban.querySelectorAll('.kanban-tasks')];
  const col = current.closest('.kanban-tasks');
  const colIdx = cols.indexOf(col);
  if (colIdx === -1) return null;
  const targetColIdx = Math.max(0, Math.min(cols.length - 1, colIdx + delta));
  if (targetColIdx === colIdx) return current;
  const targetCol = cols[targetColIdx];
  const targetCards = visibleCardsInColumn(targetCol);
  if (targetCards.length === 0) {
    // Skip empty column: keep stepping in the same direction until we find a
    // column with at least one visible card, or run out of columns.
    for (let i = targetColIdx + delta; i >= 0 && i < cols.length; i += delta) {
      const cs = visibleCardsInColumn(cols[i]);
      if (cs.length) {
        selectCard(cs[0]);
        return cs[0];
      }
    }
    return current;
  }
  const positionInOriginalCol = visibleCardsInColumn(col).indexOf(current);
  const target =
    targetCards[Math.min(positionInOriginalCol, targetCards.length - 1)] || targetCards[0];
  selectCard(target);
  return target;
}

// -- Action handlers (operate on the currently selected item) --------------

// Enter on a selected item. ``.kanban-task`` → toggle detail mode. Any
// element that links somewhere (an ``<a>`` with href, or anything with
// ``data-kb-href``) → follow the link. Other items → no-op.
function actionOpen() {
  const item = selected();
  if (!item) return;
  if (item.classList.contains('kanban-task')) {
    toggleDetail(item, { detail: 1 });
    return;
  }
  if (item.tagName === 'A' && item.href) {
    item.click();
    return;
  }
  const href = item.dataset?.kbHref;
  if (href) globalThis.location.href = href;
}

// Edit / fullscreen / create only apply to ``.kanban-task``; selected
// non-card items (home tiles) are silently ignored for these actions.
function actionEdit() {
  const card = selectedCard();
  if (card) openEditTask(card, card.dataset.taskId);
}

function actionFullscreen() {
  const card = selectedCard();
  if (card) openFullscreen(card, card.dataset.taskId);
}

function actionCreate() {
  const card = selectedCard();
  const taskList = card?.closest('.kanban-tasks') || document.querySelector('.kanban-tasks');
  if (!taskList) return;
  const projectId = taskList.closest('.kanban')?.dataset?.projectId || '';
  openTaskModal(taskList, projectId);
}

function actionHelp() {
  const m = document.getElementById('kb-help-modal');
  if (m) m.style.display = 'flex';
}

// ``g``-prefix navigation targets (#253). Browser shortcuts (cmd+b, cmd+u,
// cmd+a, cmd+q) never reach JS, so we use the existing g-prefix instead.
function navigateTo(url) {
  globalThis.location.href = url;
}

function logout() {
  // Logout is a POST (CSRF-protected form in header.html). Find the form
  // and submit it programmatically rather than navigating.
  const form = document.querySelector('form.logout-form');
  if (form) form.submit();
}

// Esc cascade: close fullscreen → close any task-modal → exit detail-mode →
// deselect. The generic ``project-add-modal`` Escape dismissal already runs
// from the modals.js handler; we layer on top by only taking action when
// no modal handled the event.
function actionEscape() {
  const fs = document.getElementById('task-fullscreen');
  if (fs?.open) {
    closeFullscreen();
    return true;
  }
  const detail = document.querySelector('.kanban-task.detail-mode');
  if (detail) {
    detail.classList.remove('detail-mode');
    clearTaskHash();
    return true;
  }
  if (selected()) {
    deselect();
    return true;
  }
  return false;
}

// -- Routing -----------------------------------------------------------------

function anyModalOpen() {
  if (document.getElementById('task-fullscreen')?.open) return true;
  for (const m of document.querySelectorAll('.project-add-modal')) {
    if (m.style.display && m.style.display !== 'none') return true;
  }
  return false;
}

function targetIsFormField(t) {
  if (!t) return false;
  if (t.matches?.('input, textarea, select, [contenteditable="true"]')) return true;
  return false;
}

function taskModalIsOpen() {
  const m = document.getElementById('task-modal');
  return !!(m?.style.display && m.style.display !== 'none');
}

// Inside the task modal: Enter saves from short text fields; Cmd/Ctrl+Enter
// saves from the description textarea (so plain Enter keeps inserting a
// newline). Esc is handled by the generic dismissal in modals.js.
function handleTaskModal(e) {
  if (e.key !== 'Enter') return false;
  const t = e.target;
  if (!t) return false;
  const isTextarea = t.tagName === 'TEXTAREA';
  const wantsModifier = isTextarea;
  const hasModifier = e.metaKey || e.ctrlKey;
  if (wantsModifier && !hasModifier) return false;
  if (!wantsModifier && hasModifier) return false;
  // Don't fire on keydown auto-repeat or IME composition.
  if (e.isComposing) return false;
  e.preventDefault();
  saveTaskModal();
  return true;
}

// ``g``-prefix dispatch (#253). Returns true if the prefix consumed the key
// (whether it matched a known target or fell through after timing out).
const G_PREFIX_TARGETS = {
  h: () => navigateTo('/'),
  b: () => navigateTo('/admin/board'),
  u: () => navigateTo('/admin/users'),
  k: () => navigateTo('/admin/keys'),
  l: logout,
};

function consumeGPrefix(e) {
  if (!_kbGPrefix) return false;
  _kbGPrefix = false;
  clearTimeout(_kbGTimer);
  _kbGTimer = null;
  const action = G_PREFIX_TARGETS[e.key];
  if (!action) return false; // Cancel prefix, fall through to single-key.
  e.preventDefault();
  action();
  return true;
}

// Navigation keys (arrows + Vim hjkl). Returns true when handled.
const NAV_HANDLERS = {
  ArrowUp: () => moveVertical(-1),
  k: () => moveVertical(-1),
  ArrowDown: () => moveVertical(1),
  j: () => moveVertical(1),
  ArrowLeft: () => moveHorizontal(-1),
  h: () => moveHorizontal(-1),
  ArrowRight: () => moveHorizontal(1),
  l: () => moveHorizontal(1),
};

function handleNav(e) {
  const handler = NAV_HANDLERS[e.key];
  if (!handler) return false;
  e.preventDefault();
  handler();
  return true;
}

// Selection-bound actions (Enter / e / f). Returns true when handled.
function handleSelectionAction(e) {
  if (e.key === 'Enter' && selected()) {
    // Double-fire guard (#253): a focused ``.kanban-task`` already handles
    // Enter via its own ``onkeydown`` (which calls .click() → toggleDetail).
    // If we ALSO call actionOpen, the two fire in sequence and toggle the
    // detail mode on then off. Bail when the target is the focused card.
    if (e.target?.classList?.contains('kanban-task')) return true;
    e.preventDefault();
    actionOpen();
    return true;
  }
  if (e.key === 'e' && selectedCard()) {
    e.preventDefault();
    actionEdit();
    return true;
  }
  if (e.key === 'f' && selectedCard()) {
    e.preventDefault();
    actionFullscreen();
    return true;
  }
  return false;
}

// Always-on shortcuts (c / ? / Esc / g-prefix start).
function handleGlobalKey(e) {
  switch (e.key) {
    case 'c':
      e.preventDefault();
      actionCreate();
      return true;
    case '?':
      e.preventDefault();
      actionHelp();
      return true;
    case 'Escape':
      if (actionEscape()) e.preventDefault();
      return true;
    case 'g':
      e.preventDefault();
      _kbGPrefix = true;
      _kbGTimer = setTimeout(() => {
        _kbGPrefix = false;
        _kbGTimer = null;
      }, 1500);
      return true;
    default:
      return false;
  }
}

function routeKey(e) {
  if (e.defaultPrevented) return;
  if (taskModalIsOpen()) {
    handleTaskModal(e);
    // Always swallow other shortcuts while the task modal is open.
    return;
  }
  if (anyModalOpen()) return;
  if (targetIsFormField(e.target)) return;
  if (consumeGPrefix(e)) return;
  if (handleNav(e)) return;
  if (handleSelectionAction(e)) return;
  handleGlobalKey(e);
}

export function bindKeyboard() {
  document.addEventListener('keydown', routeKey);

  // Click on any navigable item → select it (in addition to the item's own
  // click behaviour). Keeps the keyboard-nav state in sync with mouse
  // interaction across both kanban tasks and home-page tiles (#253).
  document.addEventListener('click', (e) => {
    const item = e.target.closest?.('.kanban-task, [data-kb-nav]');
    if (item) selectCard(item, { scroll: false });
  });

  // On load, restore keyboard selection from two sources, in priority order:
  //   1. ``sessionStorage["kb-focus-task"]`` — set by saveTaskModal so the
  //      just-saved card stays selected and scrolls into view across the
  //      reload (without flipping to detail-mode, unlike the URL hash).
  //   2. The ``#ID-<id>`` URL fragment — already drives detail-mode via
  //      detail.applyTaskHash; reuse it as the keyboard-selection seed.
  let id = null;
  try {
    id = sessionStorage.getItem('kb-focus-task');
    if (id) sessionStorage.removeItem('kb-focus-task');
  } catch (e) {
    // sessionStorage throws in private/incognito on some browsers — log and
    // fall through to the hash fallback so init still happens.
    console.debug('keyboard: sessionStorage unavailable', e);
  }
  if (!id) {
    const m = KB_TASK_HASH_RE.exec(globalThis.location.hash);
    if (m) id = m[1];
  }
  if (!id) return;
  const card = document.querySelector(`.kanban-task[data-task-id="${id}"]`);
  if (card) selectCard(card, { scroll: true });
}
