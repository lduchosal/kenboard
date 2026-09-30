// @ts-check
// Pure grouping logic for the sidebar tree — no `vscode` import.

const TREE_STATUSES = ['todo', 'doing', 'review'];
const ALL_STATUSES = ['todo', 'doing', 'review', 'done'];

/**
 * Group tasks by the statuses shown in the tree, keeping board order.
 * @param {import('./api').Task[]} tasks
 * @returns {Map<string, import('./api').Task[]>}
 */
function groupByStatus(tasks) {
  /** @type {Map<string, import('./api').Task[]>} */
  const groups = new Map(TREE_STATUSES.map((s) => [s, []]));
  for (const task of tasks) groups.get(task.status)?.push(task);
  for (const list of groups.values()) list.sort((a, b) => a.position - b.position || a.id - b.id);
  return groups;
}

/**
 * @param {import('./api').Task} task
 * @returns {string}
 */
function taskLabel(task) {
  return `#${task.id} ${task.title}`;
}

module.exports = { TREE_STATUSES, ALL_STATUSES, groupByStatus, taskLabel };
