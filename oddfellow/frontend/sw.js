const CACHE='oddfellow-synth-v020-v2';
const PRECACHE=['/','/manifest.json','/icons/icon-192.png','/icons/icon-512.png','/icons/apple-touch-icon.png'];

// What may be cached.
//
// An origin check alone is NOT enough. In the single-service deployment the API
// is served from this same origin, so a bare `url.origin !== self.location.origin`
// guard let GET /api/letta/status, /api/letta/agent and /api/letta/history be
// written into Cache Storage under a key derived from the URL only -- not from
// the X-Owner-Token. That meant:
//   * conversation history persisted in the cache indefinitely;
//   * any script running on this origin could read it with caches.match(),
//     with no token at all;
//   * on a network failure the fallback replayed a cached authenticated
//     response to a request that carried no token.
// So: never cache the API, never cache a credentialed request, and only ever
// cache a successful response.
function isCacheable(req, url){
  if(req.method!=='GET')return false;
  if(url.origin!==self.location.origin)return false;
  if(url.pathname.startsWith('/api/'))return false;
  if(req.headers.has('X-Owner-Token'))return false;
  return true;
}

self.addEventListener('install',e=>e.waitUntil(
  caches.open(CACHE).then(c=>c.addAll(PRECACHE)).then(()=>self.skipWaiting())
));

self.addEventListener('activate',e=>e.waitUntil(
  caches.keys()
    .then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))
    .then(()=>self.clients.claim())
));

self.addEventListener('fetch',e=>{
  const url=new URL(e.request.url);
  if(!isCacheable(e.request,url))return;          // API and third-party: straight to network
  e.respondWith(
    fetch(e.request).then(r=>{
      if(r&&r.ok&&r.type==='basic'){
        const copy=r.clone();
        caches.open(CACHE).then(c=>c.put(e.request,copy)).catch(()=>{});
      }
      return r;
    }).catch(()=>caches.match(e.request).then(m=>m||caches.match('/')))
  );
});
