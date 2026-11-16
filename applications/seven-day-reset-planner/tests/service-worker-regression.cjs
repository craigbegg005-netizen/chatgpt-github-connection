'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ORIGIN = 'https://planner.example';
const source = fs.readFileSync(path.join(__dirname, '..', 'dist', 'sw.js'), 'utf8');

function response(url, options = {}) {
  return {
    url,
    ok: options.ok ?? true,
    type: options.type ?? 'basic',
    redirected: options.redirected ?? false,
    marker: options.marker,
    clone() {
      return { ...this, cloned: true };
    },
  };
}

function request(url, options = {}) {
  return {
    url: new URL(url, ORIGIN).href,
    method: options.method ?? 'GET',
    mode: options.mode ?? 'same-origin',
  };
}

function createHarness() {
  const listeners = {};
  const calls = {
    addAll: [],
    cacheDelete: [],
    cacheMatch: [],
    cacheOpen: [],
    cachePut: [],
    claim: 0,
    fetch: [],
    match: [],
    skipWaiting: 0,
  };
  const cacheMatches = new Map();
  const matches = new Map();
  let fetchImpl = async req => response(req.url);

  const cache = {
    addAll(files) {
      calls.addAll.push([...files]);
      return Promise.resolve();
    },
    put(req, value) {
      calls.cachePut.push({ request: req, response: value });
      return Promise.resolve();
    },
    match(req) {
      const key = typeof req === 'string' ? req : req.url;
      calls.cacheMatch.push(key);
      return Promise.resolve(cacheMatches.get(key));
    },
  };
  const caches = {
    open(name) {
      calls.cacheOpen.push(name);
      return Promise.resolve(cache);
    },
    keys() {
      return Promise.resolve(['reset-planner-v1', 'reset-planner-v2', 'reset-planner-v3', 'other-app-v1']);
    },
    delete(name) {
      calls.cacheDelete.push(name);
      return Promise.resolve(true);
    },
    match(req) {
      const key = typeof req === 'string' ? req : req.url;
      calls.match.push(key);
      return Promise.resolve(matches.get(key));
    },
  };
  const self = {
    location: { origin: ORIGIN },
    clients: {
      claim() {
        calls.claim += 1;
        return Promise.resolve();
      },
    },
    addEventListener(type, handler) {
      listeners[type] = handler;
    },
    skipWaiting() {
      calls.skipWaiting += 1;
      return Promise.resolve();
    },
  };
  vm.runInNewContext(source, {
    URL,
    caches,
    fetch(req) {
      calls.fetch.push(req);
      return fetchImpl(req);
    },
    self,
  }, { filename: 'dist/sw.js' });

  function lifecycleEvent() {
    const waits = [];
    return {
      waits,
      waitUntil(promise) {
        waits.push(Promise.resolve(promise));
      },
    };
  }

  function fetchEvent(req) {
    const waits = [];
    let responsePromise;
    return {
      request: req,
      waits,
      get responsePromise() {
        return responsePromise;
      },
      respondWith(promise) {
        assert.equal(responsePromise, undefined, 'respondWith called more than once');
        responsePromise = Promise.resolve(promise);
      },
      waitUntil(promise) {
        waits.push(Promise.resolve(promise));
      },
    };
  }

  return {
    calls,
    cacheMatches,
    fetchEvent,
    lifecycleEvent,
    listeners,
    matches,
    setFetch(fn) {
      fetchImpl = fn;
    },
  };
}

async function settle(event) {
  if (event.responsePromise) await event.responsePromise;
  await Promise.all(event.waits);
}

