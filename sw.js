const CACHE_NAME = 'osint-map-v1';
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

self.addEventListener('install', function(e) {
  e.waitUntil(
    caches.open(CACHE_NAME).then(function(c) {
      return Promise.all(SHELL.map(function(u) {
        return c.add(u).catch(function() {});
      }));
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function(e) {
  e.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(keys.filter(function(k) { return k !== CACHE_NAME; })
                             .map(function(k) { return caches.delete(k); }));
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', function(e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return;

  // Данные всегда из сети, без кеша
  if (/telegram-events\.js|supabase|raw\.githubusercontent|githack|deepstate|jsdelivr|unpkg|cdnjs/i.test(req.url)) {
    return;
  }

  e.respondWith(
    caches.match(req).then(function(hit) {
      return hit || fetch(req).then(function(res) {
        if (!res || res.status !== 200 || res.type === 'opaque') return res;
        var copy = res.clone();
        caches.open(CACHE_NAME).then(function(c) { c.put(req, copy); });
        return res;
      }).catch(function() {
        return caches.match('./index.html');
      });
    })
  );
});
