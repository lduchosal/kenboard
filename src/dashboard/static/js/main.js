// Entry point. Pulls in every module, wires deferred bindings, and exposes
// the small set of functions still referenced from inline ``onclick=""``
// attributes in the Jinja templates onto ``globalThis``.
//
// The bundle is loaded with ``defer``, so the DOM is ready by the time this
// IIFE runs — modules are free to query / addEventListener at module load
// time without their own DOMContentLoaded wrappers.

import { apiCall, showError } from './api.js';
import { addProjectInCatModal, deleteCat, editCat, saveCat, selectCatColor } from './categories.js';
import { bindHashSync, toggleDetail } from './detail.js';
import { bindDnd } from './dnd.js';
import { bindFullscreenBackdrop, closeFullscreen, openFullscreen } from './fullscreen.js';
import { bindKeyboard } from './keyboard.js';
import { renderMarkdown } from './markdown.js';
import { bindModalDismissal } from './modals.js';
import { copyOnboardLink, deleteProject, editProject, saveProject } from './projects.js';
import {
  confirmDelete,
  deleteTask,
  duplicateTask,
  openEditTask,
  openTaskModal,
  saveTaskModal,
} from './tasks.js';

// -- Sticky title observer --------------------------------------------------
// Highlights the floating header while a section title is "stuck" against it.
// The matching ``stuck`` class on the title swaps its background; ``no-border``
// on the header drops the border so the two surfaces visually merge.
function bindStickyTitles() {
  const header = document.querySelector('.header');
  if (!header) return;
  let stuckCount = 0;
  document.querySelectorAll('.section-title').forEach((el) => {
    const observer = new IntersectionObserver(
      ([e]) => {
        const isStuck = e.intersectionRatio < 1;
        const wasStuck = el.classList.contains('stuck');
        el.classList.toggle('stuck', isStuck);
        if (isStuck && !wasStuck) stuckCount++;
        if (!isStuck && wasStuck) stuckCount--;
        header.classList.toggle('no-border', stuckCount > 0);
      },
      { threshold: [1], rootMargin: '-42px 0px 0px 0px' },
    );
    const sentinel = document.createElement('div');
    sentinel.style.height = '1px';
    sentinel.style.marginBottom = '-1px';
    el.before(sentinel);
    observer.observe(sentinel);
  });
}

// -- Auto refresh -----------------------------------------------------------
// Reload the page once a minute so the board stays in sync with other clients.
// Skip the reload when a modal is open (would lose user input), when the tab
// is hidden, or when a drag is in progress.
const AUTO_REFRESH_MS = 60_000;
function shouldSkipRefresh() {
  if (document.hidden) return true;
  if (document.querySelector('.task-chosen, .task-drag')) return true;
  // #205: the fullscreen task detail view is a <dialog>; check .open
  // so reading a task doesn't get interrupted by the auto-refresh.
  if (document.getElementById('task-fullscreen')?.open) return true;
  const modals = document.querySelectorAll('.project-add-modal');
  for (const m of modals) {
    if (m.style.display && m.style.display !== 'none') return true;
  }
  return false;
}
function bindAutoRefresh() {
  setInterval(() => {
    if (shouldSkipRefresh()) return;
    globalThis.location.reload();
  }, AUTO_REFRESH_MS);
}

// -- Bootstrap --------------------------------------------------------------

bindStickyTitles();
bindModalDismissal();
bindFullscreenBackdrop();
bindHashSync();
bindDnd();
renderMarkdown();
bindKeyboard();
bindAutoRefresh();

// -- Inline onclick="" interop ----------------------------------------------
// Inline event handlers in Jinja templates expect these as window globals.
// Migrating templates to addEventListener is a separate task; until then we
// expose the public surface explicitly. ``Object.assign`` (vs. individual
// assignments) keeps the surface visible at a glance.
Object.assign(globalThis, {
  // shared utilities (consumed by inline scripts in admin_*.html and tests)
  apiCall,
  showError,
  shouldSkipRefresh,
  // categories
  editCat,
  selectCatColor,
  saveCat,
  deleteCat,
  addProjectInCatModal,
  // projects
  editProject,
  saveProject,
  deleteProject,
  copyOnboardLink,
  // tasks
  openEditTask,
  openTaskModal,
  saveTaskModal,
  deleteTask,
  duplicateTask,
  confirmDelete,
  toggleDetail,
  // fullscreen
  openFullscreen,
  closeFullscreen,
});
