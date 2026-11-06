'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'dist', 'index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script, 'Planner inline script must exist');

const listeners = {};
const statusMutations = [];
let statusText = 'Saved on this device';
const status = {
  get textContent() {
    return statusText;
  },
  set textContent(value) {
    statusText = value;
    statusMutations.push(value);
  },
};
const heading = {
  focusCount: 0,
  focus() {
    this.focusCount += 1;
  },
};
const elements = {
  days: { innerHTML: '' },
  page: {
    innerHTML: '',
    querySelector(selector) {
      assert.equal(selector, '#planner-page-heading');
      return heading;
    },
  },
  progress: { textContent: '' },
  status,
};
let failSave = false;
let storedRaw = null;
const savedValues = [];
const document = {
  addEventListener(type, handler) {
    listeners[type] = handler;
  },
  getElementById(id) {
    return elements[id];
  },
};
const localStorage = {
  getItem() {
    return storedRaw;
  },
  setItem(key, value) {
    if (failSave) throw new Error('storage unavailable');
    savedValues.push({ key, value });
    storedRaw = value;
  },
};
const window = {
  addEventListener() {},
  print() {},
  scrollTo() {},
};

vm.runInNewContext(script, {
  console,
  document,
  localStorage,
  navigator: {},
  queueMicrotask(callback) {
    callback();
  },
  window,
}, {
  filename: 'dist/index.html',
});

assert.match(
  elements.page.innerHTML,
  /id="status" role="status" aria-live="polite" aria-atomic="true"/,
  'Save and error feedback must be exposed as an atomic polite status',
);
assert.equal(
  (elements.days.innerHTML.match(/aria-current="page"/g) || []).length,
  1,
  'Exactly one planner navigation button must be current',
);
assert.match(
  elements.days.innerHTML,
  /<button data-day="0" class="active" aria-current="page">Start here<\/button>/,
  'Start page must initially be programmatically current',
);
assert.equal(heading.focusCount, 0, 'Initial render must not steal focus');

listeners.click({
  target: {
    id: '',
    closest() {
      return { dataset: { day: '2' } };
    },
  },
});
assert.match(
  elements.days.innerHTML,
  /<button data-day="2" class="active" aria-current="page">Day 2 · Reconnect with yourself<\/button>/,
  'Selected day must become programmatically current',
);
assert.equal(
  (elements.days.innerHTML.match(/aria-current="page"/g) || []).length,
  1,
  'Changing pages must leave exactly one current navigation button',
);
assert.match(
  elements.page.innerHTML,
  /<h2 id="planner-page-heading" tabindex="-1">Reconnect with yourself<\/h2>/,
  'Rendered page heading must accept programmatic focus',
);
assert.equal(heading.focusCount, 1, 'Day navigation must move focus to the new page heading');

listeners.click({
  target: {
    id: 'next',
    closest() {
      return null;
    },
  },
});
assert.equal(heading.focusCount, 2, 'Next-page navigation must move focus to the new heading');

listeners.input({
  target: { dataset: { key: 'week_intention' }, type: 'textarea', value: 'Make space' },
});
assert.equal(status.textContent, 'Saved on this device');
assert.deepEqual(
  statusMutations.slice(-2),
  ['', 'Saved on this device'],
  'Every successful text save must create a real live-region transition',
);
assert.equal(savedValues.length, 1, 'Text entry must persist once');

listeners.change({
  target: { dataset: { key: 'd3_habit_water' }, type: 'checkbox', checked: true },
});
assert.equal(status.textContent, 'Saved on this device');
assert.deepEqual(
  statusMutations.slice(-2),
  ['', 'Saved on this device'],
  'Every successful checkbox save must create a real live-region transition',
);
assert.equal(savedValues.length, 2, 'Checkbox entry must persist once');

failSave = true;
listeners.input({
  target: { dataset: { key: 'week_release' }, type: 'textarea', value: 'Clutter' },
});
assert.equal(
  status.textContent,
  'Could not save here; print a copy',
  'Storage failures must update the announced status',
);
assert.deepEqual(
  statusMutations.slice(-2),
  ['', 'Could not save here; print a copy'],
  'Storage failures must also create a real live-region transition',
);

console.log('accessibility regression: passed');
