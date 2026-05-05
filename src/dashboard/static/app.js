'use strict';

const API_BASE = '/api/v1';

// -- Error popup -------------------------------------------------------------
// Centralized API error reporting. Every fetch to the backend should go
// through `apiCall` so failures (network, 401, 403, 4xx, 5xx) surface as a
// visible modal instead of being swallowed into console.warn or `alert()`.
function showError(title, body) {
  const modal = document.getElementById('error-modal');
  if (!modal) {
    // Fallback for pages that didn't include the partial (shouldn't happen,
    // it's in base.html).
    globalThis.alert(`${title}\n\n${body}`);
    return;
  }
  document.getElementById('error-modal-title').textContent = title;
  document.getElementById('error-modal-body').textContent = body || '';
  modal.style.display = 'flex';
}

async function apiCall(url, opts = {}) {
  let r;
  try {
    r = await fetch(url, opts);
  } catch (err) {
    showError('Erreur réseau', err?.message || String(err));
    throw err;
  }
  if (!r.ok) {
    const text = await r.text();
    let detail = text;
    try {
      const parsed = JSON.parse(text);
      detail = parsed.error || parsed.detail || text;
    } catch (parseErr) {
      // Body wasn't JSON; keep the raw text. Logged at debug so it doesn't
      // pollute the console but is available when troubleshooting.
      console.debug('apiCall: response body is not JSON', parseErr);
    }
    let title;
    if (r.status === 401) {
      title = 'Non authentifié';
      detail = detail || 'Cette opération nécessite une clé API valide. Voir /admin/keys.';
    } else if (r.status === 403) {
      title = 'Permission refusée';
    } else if (r.status === 404) {
      title = 'Introuvable';
    } else if (r.status === 409) {
      title = 'Conflit';
    } else if (r.status === 422) {
      title = 'Validation';
    } else if (r.status >= 500) {
      title = `Erreur serveur (${r.status})`;
    } else {
      title = `Erreur ${r.status}`;
    }
    showError(title, detail);
    throw new Error(`HTTP ${r.status}: ${detail}`);
  }
  return r;
}

// -- Date formatting ---------------------------------------------------------
// Format ISO date (YYYY-MM-DD) to dd.mm for display consistency with Jinja.
function _fmtDate(iso) {
  if (!iso) return '';
  const parts = iso.split('-');
  if (parts.length < 3) return iso;
  return parts[2] + '.' + parts[1];
}

// -- Sticky title observer ---------------------------------------------------

const header = document.querySelector('.header');
let stuckCount = 0;
document.querySelectorAll('.section-title').forEach(el => {
  const observer = new IntersectionObserver(
    ([e]) => {
      const isStuck = e.intersectionRatio < 1;
      const wasStuck = el.classList.contains('stuck');
      el.classList.toggle('stuck', isStuck);
      if (isStuck && !wasStuck) stuckCount++;
      if (!isStuck && wasStuck) stuckCount--;
      header.classList.toggle('no-border', stuckCount > 0);
    },
    { threshold: [1], rootMargin: '-42px 0px 0px 0px' }
  );
  const sentinel = document.createElement('div');
  sentinel.style.height = '1px';
  sentinel.style.marginBottom = '-1px';
  el.before(sentinel);
  observer.observe(sentinel);
});

// -- Category CRUD -----------------------------------------------------------

function editCat(id, name, color) {
  const modal = document.getElementById('cat-modal');
  if (!modal) return;
  document.getElementById('cat-modal-id').value = id;
  document.getElementById('cat-modal-name').value = name;
  document.querySelector('#cat-modal h3').textContent = id ? 'Editer la cat\u00e9gorie' : 'Nouvelle cat\u00e9gorie';
  const delBtn = document.getElementById('cat-modal-delete');
  if (delBtn) delBtn.style.display = id ? '' : 'none';
  // Mark the matching dot as selected. For a brand-new category (no color
  // passed) we fall back to the first dot so the form always has a valid
  // pick — the server validator (#56) refuses empty colors.
  const colors = document.getElementById('cat-modal-colors');
  if (colors) {
    const dots = colors.querySelectorAll('.color-dot');
    let any = false;
    dots.forEach(d => {
      const match = d.dataset.color === color;
      d.classList.toggle('selected', match);
      if (match) any = true;
    });
    if (!any && dots.length > 0) dots[0].classList.add('selected');
  }
  const list = document.getElementById('cat-modal-projects');
  if (list) {
    list.innerHTML = '';
    const projs = (typeof CAT_PROJECTS !== 'undefined' && id) ? (CAT_PROJECTS[id] || []) : [];
    projs.forEach(p => {
      const el = document.createElement('div');
      el.className = 'cat-modal-project';
      el.dataset.projectId = p.id;
      const canDelete = p.tasks === 0;
      // Build the row with empty placeholders, then write user-controlled
      // strings via textContent to neutralise stored XSS via project name.
      el.innerHTML = `<span class="grip">&#9776;</span><span class="proj-name"></span><span class="proj-acronym"></span>${canDelete ? '<span class="proj-remove" onclick="this.parentElement.remove()" title="Supprimer">&times;</span>' : ''}`;
      el.querySelector('.proj-name').textContent = p.name;
      el.querySelector('.proj-acronym').textContent = p.acronym;
      list.appendChild(el);
    });
    if (list._sortable) list._sortable.destroy();
    list._sortable = new Sortable(list, { animation: 150, ghostClass: 'task-ghost' });
  }
  modal.style.display = 'flex';
}

