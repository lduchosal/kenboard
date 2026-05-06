// Unit tests for the keyboard navigation logic. We exercise the pure
// selection helpers (moveVertical / moveHorizontal) against a small jsdom
// kanban so the behaviour is locked in without spinning up Playwright.

import { beforeEach, describe, expect, it } from 'vitest';
import { moveHorizontal, moveVertical, selectCard, selectedCard } from './keyboard.js';

function buildKanban(columns) {
  // ``columns`` is a list of lists of task ids: ``[['a','b'],['c'],[]]`` →
  // 3 columns with the matching cards.
  document.body.innerHTML = '';
  const kanban = document.createElement('div');
  kanban.className = 'kanban';
  columns.forEach((ids, idx) => {
    const col = document.createElement('div');
    col.className = 'kanban-tasks';
    col.dataset.status = `col${idx}`;
    ids.forEach((id) => {
      const card = document.createElement('div');
      card.className = 'kanban-task';
      card.dataset.taskId = id;
      col.appendChild(card);
    });
    kanban.appendChild(col);
  });
  document.body.appendChild(kanban);
  return kanban;
}

function selectedId() {
  const c = selectedCard();
  return c ? c.dataset.taskId : null;
}

beforeEach(() => {
  // Each test gets a fresh DOM so selection state doesn't leak.
  document.body.innerHTML = '';
  // jsdom doesn't implement scrollIntoView; stub so selectCard's internal
  // calls (which default to scroll:true) don't throw.
  Element.prototype.scrollIntoView = () => {};
});

describe('selection model', () => {
  it('only one card carries data-kb-selected at a time', () => {
    buildKanban([['a', 'b']]);
    selectCard(document.querySelector('[data-task-id="a"]'), { scroll: false });
    selectCard(document.querySelector('[data-task-id="b"]'), { scroll: false });
    expect(document.querySelectorAll('[data-kb-selected="true"]')).toHaveLength(1);
    expect(selectedId()).toBe('b');
  });
});

describe('moveVertical', () => {
  it('moves selection down within a column', () => {
    buildKanban([['a', 'b', 'c']]);
    selectCard(document.querySelector('[data-task-id="a"]'), { scroll: false });
    moveVertical(1);
    expect(selectedId()).toBe('b');
    moveVertical(1);
    expect(selectedId()).toBe('c');
  });

  it('clamps at the bottom (no wrap)', () => {
    buildKanban([['a', 'b']]);
    selectCard(document.querySelector('[data-task-id="b"]'), { scroll: false });
    moveVertical(1);
    expect(selectedId()).toBe('b');
  });

  it('clamps at the top (no wrap)', () => {
    buildKanban([['a', 'b']]);
    selectCard(document.querySelector('[data-task-id="a"]'), { scroll: false });
    moveVertical(-1);
    expect(selectedId()).toBe('a');
  });

  it('selects the first card when nothing is selected', () => {
    buildKanban([['a', 'b']]);
    moveVertical(1);
    expect(selectedId()).toBe('a');
  });
});

describe('moveHorizontal', () => {
  it('jumps to the adjacent column at the same position', () => {
    buildKanban([
      ['a', 'b', 'c'],
      ['d', 'e', 'f'],
    ]);
    selectCard(document.querySelector('[data-task-id="b"]'), { scroll: false });
    moveHorizontal(1);
    expect(selectedId()).toBe('e');
  });

  it('clamps to the last available card when target column is shorter', () => {
    buildKanban([['a', 'b', 'c'], ['d']]);
    selectCard(document.querySelector('[data-task-id="c"]'), { scroll: false });
    moveHorizontal(1);
    expect(selectedId()).toBe('d');
  });

  it('skips empty columns and lands on the next non-empty one', () => {
    buildKanban([['a'], [], [], ['z']]);
    selectCard(document.querySelector('[data-task-id="a"]'), { scroll: false });
    moveHorizontal(1);
    expect(selectedId()).toBe('z');
  });

  it('stays put when no further non-empty column exists in the direction', () => {
    buildKanban([['a'], []]);
    selectCard(document.querySelector('[data-task-id="a"]'), { scroll: false });
    moveHorizontal(1);
    expect(selectedId()).toBe('a');
  });

  it('clamps at the leftmost column', () => {
    buildKanban([['a'], ['b']]);
    selectCard(document.querySelector('[data-task-id="a"]'), { scroll: false });
    moveHorizontal(-1);
    expect(selectedId()).toBe('a');
  });
});

