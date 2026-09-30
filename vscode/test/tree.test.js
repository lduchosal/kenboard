const test = require('node:test');
const assert = require('node:assert/strict');
const { groupByStatus, taskLabel } = require('../src/tree');

const t = (id, status, position) => ({ id, status, position, title: `t${id}`, who: '' });

test('groupByStatus: todo/doing/review only, sorted by position then id', () => {
  const groups = groupByStatus([
    t(3, 'todo', 1),
    t(1, 'todo', 0),
    t(2, 'done', 0),
    t(4, 'review', 0),
    t(5, 'todo', 1),
  ]);
  assert.deepEqual([...groups.keys()], ['todo', 'doing', 'review']);
  assert.deepEqual(
    groups.get('todo').map((x) => x.id),
    [1, 3, 5],
  );
  assert.deepEqual(groups.get('doing'), []);
  assert.deepEqual(
    groups.get('review').map((x) => x.id),
    [4],
  );
});

test('taskLabel', () => {
  assert.equal(taskLabel(t(9, 'todo', 0)), '#9 t9');
});
