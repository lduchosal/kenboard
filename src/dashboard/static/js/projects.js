// Project CRUD modal: open / save / delete + the project-siblings subform.
// Also hosts ``copyOnboardLink`` (creates an onboarding token, copies the
// pre-filled onboard URL to the clipboard) since it lives next to project
// metadata in the UI.

import { API_BASE, apiCall } from './api.js';

function renderProjectSibling(p, currentId) {
  const el = document.createElement('div');
  el.className = `cat-modal-project${p.id === currentId ? ' current-project' : ''}`;
  el.dataset.projectId = p.id;
  el.innerHTML =
    '<span class="grip">&#9776;</span><span class="proj-name"></span><span class="proj-acronym"></span>';
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
  const projs = typeof CAT_PROJECTS === 'undefined' ? [] : CAT_PROJECTS[cat] || [];
  projs.forEach((p) => list.appendChild(renderProjectSibling(p, currentId)));
  if (list._sortable) list._sortable.destroy();
  list._sortable = new Sortable(list, { animation: 150, ghostClass: 'task-ghost' });
  if (label) label.style.display = projs.length > 0 ? '' : 'none';
}

export function editProject(id, name, acronym, cat, status, defaultWho) {
  const modal = document.getElementById('project-modal');
  if (!modal) return;
  document.getElementById('proj-modal-title').textContent = id
    ? 'Editer le projet'
    : 'Nouveau projet';
  document.querySelectorAll('#proj-modal-delete').forEach((b) => {
    b.style.display = id ? '' : 'none';
  });
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

export function saveProject() {
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
  const project_order = [
    ...document.querySelectorAll('#proj-modal-projects .cat-modal-project'),
  ].map((el) => el.dataset.projectId);
  apiCall(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name,
      acronym,
      cat,
      status,
      default_who: defaultWho,
      project_order,
    }),
  })
    .then(() => globalThis.location.reload())
    .catch(() => {});
  document.getElementById('project-modal').style.display = 'none';
}

export function deleteProject() {
  const id = document.getElementById('new-proj-id').value;
  if (!id) return;
  apiCall(`${API_BASE}/projects/${id}`, { method: 'DELETE' })
    .then(() => globalThis.location.reload())
    .catch(() => {});
  document.getElementById('project-modal').style.display = 'none';
}

// Create an onboarding token (or replace an existing one) via the API, then
// copy the full onboard URL (with token embedded) to clipboard. The agent
// can start immediately: pip install kenboard, create .ken, ken list (#159).
export async function copyOnboardLink(btn, catId, projectId) {
  const restore = btn.textContent;
  const flash = (label) => {
    btn.textContent = label;
    setTimeout(() => {
      btn.textContent = restore;
    }, 2500);
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
