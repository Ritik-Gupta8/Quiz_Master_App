const CACHE_NAME = 'quiz-master-cache-v5'; // 🔥 bump version
const OFFLINE_URL = '/static/offline.html';

// Only cache STATIC assets (never HTML pages)
const STATIC_ASSETS = [
  OFFLINE_URL,
  '/static/styles/main.css',
  '/static/images/logo-192.png',
  '/static/images/logo-512.png',
  'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap'
];

// 🚫 Routes we NEVER touch (auth + dynamic)
const PROTECTED_ROUTES = [
  '/admin',
  '/user',
  '/login',
  '/logout',
  '/api'
];

// INSTALL
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// ACTIVATE
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(names =>
      Promise.all(
        names.map(name => {
          if (name !== CACHE_NAME) {
            return caches.delete(name);
          }
        })
      )
    )
  );
  self.clients.claim();
});

// FETCH (🔥 critical logic)
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // 🚫 DO NOT INTERCEPT protected routes
  if (
    PROTECTED_ROUTES.some(route => url.pathname.startsWith(route))
  ) {
    return;
  }

  // 🚫 DO NOT INTERCEPT homepage (can be user-specific)
  if (event.request.mode === 'navigate') {
    return; // ❌ DO NOT TOUCH ANY HTML NAVIGATION EVER
  }

  // ✅ Navigation fallback ONLY for public pages
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  // ✅ Static asset caching (safe)
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});