// -- #253: spill-over to adjacent kanbans + flat home-page nav -------------

function buildKanbans(boards) {
  // Two-level: ``[[['a','b']], [['c']]]`` → kanban1 (1 col, 2 cards),
  // kanban2 (1 col, 1 card).
  document.body.innerHTML = '';
  boards.forEach((cols, bi) => {
    const k = document.createElement('div');
    k.className = 'kanban';
    k.dataset.projectId = `proj${bi}`;
    cols.forEach((ids, ci) => {
      const col = document.createElement('div');
      col.className = 'kanban-tasks';
      col.dataset.status = `col${ci}`;
      ids.forEach((id) => {
        const card = document.createElement('div');
        card.className = 'kanban-task';
        card.dataset.taskId = id;
        col.appendChild(card);
      });
      k.appendChild(col);
    });
    document.body.appendChild(k);
  });
}

describe('moveVertical across kanbans (#253)', () => {
  it('spills from the bottom of one board to the top of the next', () => {
    buildKanbans([[['a', 'b']], [['c', 'd']]]);
    selectCard(document.querySelector('[data-task-id="b"]'), { scroll: false });
    moveVertical(1);
    expect(selectedId()).toBe('c');
  });

  it('spills from the top of one board to the bottom of the previous', () => {
    buildKanbans([[['a', 'b']], [['c', 'd']]]);
    selectCard(document.querySelector('[data-task-id="c"]'), { scroll: false });
    moveVertical(-1);
    expect(selectedId()).toBe('b');
  });

  it('clamps at the very bottom of the last board', () => {
    buildKanbans([[['a']], [['b']]]);
    selectCard(document.querySelector('[data-task-id="b"]'), { scroll: false });
    moveVertical(1);
    expect(selectedId()).toBe('b');
  });
});

function buildHomeTiles(ids) {
  document.body.innerHTML = '';
  ids.forEach((id) => {
    const a = document.createElement('a');
    a.dataset.kbNav = '';
    a.dataset.id = id; // for the test, not read by the keyboard module
    a.textContent = id;
    document.body.appendChild(a);
  });
}

function selectedTileId() {
  const el = document.querySelector('[data-kb-selected="true"]');
  return el ? el.dataset.id : null;
}

describe('flat nav for home-page tiles (#253)', () => {
  it('moves between tiles with ↓', () => {
    buildHomeTiles(['x', 'y', 'z']);
    selectCard(document.querySelector('[data-id="x"]'), { scroll: false });
    moveVertical(1);
    expect(selectedTileId()).toBe('y');
    moveVertical(1);
    expect(selectedTileId()).toBe('z');
  });

  it('clamps at the last tile', () => {
    buildHomeTiles(['x', 'y']);
    selectCard(document.querySelector('[data-id="y"]'), { scroll: false });
    moveVertical(1);
    expect(selectedTileId()).toBe('y');
  });

  it('selects the first tile when nothing is selected', () => {
    buildHomeTiles(['x', 'y']);
    moveVertical(1);
    expect(selectedTileId()).toBe('x');
  });

  it('also navigates with ←/→', () => {
    buildHomeTiles(['x', 'y', 'z']);
    selectCard(document.querySelector('[data-id="x"]'), { scroll: false });
    moveHorizontal(1);
    expect(selectedTileId()).toBe('y');
    moveHorizontal(-1);
    expect(selectedTileId()).toBe('x');
  });
});
