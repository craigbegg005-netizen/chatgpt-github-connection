'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const dist = path.join(__dirname, '..', 'dist');
const currentOrigin = 'https://seven-day-reset-planner.craigbegg005.chatgpt.site';
const retiredOrigin = 'https://seven-day-reset-planner.tangy-gnome-9963.chatgpt.site';
const files = {
  index: fs.readFileSync(path.join(dist, 'index.html'), 'utf8'),
  robots: fs.readFileSync(path.join(dist, 'robots.txt'), 'utf8'),
  sitemap: fs.readFileSync(path.join(dist, 'sitemap.xml'), 'utf8'),
};

assert.match(
  files.index,
  new RegExp(`<link rel="canonical" href="${currentOrigin.replaceAll('.', '\\.')}/">`),
  'index.html must declare the current live origin as canonical',
);
assert.match(
  files.robots,
  new RegExp(`^Sitemap: ${currentOrigin.replaceAll('.', '\\.')}\/sitemap\\.xml$`, 'm'),
  'robots.txt must advertise the current live sitemap',
);
assert.match(
  files.sitemap,
  new RegExp(`<loc>${currentOrigin.replaceAll('.', '\\.')}/<\/loc>`),
  'sitemap.xml must list the current live root URL',
);

for (const [name, contents] of Object.entries(files)) {
  assert.equal(contents.includes(retiredOrigin), false, `${name} must not retain the retired origin`);
}

console.log('URL regression: passed');
