'use strict';

const API_BASE = '/api/v1';

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
  document.querySelector('#cat-modal h3').textContent = id ? 'Editer categorie' : 'Nouvelle categorie';
  const delBtn = document.getElementById('cat-modal-delete');
  if (delBtn) delBtn.style.display = id ? '' : 'none';
  const colors = document.getElementById('cat-modal-colors');
  if (colors) colors.querySelectorAll('.color-dot').forEach(d => {
    d.classList.toggle('selected', d.dataset.color === color);
  });
  const list = document.getElementById('cat-modal-projects');
  if (list) {
    list.innerHTML = '';
    const projs = (typeof CAT_PROJECTS !== 'undefined' && id) ? (CAT_PROJECTS[id] || []) : [];
    projs.forEach(p => {
      const el = document.createElement('div');
      el.className = 'cat-modal-project';
      el.dataset.projectId = p.id;
      const canDelete = p.tasks === 0;
      el.innerHTML = `<span class="grip">&#9776;</span><span class="proj-name">${p.name}</span><span class="proj-acronym">${p.acronym}</span>${canDelete ? '<span class="proj-remove" onclick="this.parentElement.remove()" title="Supprimer">&times;</span>' : ''}`;
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
  const projectOrder = [...document.querySelectorAll('#cat-modal-projects .cat-modal-project')].map(el => el.dataset.projectId);
  const method = id ? 'PATCH' : 'POST';
  const url = id ? `${API_BASE}/categories/${id}` : `${API_BASE}/categories`;
  fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, color, projectOrder }) })
    .then(() => window.location.reload()).catch(err => console.warn('API:', err));
  document.getElementById('cat-modal').style.display = 'none';
}

function deleteCat() {
  const id = document.getElementById('cat-modal-id').value;
  if (!id) return;
  fetch(`${API_BASE}/categories/${id}`, { method: 'DELETE' })
    .then(() => window.location.reload()).catch(err => console.warn('API:', err));
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

function editProject(id, name, acronym, cat, status) {
  const modal = document.getElementById('project-modal');
  if (!modal) return;
  document.getElementById('proj-modal-title').textContent = id ? 'Editer projet' : 'Nouveau projet';
  document.querySelectorAll('#proj-modal-delete').forEach(b => b.style.display = id ? '' : 'none');
  document.getElementById('new-proj-id').value = id || '';
  document.getElementById('new-proj-cat').value = cat || '';
  document.getElementById('new-proj-name').value = name || '';
  document.getElementById('new-proj-acronym').value = acronym || '';
  document.getElementById('new-proj-status').value = status || 'active';

  // Populate sibling projects list
  const list = document.getElementById('proj-modal-projects');
  const label = document.getElementById('proj-modal-projects-label');
  if (list && cat) {
    list.innerHTML = '';
    const projs = (typeof CAT_PROJECTS !== 'undefined') ? (CAT_PROJECTS[cat] || []) : [];
    projs.forEach(p => {
      const el = document.createElement('div');
      el.className = 'cat-modal-project' + (p.id === id ? ' current-project' : '');
      el.dataset.projectId = p.id;
      el.innerHTML = `<span class="grip">&#9776;</span><span class="proj-name">${p.name}</span><span class="proj-acronym">${p.acronym}</span>`;
      list.appendChild(el);
    });
    if (list._sortable) list._sortable.destroy();
    list._sortable = new Sortable(list, { animation: 150, ghostClass: 'task-ghost' });
    if (label) label.style.display = projs.length > 0 ? '' : 'none';
  } else if (list) {
    list.innerHTML = '';
    if (label) label.style.display = 'none';
  }

  modal.style.display = 'flex';
}

function saveProject() {
  const id = document.getElementById('new-proj-id').value;
  const name = document.getElementById('new-proj-name').value.trim();
  const acronym = document.getElementById('new-proj-acronym').value.trim().toUpperCase();
  const cat = document.getElementById('new-proj-cat').value;
  const status = document.getElementById('new-proj-status').value;
  if (!name || !acronym) return;
  const method = id ? 'PATCH' : 'POST';
  const url = id ? `${API_BASE}/projects/${id}` : `${API_BASE}/projects`;
  const projectOrder = [...document.querySelectorAll('#proj-modal-projects .cat-modal-project')].map(el => el.dataset.projectId);
  fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, acronym, cat, status, projectOrder }) })
    .then(() => window.location.reload()).catch(err => console.warn('API:', err));
  document.getElementById('project-modal').style.display = 'none';
}

function deleteProject() {
  const id = document.getElementById('new-proj-id').value;
  if (!id) return;
  fetch(`${API_BASE}/projects/${id}`, { method: 'DELETE' })
    .then(() => window.location.reload()).catch(err => console.warn('API:', err));
  document.getElementById('project-modal').style.display = 'none';
}

