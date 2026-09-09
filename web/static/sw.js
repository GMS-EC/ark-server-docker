// Service Worker para ARK Server Manager (PWA)
const CACHE_NAME = 'ark-manager-cache-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/style.css?v=1.0.0',
  '/static/js/app.js?v=1.0.0',
  '/static/js/files.js?v=1.0.0',
  '/static/img/logo.png',
  '/static/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch(() => {});
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Estrategia Network-First para APIs y dinámicos, con fallback a cache
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  // No cachear llamadas API ni websockets
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws') || event.request.method !== 'GET') {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
