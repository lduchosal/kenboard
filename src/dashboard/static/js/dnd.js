// Task card drag-and-drop. On mobile (<=480px) a drag handle is used so
// vertical scroll is not blocked by Sortable (#161, same pattern as the
// category grid's ``.cat-drag-handle``).

import { API_BASE, apiCall } from './api.js';

const _mobileTaskMq = globalThis.matchMedia('(max-width: 480px)');

export function initTaskSortables() {
  document.querySelectorAll('.kanban-col').forEach((col) => {
    const tc = col.querySelector('.kanban-tasks');
    if (!tc) return;
    // Destroy previous instance if any (re-init on breakpoint change)
    if (tc._sortable) tc._sortable.destroy();
    const opts = {
      group: 'kanban',
      animation: 150,
      draggable: '.kanban-task',
      ghostClass: 'task-ghost',
      chosenClass: 'task-chosen',
      dragClass: 'task-drag',
      onEnd: (evt) => {
        const taskId = evt.item.dataset.taskId;
        const newStatus = evt.to.dataset.status;
        const newProjectId = evt.to.closest('.kanban')?.dataset?.projectId;
        if (!taskId) return;
        const body = { status: newStatus, position: evt.newIndex };
        if (newProjectId) body.project_id = newProjectId;
        apiCall(`${API_BASE}/tasks/${taskId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }).catch(() => {});
      },
    };
    if (_mobileTaskMq.matches) {
      opts.handle = '.task-drag-handle';
    }
    tc._sortable = new Sortable(tc, opts);
  });
}

export function bindDnd() {
  initTaskSortables();
  _mobileTaskMq.addEventListener('change', initTaskSortables);
}