function selectCatColor(dot) {
  const container = document.getElementById('cat-modal-colors');
  container.querySelectorAll('.color-dot').forEach(d => d.classList.remove('selected'));
  dot.classList.add('selected');
}

function saveCat() {
  const id = document.getElementById('cat-modal-id').value;
  const name = document.getElementById('cat-modal-name').value.trim();
  const selected = document.querySelector('#cat-modal-colors .color-dot.selected');
  const color = selected ? selected.dataset.color : '';
  if (!name) return;
  // Field name MUST match the Pydantic schema (snake_case). Sending
  // camelCase ``projectOrder`` here would silently drop the reorder
  // because Pydantic v2 ignores unknown fields by default (#71).
  const project_order = [...document.querySelectorAll('#cat-modal-projects .cat-modal-project')].map(el => el.dataset.projectId);
  const method = id ? 'PATCH' : 'POST';
  const url = id ? `${API_BASE}/categories/${id}` : `${API_BASE}/categories`;
  apiCall(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, color, project_order }) })
    .then(() => globalThis.location.reload()).catch(() => {});
  document.getElementById('cat-modal').style.display = 'none';
}

function deleteCat() {
  const id = document.getElementById('cat-modal-id').value;
  if (!id) return;
  apiCall(`${API_BASE}/categories/${id}`, { method: 'DELETE' })
    .then(() => globalThis.location.reload()).catch(() => {});
  document.getElementById('cat-modal').style.display = 'none';
}

function addProjectInCatModal() {
  const list = document.getElementById('cat-modal-projects');
  const el = document.createElement('div');
  el.className = 'cat-modal-project';
  el.dataset.projectId = '';
  el.innerHTML = `<span class="grip">&#9776;</span><input type="text" class="proj-name-input" placeholder="Nom du projet" style="flex:1;border:1px solid var(--border);border-radius:3px;padding:2px 6px;font-size:12px;font-family:inherit"><input type="text" class="proj-acr-input" placeholder="ACRO" maxlength="4" style="width:50px;border:1px solid var(--border);border-radius:3px;padding:2px 6px;font-size:10px;font-family:inherit;text-transform:uppercase"><span class="proj-remove" onclick="this.parentElement.remove()" title="Supprimer">&times;</span>`;
  list.appendChild(el);
  el.querySelector('.proj-name-input').focus();
}

// -- Project CRUD ------------------------------------------------------------

function renderProjectSibling(p, currentId) {
  const el = document.createElement('div');
  el.className = 'cat-modal-project' + (p.id === currentId ? ' current-project' : '');
  el.dataset.projectId = p.id;
  el.innerHTML = `<span class="grip">&#9776;</span><span class="proj-name"></span><span class="proj-acronym"></span>`;
  el.querySelector('.proj-name').textContent = p.name;
  el.querySelector('.proj-acronym').textContent = p.acronym;
  return el;
}

function populateProjectSiblings(list, label, cat, currentId) {
  if (!list) return;
  if (!cat) {
    list.innerHTML = '';
    if (label) label.style.display = 'none';
    return;
  }
  list.innerHTML = '';
  const projs = (typeof CAT_PROJECTS === 'undefined') ? [] : (CAT_PROJECTS[cat] || []);
  projs.forEach(p => list.appendChild(renderProjectSibling(p, currentId)));
  if (list._sortable) list._sortable.destroy();
  list._sortable = new Sortable(list, { animation: 150, ghostClass: 'task-ghost' });
  if (label) label.style.display = projs.length > 0 ? '' : 'none';
}

