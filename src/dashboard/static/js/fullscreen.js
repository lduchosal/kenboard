// Fullscreen task view (#155). Native ``<dialog>``, so Escape is wired by
// the browser; backdrop click is handled here. Filling the modal is async
// because the description is fetched on demand (#221).

import { API_BASE, apiCall, fmtDate } from './api.js';
import { openEditTask } from './tasks.js';

export async function openFullscreen(btn, id) {
  const card = btn.closest('.kanban-task');
  const avatarColor = card?.querySelector('.task-avatar')?.style.background || 'var(--dimmed)';
  // Show the modal immediately with minimal data, then fill from API (#221).
  populateFullscreen(id, '...', '', '', '', '', avatarColor, btn);
  document.getElementById('task-fullscreen').showModal();

  try {
    const r = await apiCall(`${API_BASE}/tasks/${id}`);
    const t = await r.json();
    populateFullscreen(
      t.id,
      t.title,
      t.description || '',
      t.who || '',
      t.due_date ? fmtDate(t.due_date) : '',
      t.attachement || '',
      avatarColor,
      btn,
    );
  } catch (e) {
    console.debug('openFullscreen: API fetch failed', e);
  }
}

function populateFullscreen(id, title, desc, who, when, attachement, avatarColor, btn) {
  document.getElementById('fs-id').textContent = `#${id}`;
  document.getElementById('fs-title').textContent = title;
  document.getElementById('fs-who').textContent = who || '—';
  document.getElementById('fs-when').textContent = when || '';

  const avatar = document.getElementById('fs-avatar');
  avatar.textContent = (who || '?')[0].toUpperCase();
  avatar.style.background = avatarColor || 'var(--dimmed)';

  const card = btn.closest('.kanban-task');
  const status = card?.closest('.kanban-tasks')?.dataset.status || '';
  document.getElementById('fs-status').textContent = status;

  const descEl = document.getElementById('fs-desc');
  if (desc && typeof marked !== 'undefined') {
    const raw = marked.parse(desc);
    descEl.innerHTML = typeof DOMPurify === 'undefined' ? raw : DOMPurify.sanitize(raw);
  } else {
    descEl.textContent = desc || '(pas de description)';
  }

  // #575: paintbrush SVG annotation layer (sanitised) — mirrors the edit-modal
  // behaviour in tasks.js, so opening the fullscreen view also shows the
  // annotated page snapshot when the task carries one.
  const attEl = document.getElementById('fs-attachement');
  if (attEl) {
    if (attachement && typeof DOMPurify !== 'undefined') {
      attEl.innerHTML = DOMPurify.sanitize(attachement, {
        USE_PROFILES: { svg: true, svgFilters: true },
      });
      attEl.style.display = '';
    } else {
      attEl.innerHTML = '';
      attEl.style.display = 'none';
    }
  }

  document.getElementById('fs-edit-btn').onclick = () => {
    closeFullscreen();
    openEditTask(btn, id);
  };
}

export function closeFullscreen() {
  document.getElementById('task-fullscreen').close();
}

// Native <dialog> handles Escape automatically. Backdrop click needs manual
// handling (click on the dialog element itself, not its children).
export function bindFullscreenBackdrop() {
  document.getElementById('task-fullscreen')?.addEventListener('click', function (e) {
    if (e.target === this) this.close();
  });
}
