// Category CRUD modal: open / save / delete + the project-order subform.

import { API_BASE, apiCall } from './api.js';

export function editCat(id, name, color) {
  const modal = document.getElementById('cat-modal');
  if (!modal) return;
  document.getElementById('cat-modal-id').value = id;
  document.getElementById('cat-modal-name').value = name;
  document.querySelector('#cat-modal h3').textContent = id
    ? 'Editer la catégorie'
    : 'Nouvelle catégorie';
  const delBtn = document.getElementById('cat-modal-delete');
  if (delBtn) delBtn.style.display = id ? '' : 'none';
  // Mark the matching dot as selected. For a brand-new category (no color
  // passed) we fall back to the first dot so the form always has a valid
  // pick — the server validator (#56) refuses empty colors.
  const colors = document.getElementById('cat-modal-colors');
  if (colors) {
    const dots = colors.querySelectorAll('.color-dot');
    let any = false;
    dots.forEach((d) => {
      const match = d.dataset.color === color;
      d.classList.toggle('selected', match);
      if (match) any = true;
    });
    if (!any && dots.length > 0) dots[0].classList.add('selected');
  }
  const list = document.getElementById('cat-modal-projects');
  if (list) {
    list.innerHTML = '';
    const projs = typeof CAT_PROJECTS !== 'undefined' && id ? CAT_PROJECTS[id] || [] : [];
    projs.forEach((p) => {
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

export function selectCatColor(dot) {
  const container = document.getElementById('cat-modal-colors');
  container.querySelectorAll('.color-dot').forEach((d) => d.classList.remove('selected'));
  dot.classList.add('selected');
}

export function saveCat() {
  const id = document.getElementById('cat-modal-id').value;
  const name = document.getElementById('cat-modal-name').value.trim();
  const selected = document.querySelector('#cat-modal-colors .color-dot.selected');
  const color = selected ? selected.dataset.color : '';
  if (!name) return;
  // Field name MUST match the Pydantic schema (snake_case). Sending camelCase
  // ``projectOrder`` here would silently drop the reorder because Pydantic v2
  // ignores unknown fields by default (#71).
  const project_order = [
    ...document.querySelectorAll('#cat-modal-projects .cat-modal-project'),
  ].map((el) => el.dataset.projectId);
  const method = id ? 'PATCH' : 'POST';
  const url = id ? `${API_BASE}/categories/${id}` : `${API_BASE}/categories`;
  apiCall(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, color, project_order }),
  })
    .then(() => globalThis.location.reload())
    .catch(() => {});
  document.getElementById('cat-modal').style.display = 'none';
}

export function deleteCat() {
  const id = document.getElementById('cat-modal-id').value;
  if (!id) return;
  apiCall(`${API_BASE}/categories/${id}`, { method: 'DELETE' })
    .then(() => globalThis.location.reload())
    .catch(() => {});
  document.getElementById('cat-modal').style.display = 'none';
}

export function addProjectInCatModal() {
  const list = document.getElementById('cat-modal-projects');
  const el = document.createElement('div');
  el.className = 'cat-modal-project';
  el.dataset.projectId = '';
  el.innerHTML =
    '<span class="grip">&#9776;</span>' +
    '<input type="text" class="proj-name-input" placeholder="Nom du projet" style="flex:1;border:1px solid var(--border);border-radius:3px;padding:2px 6px;font-size:12px;font-family:inherit">' +
    '<input type="text" class="proj-acr-input" placeholder="ACRO" maxlength="4" style="width:50px;border:1px solid var(--border);border-radius:3px;padding:2px 6px;font-size:10px;font-family:inherit;text-transform:uppercase">' +
    '<span class="proj-remove" onclick="this.parentElement.remove()" title="Supprimer">&times;</span>';
  list.appendChild(el);
  el.querySelector('.proj-name-input').focus();
}