function editProject(id, name, acronym, cat, status, defaultWho) {
  const modal = document.getElementById('project-modal');
  if (!modal) return;
  document.getElementById('proj-modal-title').textContent = id ? 'Editer le projet' : 'Nouveau projet';
  document.querySelectorAll('#proj-modal-delete').forEach(b => b.style.display = id ? '' : 'none');
  document.getElementById('new-proj-id').value = id || '';
  document.getElementById('new-proj-cat').value = cat || '';
  document.getElementById('new-proj-name').value = name || '';
  document.getElementById('new-proj-acronym').value = acronym || '';
  document.getElementById('new-proj-status').value = status || 'active';
  const dwSelect = document.getElementById('new-proj-default-who');
  if (dwSelect) dwSelect.value = defaultWho || '';

  populateProjectSiblings(
    document.getElementById('proj-modal-projects'),
    document.getElementById('proj-modal-projects-label'),
    cat,
    id,
  );

  modal.style.display = 'flex';
}

function saveProject() {
  const id = document.getElementById('new-proj-id').value;
  const name = document.getElementById('new-proj-name').value.trim();
  const acronym = document.getElementById('new-proj-acronym').value.trim().toUpperCase();
  const cat = document.getElementById('new-proj-cat').value;
  const status = document.getElementById('new-proj-status').value;
  const defaultWho = document.getElementById('new-proj-default-who')?.value || '';
  if (!name || !acronym) return;
  const method = id ? 'PATCH' : 'POST';
  const url = id ? `${API_BASE}/projects/${id}` : `${API_BASE}/projects`;
  // Field name MUST match the Pydantic schema (snake_case). Sending
  // camelCase ``projectOrder`` here would silently drop the reorder (#71).
  const project_order = [...document.querySelectorAll('#proj-modal-projects .cat-modal-project')].map(el => el.dataset.projectId);
  apiCall(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, acronym, cat, status, default_who: defaultWho, project_order }) })
    .then(() => globalThis.location.reload()).catch(() => {});
  document.getElementById('project-modal').style.display = 'none';
}

function deleteProject() {
  const id = document.getElementById('new-proj-id').value;
  if (!id) return;
  apiCall(`${API_BASE}/projects/${id}`, { method: 'DELETE' })
    .then(() => globalThis.location.reload()).catch(() => {});
  document.getElementById('project-modal').style.display = 'none';
}

// Create an onboarding token (or replace an existing one) via the API, then
// copy the full onboard URL (with token embedded) to clipboard. The agent
// can start immediately: pip install kenboard, create .ken, ken list (#159).
async function copyOnboardLink(btn, catId, projectId) {
  const restore = btn.textContent;
  const flash = (label) => {
    btn.textContent = label;
    setTimeout(() => { btn.textContent = restore; }, 2500);
  };
  try {
    const r = await apiCall(`${API_BASE}/keys/onboard`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cat_id: catId, project_id: projectId }),
    });
    const data = await r.json();
    const url = `${globalThis.location.origin}/onboard/cat/${catId}/project/${projectId}?token=${data.key}`;
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(url);
      flash('Copied!');
    } else {
      flash('Copy unsupported');
    }
  } catch (e) {
    console.debug('copyOnboardLink: apiCall failed', e);
  }
}

// -- Fullscreen task view (#155) ----------------------------------------------

async function openFullscreen(btn, id) {
  const card = btn.closest('.kanban-task');
  const avatarColor = card?.querySelector('.task-avatar')?.style.background || 'var(--dimmed)';
  // Show the modal immediately with minimal data, then fill from API (#221)
  _populateFullscreen(id, '...', '', '', '', avatarColor, btn);
  document.getElementById('task-fullscreen').showModal();

  try {
    const r = await apiCall(`${API_BASE}/tasks/${id}`);
    const t = await r.json();
    _populateFullscreen(
      t.id, t.title, t.description || '', t.who || '',
      t.due_date ? _fmtDate(t.due_date) : '', avatarColor, btn
    );
  } catch (e) {
    console.debug('openFullscreen: API fetch failed', e);
  }
}

function _populateFullscreen(id, title, desc, who, when, avatarColor, btn) {
  document.getElementById('fs-id').textContent = '#' + id;
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

  document.getElementById('fs-edit-btn').onclick = function () {
    closeFullscreen();
    openEditTask(btn, id);
  };
}

function closeFullscreen() {
  document.getElementById('task-fullscreen').close();
}

// Native <dialog> handles Escape key automatically. Backdrop click
// needs manual handling (click on the dialog element itself, not its children).
document.getElementById('task-fullscreen')?.addEventListener('click', function (e) {
  if (e.target === this) this.close();
});

// -- Task CRUD ---------------------------------------------------------------

async function _lazyLoadDesc(el, taskId) {
  if (!taskId || el.dataset.descLoaded) return;
  try {
    const r = await fetch(`${API_BASE}/tasks/${taskId}`);
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
    console.debug('_lazyLoadDesc: fetch failed', e);
  }
}

