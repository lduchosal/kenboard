// Unit tests for the task modal helpers. Focused on the small, testable
// pieces of behaviour that don't require a real DOM lifecycle — the rest
// is covered end-to-end by the Playwright suite under tests/e2e/.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { duplicateTask, openEditTask } from './tasks.js';

function buildTaskModal() {
  // Minimal DOM mirroring src/dashboard/templates/modals/task.html — just
  // the inputs touched by openEditTask / duplicateTask.
  document.body.innerHTML = `
    <div id="task-modal" style="display:none">
      <input id="task-modal-project-id" />
      <h3 id="task-modal-heading"></h3>
      <input id="task-modal-title" />
      <textarea id="task-modal-desc"></textarea>
      <input id="task-modal-when" />
      <select id="task-modal-status">
        <option value="todo">todo</option>
        <option value="doing">doing</option>
        <option value="review">review</option>
        <option value="done">done</option>
      </select>
      <select id="task-modal-who">
        <option value="Q">Q</option>
        <option value="Alice">Alice</option>
      </select>
      <button id="task-modal-delete"></button>
      <button id="task-modal-duplicate"></button>
    </div>
    <div id="error-modal" style="display:none">
      <div id="error-modal-title"></div>
      <div id="error-modal-body"></div>
    </div>
  `;
}

function makeFetchStub(getResponse, postResponse) {
  // Route fetch calls by method: GET → openEditTask's lazy-load,
  // POST → the duplicate / save path. Captures all calls so the test
  // can inspect what was sent.
  const calls = [];
  globalThis.fetch = vi.fn(async (url, opts = {}) => {
    calls.push({ url, opts });
    if ((opts.method || 'GET') === 'GET') {
      return new Response(JSON.stringify(getResponse), { status: 200 });
    }
    return new Response(JSON.stringify(postResponse), { status: 201 });
  });
  return calls;
}

beforeEach(() => {
  buildTaskModal();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('duplicateTask', () => {
  // #395: regardless of the original task's status (doing / review / done),
  // the duplicate must always be created in ``todo``. A copy is "new work
  // to schedule", not a re-instance of in-progress / completed work.
  it('always POSTs status="todo" even when the original is in "doing"', async () => {
    const calls = makeFetchStub(
      // openEditTask GET response: a task in "doing"
      {
        id: 42,
        title: 'Original',
        description: 'desc',
        who: 'Q',
        status: 'doing',
        due_date: null,
        project_id: 'proj-1',
      },
      // duplicate POST response: the server echoes back what was created
      { id: 43, title: 'Original - copy', status: 'todo' },
    );

    // Seed _taskEditId by going through openEditTask (its only public path).
    const card = document.createElement('div');
    card.className = 'kanban-task';
    const kanban = document.createElement('div');
    kanban.className = 'kanban';
    kanban.dataset.projectId = 'proj-1';
    const col = document.createElement('div');
    col.className = 'kanban-tasks';
    col.dataset.status = 'doing';
    col.appendChild(card);
    kanban.appendChild(col);
    document.body.appendChild(kanban);

    await openEditTask(card, 42);
    // Sanity: openEditTask reflected the original "doing" status in the modal.
    expect(document.getElementById('task-modal-status').value).toBe('doing');

    await duplicateTask();

    // The duplicate POST is the second fetch (first was the GET).
    const post = calls.find((c) => (c.opts.method || 'GET') === 'POST');
    expect(post).toBeDefined();
    const body = JSON.parse(post.opts.body);
    expect(body.status).toBe('todo');
    expect(body.title).toBe('Original - copy');

    // UI is also re-aligned to the forced status so the user doesn't see
    // a stale "doing" if they save again without opening the dropdown.
    expect(document.getElementById('task-modal-status').value).toBe('todo');
  });

  it('also forces todo when the original was in "done"', async () => {
    const calls = makeFetchStub(
      {
        id: 7,
        title: 'Closed',
        description: '',
        who: 'Q',
        status: 'done',
        due_date: null,
        project_id: 'proj-1',
      },
      { id: 8, title: 'Closed - copy', status: 'todo' },
    );

    const card = document.createElement('div');
    card.className = 'kanban-task';
    const kanban = document.createElement('div');
    kanban.className = 'kanban';
    kanban.dataset.projectId = 'proj-1';
    const col = document.createElement('div');
    col.className = 'kanban-tasks';
    col.dataset.status = 'done';
    col.appendChild(card);
    kanban.appendChild(col);
    document.body.appendChild(kanban);

    await openEditTask(card, 7);
    await duplicateTask();

    const post = calls.find((c) => (c.opts.method || 'GET') === 'POST');
    expect(JSON.parse(post.opts.body).status).toBe('todo');
  });
});
