const CACHE_PREFIX = 'reset-planner-';
const CACHE = `${CACHE_PREFIX}v5`;
const INDEX = '/index.html';
const APP_SHELL = [
  '/',
  INDEX,
  '/manifest.webmanifest',
  '/planner-model.js',
  '/daily-planner.js',
  '/icon.svg',
  '/icon-192.png',
  '/icon-512.png',
];
const APP_SHELL_PATHS = new Set(APP_SHELL);

self.addEventListener('install', event => {
  event.waitUntil(Promise.all([
    caches.open(CACHE).then(cache => cache.addAll(APP_SHELL)),
    self.skipWaiting(),
  ]));
});

self.addEventListener('activate', event => {
  const removeOldPlannerCaches =
    caches.keys().then(keys => Promise.all(
      keys
        .filter(key => key.startsWith(CACHE_PREFIX) && key !== CACHE)
        .map(key => caches.delete(key)),
    ));
  event.waitUntil(Promise.all([removeOldPlannerCaches, self.clients.claim()]));
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const requestUrl = new URL(request.url);
  if (requestUrl.origin !== self.location.origin) return;

  const isAppShell = requestUrl.search === '' && APP_SHELL_PATHS.has(requestUrl.pathname);
  const isAppNavigation = request.mode === 'navigate'
    && requestUrl.search === ''
    && (requestUrl.pathname === '/' || requestUrl.pathname === INDEX);
  if (!isAppShell && !isAppNavigation) return;

  event.respondWith(
    fetch(request)
      .then(response => {
        let responseOrigin = '';
        try {
          responseOrigin = new URL(response.url).origin;
        } catch {
          // Responses without a trustworthy final URL are never cached.
        }
        const cacheable = isAppShell
          && response.ok
          && response.type === 'basic'
          && !response.redirected
          && responseOrigin === self.location.origin;

        if (!cacheable) return response;
        return caches.open(CACHE)
          .then(cache => cache.put(request, response.clone()))
          .catch(() => undefined)
          .then(() => response);
      })
      .catch(error => caches.open(CACHE).then(cache =>
        cache.match(request).then(cached => {
          if (cached) return cached;
          if (!isAppNavigation) throw error;
          return cache.match(INDEX).then(index => {
            if (index) return index;
            throw error;
          });
        }),
      )),
  );
});
