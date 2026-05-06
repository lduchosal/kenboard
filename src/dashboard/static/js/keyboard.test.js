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
