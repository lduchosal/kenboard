// Keyboard shortcuts (#249). Selection model: at most one ``.kanban-task``
// carries ``data-kb-selected="true"``. Navigation, actions, and the help
// modal route through that selection. Disabled while a form field has
// focus (so typing "edit" in a title doesn't open the edit modal); modal-
// aware (only Enter / Cmd+Enter / Esc fire when a task modal is open).

import { clearTaskHash, toggleDetail } from './detail.js';
import { closeFullscreen, openFullscreen } from './fullscreen.js';
import { openEditTask, openTaskModal, saveTaskModal } from './tasks.js';

const KB_TASK_HASH_RE = /^#?ID-(\d+)$/;
let _kbGPrefix = false;
let _kbGTimer = null;

export function selectedCard() {
  return document.querySelector('.kanban-task[data-kb-selected="true"]');
}

function visibleCardsInColumn(col) {
  return [...col.querySelectorAll('.kanban-task:not(.task-hidden)')];
}

function allVisibleCards() {
  return [...document.querySelectorAll('.kanban-task:not(.task-hidden)')];
}

export function selectCard(card, { scroll = true } = {}) {
  document.querySelectorAll('.kanban-task[data-kb-selected]').forEach((c) => {
    if (c !== card) c.removeAttribute('data-kb-selected');
  });
  if (!card) return;
  card.dataset.kbSelected = 'true';
  if (scroll) card.scrollIntoView({ block: 'center', behavior: 'auto' });
}

function deselect() {
  document.querySelectorAll('.kanban-task[data-kb-selected]').forEach((c) => {
    c.removeAttribute('data-kb-selected');
  });
}

function selectFirst() {
  const first = allVisibleCards()[0];
  if (first) selectCard(first);
  return first;
}

// 2D navigation. Vertical = within the current column; horizontal = jump
// to the adjacent column at the same position (clamped to its length).
export function moveVertical(delta) {
  const current = selectedCard();
  if (!current) return selectFirst();
  const col = current.closest('.kanban-tasks');
  if (!col) return null;
  const siblings = visibleCardsInColumn(col);
  const idx = siblings.indexOf(current);
  if (idx === -1) return null;
  const next = siblings[Math.max(0, Math.min(siblings.length - 1, idx + delta))];
  if (next && next !== current) selectCard(next);
  return next;
}

export function moveHorizontal(delta) {
  const current = selectedCard();
  if (!current) return selectFirst();
  const kanban = current.closest('.kanban');
  if (!kanban) return null;
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

// -- Action handlers (operate on the currently selected card) ---------------

function actionOpen() {
  const card = selectedCard();
  if (card) toggleDetail(card, { detail: 1 });
}

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

function actionHome() {
  globalThis.location.href = '/';
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
  if (selectedCard()) {
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

export function bindKeyboard() {
  document.addEventListener('keydown', (e) => {
    // The generic Escape dismissal in modals.js already handles
    // .project-add-modal close. Don't double-process.
    if (e.defaultPrevented) return;

    // ---- Modal-scoped shortcuts ----
    if (taskModalIsOpen()) {
      if (handleTaskModal(e)) return;
      // While the task modal is open, swallow all other keyboard shortcuts
      // (navigation, actions, ?, g h) so they can't fire underneath it.
      return;
    }
    if (anyModalOpen()) return;

    // ---- Form-field gate ----
    // Don't intercept letters/arrows while the user is typing in a field.
    // (Modifier combos like Cmd+R / Cmd+F are still passed through anyway
    // because we only act on a small allowlist of keys.)
    if (targetIsFormField(e.target)) return;

    // ---- ``g`` two-step prefix ----
    if (_kbGPrefix) {
      _kbGPrefix = false;
      clearTimeout(_kbGTimer);
      _kbGTimer = null;
      if (e.key === 'h') {
        e.preventDefault();
        actionHome();
        return;
      }
      // Any other key cancels the prefix and falls through to normal routing.
    }

    // ---- Single-key actions ----
    // Navigation: arrows + Vim hjkl aliases. Clamped (no wrap) to match Linear.
    switch (e.key) {
      case 'ArrowUp':
      case 'k':
        e.preventDefault();
        moveVertical(-1);
        return;
      case 'ArrowDown':
      case 'j':
        e.preventDefault();
        moveVertical(1);
        return;
      case 'ArrowLeft':
      case 'h':
        e.preventDefault();
        moveHorizontal(-1);
        return;
      case 'ArrowRight':
      case 'l':
        e.preventDefault();
        moveHorizontal(1);
        return;
      case 'Enter':
        if (selectedCard()) {
          e.preventDefault();
          actionOpen();
          return;
        }
        break;
      case 'e':
        if (selectedCard()) {
          e.preventDefault();
          actionEdit();
          return;
        }
        break;
      case 'f':
        if (selectedCard()) {
          e.preventDefault();
          actionFullscreen();
          return;
        }
        break;
      case 'c':
        e.preventDefault();
        actionCreate();
        return;
      case '?':
        e.preventDefault();
        actionHelp();
        return;
      case 'Escape':
        // The generic dismissal handles open modals; here we cover the
        // detail-mode / selection cascade for the bare-board case.
        if (actionEscape()) e.preventDefault();
        return;
      case 'g':
        e.preventDefault();
        _kbGPrefix = true;
        _kbGTimer = setTimeout(() => {
          _kbGPrefix = false;
          _kbGTimer = null;
        }, 1500);
        return;
      default:
        break;
    }
  });

  // Click on a card → select it (in addition to the existing toggleDetail
  // behaviour). Keeps the keyboard-nav state in sync with mouse interaction.
  document.addEventListener('click', (e) => {
    const card = e.target.closest?.('.kanban-task');
    if (card) selectCard(card, { scroll: false });
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
  } catch (_e) {
    /* sessionStorage unavailable (private mode) — fall through */
  }
  if (!id) {
    const m = KB_TASK_HASH_RE.exec(globalThis.location.hash);
    if (m) id = m[1];
  }
  if (!id) return;
  const card = document.querySelector(`.kanban-task[data-task-id="${id}"]`);
  if (card) selectCard(card, { scroll: true });
}
