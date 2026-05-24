// Task CRUD modal: open / save / delete / duplicate / confirm-delete.
// State lives in module-private vars (target column for create, edit id for
// patch) and is reset on every modal open.

import { API_BASE, apiCall, fmtDate } from './api.js';

let _taskTargetList = null;
let _taskProjectId = null;
let _taskEditId = null;

export async function openEditTask(btn, id) {
  // Read status and projectId from the live DOM (the closest column / kanban),
  // not from inlined Jinja values: drag&drop moves the card without reloading,
  // so the original onclick params are stale and would silently revert the
  // task to its render-time status on save (#11).
  const card = btn.closest('.kanban-task');
  const kanban = card?.closest('.kanban');
  const status = card?.closest('.kanban-tasks')?.dataset.status || 'todo';
  const projectId = kanban?.dataset.projectId || '';
  const projectDefaultWho = kanban?.dataset.defaultWho || '';
  _taskTargetList = null;
  _taskEditId = id;
  document.getElementById('task-modal-project-id').value = projectId;
  document.getElementById('task-modal-heading').textContent = 'Editer la tâche';
  document.getElementById('task-modal-title').value = '';
  document.getElementById('task-modal-desc').value = '';
  document.getElementById('task-modal-when').value = '';
  document.getElementById('task-modal-status').value = status;
  const delBtn = document.getElementById('task-modal-delete');
  if (delBtn) delBtn.style.display = id ? '' : 'none';
  const dupBtn = document.getElementById('task-modal-duplicate');
  if (dupBtn) dupBtn.style.display = id ? '' : 'none';
  document.getElementById('task-modal').style.display = 'flex';

  try {
    const r = await apiCall(`${API_BASE}/tasks/${id}`);
    const t = await r.json();
    document.getElementById('task-modal-title').value = t.title;
    document.getElementById('task-modal-desc').value = t.description || '';
    document.getElementById('task-modal-when').value = t.due_date ? fmtDate(t.due_date) : '';
    document.getElementById('task-modal-status').value = t.status || status;
    const whoSelect = document.getElementById('task-modal-who');
    const effectiveWho = t.who || projectDefaultWho;
    if (whoSelect && effectiveWho && [...whoSelect.options].some((o) => o.value === effectiveWho)) {
      whoSelect.value = effectiveWho;
    }
  } catch (e) {
    console.debug('openEditTask: API fetch failed', e);
  }
}

export function openTaskModal(taskList, projectId) {
  _taskTargetList = taskList;
  const kanban = taskList.closest('.kanban');
  _taskProjectId = projectId || kanban?.dataset?.projectId || '';
  _taskEditId = null;
  document.getElementById('task-modal-project-id').value = _taskProjectId;
  document.getElementById('task-modal-heading').textContent = 'Nouvelle tâche';
  document.getElementById('task-modal-title').value = '';
  document.getElementById('task-modal-desc').value = '';
  document.getElementById('task-modal-when').value = '';
  // who: project default if set, else logged-in user (already pre-selected
  // server-side via Jinja in the modal template).
  const projectDefaultWho = kanban?.dataset?.defaultWho || '';
  if (projectDefaultWho) {
    const whoSelect = document.getElementById('task-modal-who');
    if (whoSelect && [...whoSelect.options].some((o) => o.value === projectDefaultWho)) {
      whoSelect.value = projectDefaultWho;
    }
  }
  document.getElementById('task-modal-status').value = 'todo';
  const delBtn = document.getElementById('task-modal-delete');
  if (delBtn) delBtn.style.display = 'none';
  const dupBtn = document.getElementById('task-modal-duplicate');
  if (dupBtn) dupBtn.style.display = 'none';
  document.getElementById('task-modal').style.display = 'flex';
  document.getElementById('task-modal-title').focus();
}