async function toggleDetail(el, event) {
  // The 2nd click of a double-click reaches us with `event.detail === 2`
  // (browser-set click count). Bail so the matching `dblclick` handler can
  // open the edit modal without us toggling the detail view back off
  // underneath it (#111).
  if (event && event.detail > 1) return;
  const taskId = el.dataset.taskId;
  const wasDetail = el.classList.contains('detail-mode');
  document.querySelectorAll('.kanban-task.detail-mode').forEach(t => t.classList.remove('detail-mode'));
  if (wasDetail) {
    if (_taskHashId() === taskId) _clearTaskHash();
    return;
  }
  el.classList.add('detail-mode');
  if (taskId) _setTaskHash(taskId);
  await _lazyLoadDesc(el, taskId);
}

// -- URL <-> task detail sync (#109) -----------------------------------------
// The URL fragment doubles as task-detail state: ``#ID-<task-id>`` puts the
// matching card into detail mode. Cards expose the id via ``data-task-id``
// (not a real DOM ``id``) so the browser does not auto-scroll on hash
// changes — we control scrolling explicitly.
const _TASK_HASH_RE = /^#?ID-(\d+)$/;

function _taskHashId() {
  const m = _TASK_HASH_RE.exec(globalThis.location.hash);
  return m ? m[1] : null;
}

function _setTaskHash(taskId) {
  // replaceState avoids polluting the history with one entry per click.
  // hashchange does not fire on replaceState, but toggleDetail already
  // updated the DOM directly, so no extra work is needed here.
  if (_taskHashId() === String(taskId)) return;
  const url = new URL(globalThis.location.href);
  url.hash = 'ID-' + taskId;
  globalThis.history.replaceState(null, '', url);
}

function _clearTaskHash() {
  if (_taskHashId() === null) return;
  const url = new URL(globalThis.location.href);
  globalThis.history.replaceState(null, '', url.pathname + url.search);
}

async function _applyTaskHash() {
  const id = _taskHashId();
  document.querySelectorAll('.kanban-task.detail-mode').forEach(t => {
    if (t.dataset.taskId !== id) t.classList.remove('detail-mode');
  });
  if (!id) return;
  const card = document.querySelector(`.kanban-task[data-task-id="${id}"]`);
  if (!card) return;  // Stale link: task no longer on this page.
  card.classList.add('detail-mode');
  card.scrollIntoView({ block: 'center', behavior: 'auto' });
  await _lazyLoadDesc(card, id);
}

// React to back/forward and direct edits of the URL fragment. We don't fire
// this from `toggleDetail` (that path uses replaceState) so the listener
// only handles externally-driven changes.
globalThis.addEventListener('hashchange', _applyTaskHash);
// Initial pass: restore detail mode from the URL on load (incl. after the
// 60s auto-refresh, which preserves the fragment).
_applyTaskHash();

async function openEditTask(btn, id) {
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
  document.getElementById('task-modal-heading').textContent = 'Editer la t\u00e2che';
  document.getElementById('task-modal-title').value = '';
  document.getElementById('task-modal-desc').value = '';
  document.getElementById('task-modal-when').value = '';
  document.getElementById('task-modal-status').value = status;
  const delBtn = document.getElementById('task-modal-delete');
  if (delBtn) delBtn.style.display = id ? '' : 'none';
  const dupBtn = document.getElementById('task-modal-duplicate');
  if (dupBtn) dupBtn.style.display = id ? '' : 'none';
  document.getElementById('task-modal').style.display = 'flex';

  // Fetch full task data from API (#221)
  try {
    const r = await apiCall(`${API_BASE}/tasks/${id}`);
    const t = await r.json();
    document.getElementById('task-modal-title').value = t.title;
    document.getElementById('task-modal-desc').value = t.description || '';
    document.getElementById('task-modal-when').value = t.due_date ? _fmtDate(t.due_date) : '';
    document.getElementById('task-modal-status').value = t.status || status;
    const whoSelect = document.getElementById('task-modal-who');
    const effectiveWho = t.who || projectDefaultWho;
    if (whoSelect && effectiveWho && [...whoSelect.options].some(o => o.value === effectiveWho)) {
      whoSelect.value = effectiveWho;
    }
  } catch (e) {
    console.debug('openEditTask: API fetch failed', e);
  }
}