// -- Task CRUD ---------------------------------------------------------------

function toggleDetail(el) {
  const wasDetail = el.classList.contains('detail-mode');
  document.querySelectorAll('.kanban-task.detail-mode').forEach(t => t.classList.remove('detail-mode'));
  if (!wasDetail) el.classList.add('detail-mode');
}

function openEditTask(id, title, desc, who, when, status) {
  _taskTargetList = null;
  document.getElementById('task-modal-heading').textContent = 'Editer t\u00e2che';
  document.getElementById('task-modal-title').value = title;
  document.getElementById('task-modal-desc').value = desc;
  document.getElementById('task-modal-who').value = who;
  document.getElementById('task-modal-when').value = when;
  document.getElementById('task-modal-status').value = status || 'todo';
  const delBtn = document.getElementById('task-modal-delete');
  if (delBtn) delBtn.style.display = id ? '' : 'none';
  document.getElementById('task-modal').style.display = 'flex';
}

let _taskTargetList = null;
function openTaskModal(taskList) {
  _taskTargetList = taskList;
  document.getElementById('task-modal-heading').textContent = 'Nouvelle t\u00e2che';
  document.getElementById('task-modal-title').value = '';
  document.getElementById('task-modal-desc').value = '';
  document.getElementById('task-modal-when').value = '';
  document.getElementById('task-modal-status').value = 'todo';
  const delBtn = document.getElementById('task-modal-delete');
  if (delBtn) delBtn.style.display = 'none';
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
  fetch(`${API_BASE}/tasks`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title, desc, who, when, status }) })
    .catch(err => console.warn('API:', err));
  if (_taskTargetList) {
    const card = document.createElement('div');
    card.className = 'kanban-task';
    card.innerHTML = `<div class="task-body"><div class="task-title">${title}</div>${desc ? `<div class="task-desc">${desc}</div>` : ''}</div>`;
    _taskTargetList.prepend(card);
  }
  document.getElementById('task-modal').style.display = 'none';
}

function deleteTask() {
  fetch(`${API_BASE}/tasks/0`, { method: 'DELETE' })
    .then(() => window.location.reload()).catch(err => console.warn('API:', err));
  document.getElementById('task-modal').style.display = 'none';
}

// -- Delete confirmation -----------------------------------------------------

let _deleteInterval = null;
function confirmDelete(btn, callback) {
  if (btn.dataset.confirmed === 'ready') { btn.dataset.confirmed = 'done'; callback(); return; }
  if (btn.dataset.confirmed) return;
  btn.dataset.confirmed = 'pending';
  let countdown = 2;
  btn.textContent = `Confirmer (${countdown})`;
  btn.style.background = 'color-mix(in srgb, var(--red) 15%, white)';
  _deleteInterval = setInterval(() => {
    countdown--;
    if (countdown > 0) { btn.textContent = `Confirmer (${countdown})`; }
    else { clearInterval(_deleteInterval); _deleteInterval = null; btn.textContent = 'Confirmer'; btn.dataset.confirmed = 'ready'; }
  }, 1000);
}

function resetDeleteBtns() {
  if (_deleteInterval) { clearInterval(_deleteInterval); _deleteInterval = null; }
  document.querySelectorAll('.btn-delete').forEach(btn => { btn.textContent = 'Supprimer'; btn.style.background = ''; delete btn.dataset.confirmed; });
}

document.querySelectorAll('.project-add-modal').forEach(modal => {
  const observer = new MutationObserver(() => { if (modal.style.display === 'none') resetDeleteBtns(); });
  observer.observe(modal, { attributes: true, attributeFilter: ['style'] });
});

// -- Drag & drop -------------------------------------------------------------

const catGrid = document.querySelector('.cat-grid');
if (catGrid) {
  new Sortable(catGrid, {
    animation: 150, draggable: '.cat-card:not(.cat-card-add)',
    ghostClass: 'task-ghost', chosenClass: 'task-chosen', filter: '.cat-card-add',
    onEnd: (evt) => {
      fetch(`${API_BASE}/categories/reorder`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ from: evt.oldIndex, to: evt.newIndex }) })
        .catch(err => console.warn('API:', err));
    }
  });
}

document.querySelectorAll('.kanban-col').forEach(col => {
  const tc = col.querySelector('.kanban-tasks');
  if (!tc) return;
  new Sortable(tc, {
    group: 'kanban', animation: 150, draggable: '.kanban-task',
    ghostClass: 'task-ghost', chosenClass: 'task-chosen', dragClass: 'task-drag',
    onEnd: (evt) => {
      const taskId = evt.item.dataset.taskId;
      const newStatus = evt.to.dataset.status;
      if (!taskId) return;
      fetch(`${API_BASE}/tasks/${taskId}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: newStatus, position: evt.newIndex }) })
        .catch(err => console.warn('API:', err));
    }
  });
});
