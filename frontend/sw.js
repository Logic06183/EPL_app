const CACHE = 'fpl-ai-v5';
const ASSETS = ['/', '/index.html', '/manifest.json', '/icon.svg'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // Network-only for API calls — bypass HTTP cache so backend changes propagate immediately
  if (url.pathname.startsWith('/api') || url.pathname === '/health') {
    const bypassed = new Request(e.request, { cache: 'no-store' });
    e.respondWith(
      fetch(bypassed).catch(() => new Response(
        JSON.stringify({ error: 'Offline — no cached data available', offline: true }),
        { status: 503, headers: { 'Content-Type': 'application/json' } }
      ))
    );
    return;
  }

  // Cache-first for Google Fonts (external)
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') {
    e.respondWith(
      caches.match(e.request).then(cached => cached || fetch(e.request).then(resp => {
        const clone = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return resp;
      }))
    );
    return;
  }

  // Only handle same-origin GETs from here on (PayFast, Firebase Auth etc. pass straight through)
  if (e.request.method !== 'GET' || url.origin !== self.location.origin) return;

  // Network-first for the app shell so a deploy reaches users on the next load;
  // fall back to the cached copy when offline.
  e.respondWith(
    fetch(e.request).then(resp => {
      if (resp.ok) {
        const clone = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
      }
      return resp;
    }).catch(() =>
      caches.match(e.request).then(cached =>
        cached || (e.request.mode === 'navigate' ? caches.match('/index.html') : Response.error())
      )
    )
  );
});