let _taskTargetList = null;
let _taskProjectId = null;
let _taskEditId = null;
function openTaskModal(taskList, projectId) {
  _taskTargetList = taskList;
  const kanban = taskList.closest('.kanban');
  _taskProjectId = projectId || kanban?.dataset?.projectId || '';
  _taskEditId = null;
  document.getElementById('task-modal-project-id').value = _taskProjectId;
  document.getElementById('task-modal-heading').textContent = 'Nouvelle t\u00e2che';
  document.getElementById('task-modal-title').value = '';
  document.getElementById('task-modal-desc').value = '';
  document.getElementById('task-modal-when').value = '';
  document.getElementById('task-modal-status').value = 'todo';
  // who: project default if set, else logged-in user (already pre-selected
  // server-side via Jinja in the modal template).
  const projectDefaultWho = kanban?.dataset?.defaultWho || '';
  if (projectDefaultWho) {
    const whoSelect = document.getElementById('task-modal-who');
    if (whoSelect && [...whoSelect.options].some(o => o.value === projectDefaultWho)) {
      whoSelect.value = projectDefaultWho;
    }
  }
  const delBtn = document.getElementById('task-modal-delete');
  if (delBtn) delBtn.style.display = 'none';
  const dupBtn = document.getElementById('task-modal-duplicate');
  if (dupBtn) dupBtn.style.display = 'none';
  document.getElementById('task-modal').style.display = 'flex';
  document.getElementById('task-modal-title').focus();
}

function saveTaskModal() {
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
      try { sessionStorage.setItem('kb-focus-task', String(taskId)); } catch (_e) { /* ignore */ }
    }
    globalThis.location.reload();
  };
  if (_taskEditId) {
    apiCall(`${API_BASE}/tasks/${_taskEditId}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title, description: desc, who, due_date: when || null, status }) })
      .then(() => reloadFocused(_taskEditId)).catch(() => {});
  } else {
    apiCall(`${API_BASE}/tasks`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ project_id: projectId, title, description: desc, who, due_date: when || null, status }) })
      .then(r => r.json()).then(t => reloadFocused(t && t.id)).catch(() => {});
  }
  document.getElementById('task-modal').style.display = 'none';
}

function deleteTask() {
  if (!_taskEditId) return;
  apiCall(`${API_BASE}/tasks/${_taskEditId}`, { method: 'DELETE' })
    .then(() => globalThis.location.reload()).catch(() => {});
  document.getElementById('task-modal').style.display = 'none';
}

async function duplicateTask() {
  // POST a copy of the current modal fields, then re-bind the modal to
  // the new task id so the user can keep editing without closing.
  if (!_taskEditId) return;
  const title = document.getElementById('task-modal-title').value.trim();
  if (!title) return;
  const desc = document.getElementById('task-modal-desc').value;
  const who = document.getElementById('task-modal-who').value;
  const when = document.getElementById('task-modal-when').value;
  const status = document.getElementById('task-modal-status').value;
  const projectId = document.getElementById('task-modal-project-id').value;
  let r;
  try {
    r = await apiCall(`${API_BASE}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: projectId,
        title: title + ' - copy',
        description: desc,
        who,
        due_date: when || null,
        status,
      }),
    });
  } catch (e) {
    // apiCall already surfaced the error popup; bail out of the duplicate.
    console.debug('duplicateTask: apiCall failed', e);
    return;
  }
  const created = await r.json();
  // Re-bind the modal to the new task. The user keeps editing in place.
  _taskEditId = created.id;
  document.getElementById('task-modal-title').value = created.title;
  document.getElementById('task-modal-heading').textContent = 'Editer la t\u00e2che (copie)';
  document.getElementById('task-modal-title').focus();
  document.getElementById('task-modal-title').select();
}

// -- Delete confirmation -----------------------------------------------------

function confirmDelete(btn, callback) {
  // Hide parent edit modal first
  const parentModal = btn.closest('.project-add-modal');
  if (parentModal) parentModal.style.display = 'none';

  const modal = document.getElementById('confirm-modal');
  const msg = document.getElementById('confirm-modal-msg');
  msg.textContent = '\u00cates-vous s\u00fbr de vouloir supprimer cet \u00e9l\u00e9ment ?';
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
  // reference so the generic dismissal handler below picks it up. Replaces
  // the previous modal.onclick handler that depended on stopPropagation
  // from the inner card (Sonar a11y, #83).
  modal._reopenParent = parentModal;
  modal.style.display = 'flex';
}

// -- Drag & drop -------------------------------------------------------------

// Task card drag-and-drop. On mobile (≤480px) a drag handle is used so
// vertical scroll is not blocked by Sortable (#161, same pattern as
// the category grid's .cat-drag-handle).
const _mobileTaskMq = globalThis.matchMedia('(max-width: 480px)');

