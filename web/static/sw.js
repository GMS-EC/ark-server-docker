// Service Worker para ARK Server Manager (PWA) - Sincronizado con CHANGELOG.md via ?v=
const SW_VERSION = new URL(self.location.href).searchParams.get('v') || 'app';
const CACHE_NAME = `ark-manager-cache-v${SW_VERSION}`;

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

// Network-only para APIs, WebSockets y activos dinámicos con query string
self.addEventListener('fetch', (event) => {
  // Dejar pasar directamente todas las peticiones a la red para que no se congele el código
  return;
});