export function saveTaskModal() {
  const title = document.getElementById('task-modal-title').value.trim();
  if (!title) return;
  const desc = document.getElementById('task-modal-desc').value.trim();
  const who = document.getElementById('task-modal-who').value;
  const when = document.getElementById('task-modal-when').value;
  const status = document.getElementById('task-modal-status').value;
  const projectId = document.getElementById('task-modal-project-id').value;
  const reloadFocused = (taskId) => {
    // Stash the saved task in sessionStorage (not the URL fragment, which is
    // already used to put a card into detail-mode). On the next load, the
    // keyboard-selection init reads this and marks the card as kb-selected
    // + scrolls it into view, without flipping it to detail-mode (#249).
    if (taskId) {
      try {
        sessionStorage.setItem('kb-focus-task', String(taskId));
      } catch (e) {
        // sessionStorage may throw in private mode; the keyboard-selection
        // restore is a UX nicety, not a hard requirement, so just log.
        console.debug('saveTaskModal: sessionStorage write failed', e);
      }
    }
    globalThis.location.reload();
  };
  if (_taskEditId) {
    apiCall(`${API_BASE}/tasks/${_taskEditId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description: desc, who, due_date: when || null, status }),
    })
      .then(() => reloadFocused(_taskEditId))
      .catch(() => {});
  } else {
    apiCall(`${API_BASE}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: projectId,
        title,
        description: desc,
        who,
        due_date: when || null,
        status,
      }),
    })
      .then((r) => r.json())
      .then((t) => reloadFocused(t?.id))
      .catch(() => {});
  }
  document.getElementById('task-modal').style.display = 'none';
}

export function deleteTask() {
  if (!_taskEditId) return;
  apiCall(`${API_BASE}/tasks/${_taskEditId}`, { method: 'DELETE' })
    .then(() => globalThis.location.reload())
    .catch(() => {});
  document.getElementById('task-modal').style.display = 'none';
}

export async function duplicateTask() {
  // POST a copy of the current modal fields, then re-bind the modal to
  // the new task id so the user can keep editing without closing.
  //
  // The duplicate is always created in ``todo``, regardless of the
  // original's status (#395). Rationale: a duplicated task represents
  // new work to schedule, not a re-instance of an in-progress / done
  // item — so it belongs back at the top of the funnel where the user
  // can decide what to do with it.
  if (!_taskEditId) return;
  const title = document.getElementById('task-modal-title').value.trim();
  if (!title) return;
  const desc = document.getElementById('task-modal-desc').value;
  const who = document.getElementById('task-modal-who').value;
  const when = document.getElementById('task-modal-when').value;
  const projectId = document.getElementById('task-modal-project-id').value;
  let r;
  try {
    r = await apiCall(`${API_BASE}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: projectId,
        title: `${title} - copy`,
        description: desc,
        who,
        due_date: when || null,
        status: 'todo',
      }),
    });
  } catch (e) {
    console.debug('duplicateTask: apiCall failed', e);
    return;
  }
  const created = await r.json();
  // Re-bind the modal to the new task. The user keeps editing in place.
  _taskEditId = created.id;
  document.getElementById('task-modal-title').value = created.title;
  // Reflect the forced ``todo`` status in the dropdown so the modal
  // matches the server-side state (the user could save right away
  // without ever opening the status select).
  document.getElementById('task-modal-status').value = 'todo';
  document.getElementById('task-modal-heading').textContent = 'Editer la tâche (copie)';
  document.getElementById('task-modal-title').focus();
  document.getElementById('task-modal-title').select();
}

export function confirmDelete(btn, callback) {
  // Hide parent edit modal first
  const parentModal = btn.closest('.project-add-modal');
  if (parentModal) parentModal.style.display = 'none';

  const modal = document.getElementById('confirm-modal');
  const msg = document.getElementById('confirm-modal-msg');
  msg.textContent = 'Êtes-vous sûr de vouloir supprimer cet élément ?';
  const okBtn = document.getElementById('confirm-modal-ok');
  okBtn.onclick = () => {
    modal.style.display = 'none';
    callback();
  };
  // Cancel reopens parent modal
  const cancelBtn = modal.querySelector('.btn-cancel');
  cancelBtn.onclick = () => {
    modal.style.display = 'none';
    if (parentModal) parentModal.style.display = 'flex';
  };
  // Backdrop click and Escape dismissal also reopen the parent: stash the
  // reference so the generic dismissal handler picks it up. Replaces the
  // previous modal.onclick handler that depended on stopPropagation from
  // the inner card (Sonar a11y, #83).
  modal._reopenParent = parentModal;
  modal.style.display = 'flex';
}