function _initTaskSortables() {
  document.querySelectorAll('.kanban-col').forEach(col => {
    const tc = col.querySelector('.kanban-tasks');
    if (!tc) return;
    // Destroy previous instance if any (re-init on breakpoint change)
    if (tc._sortable) tc._sortable.destroy();
    const opts = {
      group: 'kanban', animation: 150, draggable: '.kanban-task',
      ghostClass: 'task-ghost', chosenClass: 'task-chosen', dragClass: 'task-drag',
      onEnd: (evt) => {
        const taskId = evt.item.dataset.taskId;
        const newStatus = evt.to.dataset.status;
        const newProjectId = evt.to.closest('.kanban')?.dataset?.projectId;
        if (!taskId) return;
        const body = { status: newStatus, position: evt.newIndex };
        if (newProjectId) body.project_id = newProjectId;
        apiCall(`${API_BASE}/tasks/${taskId}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
          .catch(() => {});
      }
    };
    if (_mobileTaskMq.matches) {
      opts.handle = '.task-drag-handle';
    }
    tc._sortable = new Sortable(tc, opts);
  });
}
_initTaskSortables();
_mobileTaskMq.addEventListener('change', _initTaskSortables);

// -- Markdown rendering -----------------------------------------------------
// Task descriptions are authored in Markdown and rendered with marked.js,
// then sanitized with DOMPurify (#52) before being assigned to innerHTML.
// marked >= 5 no longer sanitizes itself, so a description like
// `<img src=x onerror=alert(1)>` would otherwise execute on render.
//
// The raw markdown lives as the textContent of `.task-desc` (escaped by Jinja
// so reading textContent always returns the original characters). We replace
// the innerHTML once with the parsed+sanitized HTML and stash the source on a
// data attribute so we never re-parse the same node twice.
if (typeof marked !== 'undefined') {
  marked.setOptions({ gfm: true, breaks: true });
}
function renderMarkdown(root) {
  if (typeof marked === 'undefined') return;
  (root || document).querySelectorAll('.task-desc').forEach(el => {
    if (el.dataset.mdRendered === '1') return;
    const src = el.textContent;
    const dirty = marked.parse(src);
    el.innerHTML = (typeof DOMPurify === 'undefined')
      ? dirty
      : DOMPurify.sanitize(dirty);
    el.dataset.mdRendered = '1';
  });
}
renderMarkdown();

// -- Modal dismissal ---------------------------------------------------------
// Generic Escape + click-outside dismissal for .project-add-modal. Replaces
// the inline `onclick="this.style.display='none'"` on backdrops and the
// `event.stopPropagation()` on inner cards (Sonar S6848: clickable element
// without keyboard equivalent, #83). Modals with `data-no-dismiss="1"` are
// excluded — used by the API key reveal modal which must be acknowledged
// explicitly because the secret is shown only once.
function _dismissModal(modal) {
  modal.style.display = 'none';
  // confirmDelete stashes the parent modal so backdrop/Escape dismissal
  // re-opens it (matches the cancel button behaviour).
  if (modal._reopenParent) {
    modal._reopenParent.style.display = 'flex';
    modal._reopenParent = null;
  }
}
document.querySelectorAll('.project-add-modal').forEach(modal => {
  if (modal.dataset.noDismiss === '1') return;
  modal.addEventListener('click', (e) => {
    // Only fire when the click landed on the backdrop itself, not on any
    // child — clicks inside the inner card must not dismiss the modal.
    if (e.target === modal) _dismissModal(modal);
  });
});
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  const visible = [...document.querySelectorAll('.project-add-modal')].filter(
    m => m.style.display && m.style.display !== 'none' && m.dataset.noDismiss !== '1',
  );
  if (visible.length === 0) return;
  // Topmost = last in DOM order (most recently opened on top of any others).
  _dismissModal(visible.at(-1));
});

// -- Auto refresh ------------------------------------------------------------
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
setInterval(() => {
  if (shouldSkipRefresh()) return;
  globalThis.location.reload();
}, AUTO_REFRESH_MS);

// -- Keyboard shortcuts (#249) -----------------------------------------------
// Selection model: at most one ``.kanban-task`` carries
// ``data-kb-selected="true"``. Navigation, actions, and the help modal
// route through that selection. Disabled while a form field has focus
// (so typing "edit" in a title doesn't open the edit modal); modal-aware
// (only Enter / Cmd+Enter / Esc fire when a task modal is open).

const KB_TASK_HASH_RE = /^#?ID-(\d+)$/;
let _kbGPrefix = false;
let _kbGTimer = null;

function _kbSelectedCard() {
  return document.querySelector('.kanban-task[data-kb-selected="true"]');
}

function _kbVisibleCardsInColumn(col) {
  return [...col.querySelectorAll('.kanban-task:not(.task-hidden)')];
}

function _kbAllVisibleCards() {
  return [...document.querySelectorAll('.kanban-task:not(.task-hidden)')];
}

function _kbSelectCard(card, { scroll = true } = {}) {
  document.querySelectorAll('.kanban-task[data-kb-selected]').forEach(c => {
    if (c !== card) c.removeAttribute('data-kb-selected');
  });
  if (!card) return;
  card.dataset.kbSelected = 'true';
  if (scroll) card.scrollIntoView({ block: 'center', behavior: 'auto' });
}

function _kbDeselect() {
  document.querySelectorAll('.kanban-task[data-kb-selected]').forEach(c => {
    c.removeAttribute('data-kb-selected');
  });
}

function _kbSelectFirst() {
  const first = _kbAllVisibleCards()[0];
  if (first) _kbSelectCard(first);
  return first;
}

// 2D navigation. Vertical = within the current column; horizontal = jump
// to the adjacent column at the same position (clamped to its length).
function _kbMoveVertical(delta) {
  const current = _kbSelectedCard();
  if (!current) return _kbSelectFirst();
  const col = current.closest('.kanban-tasks');
  if (!col) return null;
  const siblings = _kbVisibleCardsInColumn(col);
  const idx = siblings.indexOf(current);
  if (idx === -1) return null;
  const next = siblings[Math.max(0, Math.min(siblings.length - 1, idx + delta))];
  if (next && next !== current) _kbSelectCard(next);
  return next;
}

function _kbMoveHorizontal(delta) {
  const current = _kbSelectedCard();
  if (!current) return _kbSelectFirst();
  const kanban = current.closest('.kanban');
  if (!kanban) return null;
  const cols = [...kanban.querySelectorAll('.kanban-tasks')];
  const col = current.closest('.kanban-tasks');
  const colIdx = cols.indexOf(col);
  if (colIdx === -1) return null;
  const targetColIdx = Math.max(0, Math.min(cols.length - 1, colIdx + delta));
  if (targetColIdx === colIdx) return current;
  const targetCol = cols[targetColIdx];
  const targetCards = _kbVisibleCardsInColumn(targetCol);
  if (targetCards.length === 0) {
    // Skip empty column: keep stepping in the same direction until we find a
    // column with at least one visible card, or run out of columns.
    for (let i = targetColIdx + delta; i >= 0 && i < cols.length; i += delta) {
      const cs = _kbVisibleCardsInColumn(cols[i]);
      if (cs.length) {
        _kbSelectCard(cs[0]);
        return cs[0];
      }
    }
    return current;
  }
  const positionInOriginalCol = _kbVisibleCardsInColumn(col).indexOf(current);
  const target = targetCards[Math.min(positionInOriginalCol, targetCards.length - 1)] || targetCards[0];
  _kbSelectCard(target);
  return target;
}

// -- Action handlers (operate on the currently selected card) ---------------

function _kbActionOpen() {
  const card = _kbSelectedCard();
  if (card) toggleDetail(card, { detail: 1 });
}

function _kbActionEdit() {
  const card = _kbSelectedCard();
  if (card) openEditTask(card, card.dataset.taskId);
}

function _kbActionFullscreen() {
  const card = _kbSelectedCard();
  if (card) openFullscreen(card, card.dataset.taskId);
}

function _kbActionCreate() {
  const card = _kbSelectedCard();
  const taskList = card?.closest('.kanban-tasks')
    || document.querySelector('.kanban-tasks');
  if (!taskList) return;
  const projectId = taskList.closest('.kanban')?.dataset?.projectId || '';
  openTaskModal(taskList, projectId);
}

function _kbActionHelp() {
  const m = document.getElementById('kb-help-modal');
  if (m) m.style.display = 'flex';
}

function _kbActionHome() {
  globalThis.location.href = '/';
}

// Esc cascade: close fullscreen → close any task-modal → exit detail-mode →
// deselect. The generic ``project-add-modal`` Escape dismissal already runs
// from the earlier handler (see ``_dismissModal``); we layer on top by only
// taking action when no modal handled the event.
function _kbActionEscape() {
  const fs = document.getElementById('task-fullscreen');
  if (fs && fs.open) {
    if (typeof closeFullscreen === 'function') closeFullscreen();
    return true;
  }
  const detail = document.querySelector('.kanban-task.detail-mode');
  if (detail) {
    detail.classList.remove('detail-mode');
    _clearTaskHash();
    return true;
  }
  if (_kbSelectedCard()) {
    _kbDeselect();
    return true;
  }
  return false;
}

// -- Routing -----------------------------------------------------------------

function _kbAnyModalOpen() {
  if (document.getElementById('task-fullscreen')?.open) return true;
  for (const m of document.querySelectorAll('.project-add-modal')) {
    if (m.style.display && m.style.display !== 'none') return true;
  }
  return false;
}

function _kbTargetIsFormField(t) {
  if (!t) return false;
  if (t.matches?.('input, textarea, select, [contenteditable="true"]')) return true;
  return false;
}

function _kbTaskModalIsOpen() {
  const m = document.getElementById('task-modal');
  return m && m.style.display && m.style.display !== 'none';
}

// Inside the task modal: Enter saves from short text fields; Cmd/Ctrl+Enter
// saves from the description textarea (so plain Enter keeps inserting a
// newline). Esc is handled by the generic dismissal earlier in the file.
function _kbHandleTaskModal(e) {
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

document.addEventListener('keydown', (e) => {
  // The generic Escape dismissal earlier in the file already handles
  // .project-add-modal close. Don't double-process.
  if (e.defaultPrevented) return;

  // ---- Modal-scoped shortcuts ----
  if (_kbTaskModalIsOpen()) {
    if (_kbHandleTaskModal(e)) return;
    // While the task modal is open, swallow all other keyboard shortcuts
    // (navigation, actions, ?, g h) so they can't fire underneath it.
    return;
  }
  if (_kbAnyModalOpen()) return;

  // ---- Form-field gate ----
  // Don't intercept letters/arrows while the user is typing in a field.
  // (Modifier combos like Cmd+R / Cmd+F are still passed through anyway
  // because we only act on a small allowlist of keys.)
  if (_kbTargetIsFormField(e.target)) return;

  // ---- ``g`` two-step prefix ----
  if (_kbGPrefix) {
    _kbGPrefix = false;
    clearTimeout(_kbGTimer);
    _kbGTimer = null;
    if (e.key === 'h') {
      e.preventDefault();
      _kbActionHome();
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
      _kbMoveVertical(-1);
      return;
    case 'ArrowDown':
    case 'j':
      e.preventDefault();
      _kbMoveVertical(1);
      return;
    case 'ArrowLeft':
    case 'h':
      e.preventDefault();
      _kbMoveHorizontal(-1);
      return;
    case 'ArrowRight':
    case 'l':
      e.preventDefault();
      _kbMoveHorizontal(1);
      return;
    case 'Enter':
      if (_kbSelectedCard()) {
        e.preventDefault();
        _kbActionOpen();
        return;
      }
      break;
    case 'e':
      if (_kbSelectedCard()) {
        e.preventDefault();
        _kbActionEdit();
        return;
      }
      break;
    case 'f':
      if (_kbSelectedCard()) {
        e.preventDefault();
        _kbActionFullscreen();
        return;
      }
      break;
    case 'c':
      e.preventDefault();
      _kbActionCreate();
      return;
    case '?':
      e.preventDefault();
      _kbActionHelp();
      return;
    case 'Escape':
      // The generic dismissal handles open modals; here we cover the
      // detail-mode / selection cascade for the bare-board case.
      if (_kbActionEscape()) e.preventDefault();
      return;
    case 'g':
      e.preventDefault();
      _kbGPrefix = true;
      _kbGTimer = setTimeout(() => { _kbGPrefix = false; _kbGTimer = null; }, 1500);
      return;
    default:
      break;
  }
});

// Click on a card → select it (in addition to the existing toggleDetail
// behaviour). Keeps the keyboard-nav state in sync with mouse interaction.
document.addEventListener('click', (e) => {
  const card = e.target.closest?.('.kanban-task');
  if (card) _kbSelectCard(card, { scroll: false });
});

// On load, restore keyboard selection from two sources, in priority order:
//   1. ``sessionStorage["kb-focus-task"]`` — set by saveTaskModal so the
//      just-saved card stays selected and scrolls into view across the
//      reload (without flipping to detail-mode, unlike the URL hash).
//   2. The ``#ID-<id>`` URL fragment — already drives detail-mode via
//      _applyTaskHash; reuse it as the keyboard-selection starting point.
(function _kbInitSelection() {
  let id = null;
  try {
    id = sessionStorage.getItem('kb-focus-task');
    if (id) sessionStorage.removeItem('kb-focus-task');
  } catch (_e) { /* sessionStorage unavailable (private mode) — fall through */ }
  if (!id) {
    const m = KB_TASK_HASH_RE.exec(globalThis.location.hash);
    if (m) id = m[1];
  }
  if (!id) return;
  const card = document.querySelector(`.kanban-task[data-task-id="${id}"]`);
  if (card) _kbSelectCard(card, { scroll: true });
})();
