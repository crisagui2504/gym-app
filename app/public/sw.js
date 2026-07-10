/* Service worker de GymTracker.
   - Navegacion (index.html): red primero, cache si no hay conexion.
   - Estaticos del mismo origen: cache primero con actualizacion en segundo plano.
   - /api/ y otros origenes (fuentes): nunca se cachean aqui. */
const CACHE = 'gymtracker-v1';

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // fuentes de Google, etc.
  if (url.pathname.includes('/api/')) return; // datos: siempre a la red

  if (req.mode === 'navigate') {
    // index.html: red primero para no servir un shell viejo
    event.respondWith(
      fetch(req)
        .then((resp) => {
          const copia = resp.clone();
          caches.open(CACHE).then((c) => c.put(req, copia));
          return resp;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // JS/CSS/iconos: cache primero, refresco en segundo plano
  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const cacheado = await cache.match(req);
      const red = fetch(req)
        .then((resp) => {
          if (resp.ok) cache.put(req, resp.clone());
          return resp;
        })
        .catch(() => cacheado);
      return cacheado || red;
    })
  );
});
