const CACHE_NAME = 'osint-map-v2';
const SHELL = [
  './',
  './index.html',
  './icon.svg',
  './manifest.json',
  './lib/leaflet.css',
  './lib/leaflet.js',
  './lib/leaflet-draw.css',
  './lib/leaflet-draw.js',
  './lib/markercluster.css',
  './lib/markercluster.default.css',
  './lib/markercluster.js',
  './lib/leaflet.polylineDecorator.js'
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return Promise.all(SHELL.map(function (url) {
        return cache.add(url).catch(function () {});
      }));
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      // Удаляем только старые кэши этого приложения, не затрагивая другие приложения origin.
      return Promise.all(
        keys.filter(function (key) {
          return key.indexOf('osint-map-') === 0 && key !== CACHE_NAME;
        }).map(function (key) {
          return caches.delete(key);
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', function (event) {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return;
  // Не перехватываем запросы к сторонним сервисам и API.
  if (url.origin !== self.location.origin) return;
  // Данные должны обновляться из сети, а не застревать в cache-first кэше.
  if (/\/data\/(?:telegram-events\.js|firms-fires\.json)$/.test(url.pathname)) return;

  const isNavigation = request.mode === 'navigate' || /\/index\.html$/.test(url.pathname);
  if (isNavigation) {
    // Онлайн — всегда свежая страница; офлайн — последняя сохранённая версия.
    event.respondWith(
      fetch(request).then(function (response) {
        if (response && response.ok && response.type !== 'opaque') {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(function (cache) {
            return cache.put(request, copy);
          }).catch(function () {});
        }
        return response;
      }).catch(function () {
        return caches.match(request).then(function (cached) {
          return cached || caches.match('./index.html');
        });
      })
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(function (cached) {
      if (cached) return cached;
      return fetch(request).then(function (response) {
        if (!response || !response.ok || response.type === 'opaque') return response;
        const copy = response.clone();
        caches.open(CACHE_NAME).then(function (cache) {
          return cache.put(request, copy);
        }).catch(function () {});
        return response;
      });
    })
  );
});