async function main() {
  const h = createHarness();

  const install = h.lifecycleEvent();
  h.listeners.install(install);
  await Promise.all(install.waits);
  assert.equal(h.calls.skipWaiting, 1);
  assert.deepEqual(h.calls.addAll, [[
    '/',
    '/index.html',
    '/manifest.webmanifest',
    '/planner-model.js',
    '/daily-planner.js',
    '/icon.svg',
    '/icon-192.png',
    '/icon-512.png',
  ]]);

  const activate = h.lifecycleEvent();
  h.listeners.activate(activate);
  await Promise.all(activate.waits);
  assert.deepEqual(h.calls.cacheDelete, ['reset-planner-v1', 'reset-planner-v2', 'reset-planner-v3']);
  assert.equal(h.calls.claim, 1);

  for (const req of [
    request('/api/save', { method: 'POST' }),
    request('https://cdn.example/icon.png'),
    request('/private-data.json'),
    request('/icon-192.png?v=1'),
    request('/account', { mode: 'navigate' }),
    request('/api/private', { mode: 'navigate' }),
    request('/?preview=1', { mode: 'navigate' }),
  ]) {
    const event = h.fetchEvent(req);
    h.listeners.fetch(event);
    assert.equal(event.responsePromise, undefined, `${req.url} should bypass the worker`);
  }

  h.setFetch(async req => response(req.url, { marker: 'network-shell' }));
  const shell = h.fetchEvent(request('/icon-192.png'));
  h.listeners.fetch(shell);
  assert.equal((await shell.responsePromise).marker, 'network-shell');
  await Promise.all(shell.waits);
  assert.equal(h.calls.cachePut.length, 1);
  assert.equal(h.calls.cachePut[0].request.url, `${ORIGIN}/icon-192.png`);
  assert.equal(h.calls.cachePut[0].response.cloned, true);

  const unsafeCases = [
    response(`${ORIGIN}/icon-512.png`, { ok: false }),
    response(`${ORIGIN}/icon-512.png`, { type: 'opaque' }),
    response(`${ORIGIN}/icon-512.png`, { redirected: true }),
    response('https://redirected.example/icon-512.png'),
    response(''),
  ];
  for (const unsafe of unsafeCases) {
    h.setFetch(async () => unsafe);
    const event = h.fetchEvent(request('/icon-512.png'));
    h.listeners.fetch(event);
    await settle(event);
  }
  assert.equal(h.calls.cachePut.length, 1, 'unsafe responses must not be cached');

  const cachedShell = response(`${ORIGIN}/icon.svg`, { marker: 'cached-shell' });
  h.cacheMatches.set(`${ORIGIN}/icon.svg`, cachedShell);
  h.setFetch(async () => { throw new Error('offline'); });
  const offlineShell = h.fetchEvent(request('/icon.svg'));
  h.listeners.fetch(offlineShell);
  assert.equal((await offlineShell.responsePromise).marker, 'cached-shell');

  const cachedIndex = response(`${ORIGIN}/index.html`, { marker: 'cached-index' });
  h.matches.set(`${ORIGIN}/`, response(`${ORIGIN}/`, { marker: 'unrelated-root' }));
  h.matches.set('/index.html', response(`${ORIGIN}/index.html`, { marker: 'unrelated-index' }));
  const unrelatedOnlyNavigation = h.fetchEvent(request('/', { mode: 'navigate' }));
  h.listeners.fetch(unrelatedOnlyNavigation);
  await assert.rejects(unrelatedOnlyNavigation.responsePromise, /offline/);
  assert.deepEqual(h.calls.match, [], 'global cache storage must never be searched');

  h.cacheMatches.set('/index.html', cachedIndex);
  const offlineNavigation = h.fetchEvent(request('/', { mode: 'navigate' }));
  h.listeners.fetch(offlineNavigation);
  assert.equal((await offlineNavigation.responsePromise).marker, 'cached-index');

  h.setFetch(async req => response(req.url, { marker: 'network-navigation' }));
  const onlineNavigation = h.fetchEvent(request('/', { mode: 'navigate' }));
  h.listeners.fetch(onlineNavigation);
  assert.equal((await onlineNavigation.responsePromise).marker, 'network-navigation');
  await Promise.all(onlineNavigation.waits);
  assert.equal(h.calls.cachePut.length, 2, 'the explicit root shell may be refreshed');

  console.log('service-worker regression: passed');
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
