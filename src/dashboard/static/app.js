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

// Copy a deep-link onboarding URL (cat_id in path + project_id in fragment)
// to the clipboard so the user can paste it to an LLM agent. The agent then
// hits the URL, the server replies 401 with the runbook from
// dashboard.onboarding (#117) and the agent has both ids it needs to write
// its `.ken` file.
function copyOnboardLink(btn, catId, projectId) {
  const url = `${globalThis.location.origin}/cat/${catId}.html#${projectId}`;
  const restore = btn.textContent;
  const flash = (label) => {
    btn.textContent = label;
    setTimeout(() => { btn.textContent = restore; }, 1500);
  };
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(url).then(
      () => flash('Copied!'),
      () => flash('Copy failed'),
    );
  } else {
    // navigator.clipboard requires HTTPS or localhost. Anything else
    // (legacy IE, prehistoric Safari, etc.) is out of support — kenboard
    // targets modern browsers, the user can copy from the URL bar instead.
    flash('Copy unsupported');
  }
}

// -- Task CRUD ---------------------------------------------------------------

function toggleDetail(el, event) {
  // The 2nd click of a double-click reaches us with `event.detail === 2`
  // (browser-set click count). Bail so the matching `dblclick` handler can
  // open the edit modal without us toggling the detail view back off
  // underneath it (#111).
  if (event && event.detail > 1) return;
  const taskId = el.dataset.taskId;
  const wasDetail = el.classList.contains('detail-mode');
  document.querySelectorAll('.kanban-task.detail-mode').forEach(t => t.classList.remove('detail-mode'));
  if (wasDetail) {
    // Closing the currently open task: drop the URL fragment if it points
    // to it, so a copy of the address bar no longer reopens it.
    if (_taskHashId() === taskId) _clearTaskHash();
    return;
  }
  el.classList.add('detail-mode');
  // Sync the URL fragment so the detail view survives reloads (60s
  // auto-refresh) and produces shareable deep links to the card (#109).
  if (taskId) _setTaskHash(taskId);
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

function _applyTaskHash() {
  const id = _taskHashId();
  document.querySelectorAll('.kanban-task.detail-mode').forEach(t => {
    if (t.dataset.taskId !== id) t.classList.remove('detail-mode');
  });
  if (!id) return;
  const card = document.querySelector(`.kanban-task[data-task-id="${id}"]`);
  if (!card) return;  // Stale link: task no longer on this page.
  card.classList.add('detail-mode');
  card.scrollIntoView({ block: 'center', behavior: 'auto' });
}

// React to back/forward and direct edits of the URL fragment. We don't fire
// this from `toggleDetail` (that path uses replaceState) so the listener
// only handles externally-driven changes.
globalThis.addEventListener('hashchange', _applyTaskHash);
// Initial pass: restore detail mode from the URL on load (incl. after the
// 60s auto-refresh, which preserves the fragment).
_applyTaskHash();

function openEditTask(btn, id, title, desc, who, when) {
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
  document.getElementById('task-modal-title').value = title;
  document.getElementById('task-modal-desc').value = desc;
  // Keep the existing assignee if set, else fall back to the project's
  // default_who (#33). When neither is set the select stays on its
  // server-rendered default (the logged-in user, cf. modals/task.html).
  const whoSelect = document.getElementById('task-modal-who');
  const effectiveWho = who || projectDefaultWho;
  if (whoSelect && effectiveWho && [...whoSelect.options].some(o => o.value === effectiveWho)) {
    whoSelect.value = effectiveWho;
  } else if (whoSelect) {
    whoSelect.value = who;
  }
  document.getElementById('task-modal-when').value = when;
  document.getElementById('task-modal-status').value = status;
  const delBtn = document.getElementById('task-modal-delete');
  if (delBtn) delBtn.style.display = id ? '' : 'none';
  const dupBtn = document.getElementById('task-modal-duplicate');
  if (dupBtn) dupBtn.style.display = id ? '' : 'none';
  document.getElementById('task-modal').style.display = 'flex';
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
  if (_taskEditId) {
    // Update existing task
    apiCall(`${API_BASE}/tasks/${_taskEditId}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title, description: desc, who, due_date: when || null, status }) })
      .then(() => globalThis.location.reload()).catch(() => {});
  } else {
    // Create new task
    apiCall(`${API_BASE}/tasks`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ project_id: projectId, title, description: desc, who, due_date: when || null, status }) })
      .then(() => globalThis.location.reload()).catch(() => {});
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

// On mobile (≤ 480px), restrict the draggable area of category cards to a
// dedicated handle so vertical scrolling stays smooth. On desktop the whole
// card stays draggable. We re-evaluate the matchMedia on resize and rebuild
// the Sortable instance so the behaviour switches as the viewport changes.
const catGrid = document.querySelector('.cat-grid');
let _catSortable = null;
const _mobileCatMq = globalThis.matchMedia('(max-width: 480px)');

function _initCatSortable() {
  if (!catGrid) return;
  if (_catSortable) {
    _catSortable.destroy();
    _catSortable = null;
  }
  const opts = {
    animation: 150,
    draggable: '.cat-card:not(.cat-card-add)',
    ghostClass: 'task-ghost',
    chosenClass: 'task-chosen',
    filter: '.cat-card-add',
    onEnd: (evt) => {
      apiCall(`${API_BASE}/categories/reorder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from: evt.oldIndex, to: evt.newIndex }),
      }).catch(() => {});
    },
  };
  if (_mobileCatMq.matches) {
    opts.handle = '.cat-drag-handle';
  }
  _catSortable = new Sortable(catGrid, opts);
}
_initCatSortable();
_mobileCatMq.addEventListener('change', _initCatSortable);

document.querySelectorAll('.kanban-col').forEach(col => {
  const tc = col.querySelector('.kanban-tasks');
  if (!tc) return;
  new Sortable(tc, {
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
  });
});

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
