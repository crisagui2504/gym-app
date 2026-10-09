/* Service worker de GymTracker.
   - Navegacion (index.html): red primero, cache si no hay conexion.
   - Estaticos del mismo origen: cache primero con actualizacion en segundo plano.
   - /api/ y otros origenes (fuentes): nunca se cachean aqui. */
// Cambiar el nombre hace que el activate borre la cache anterior (icono,
// manifiesto y bundles viejos) en el telefono. v4: avisos push + encuesta.
const CACHE = 'gymtracker-v4';

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

// ── Notificaciones push (las envia la VM con avisos.py) ─────────────────────
self.addEventListener('push', (event) => {
  let d = {};
  try {
    d = event.data ? event.data.json() : {};
  } catch {
    d = { body: event.data ? event.data.text() : '' };
  }
  event.waitUntil(
    self.registration.showNotification(d.title || 'GymTracker', {
      body: d.body || '',
      icon: 'icon.svg',
      badge: 'icon.svg',
      tag: d.tag || 'gymtracker', // mismo tag = reemplaza al anterior, no se apilan
      data: { url: d.url || './' }
    })
  );
});

// tocar el aviso abre la app (o la trae al frente si ya estaba abierta)
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const destino = new URL(event.notification.data?.url || './', self.registration.scope).href;
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((ventanas) => {
      for (const v of ventanas) {
        if (v.url.startsWith(self.registration.scope) && 'focus' in v) return v.focus();
      }
      return self.clients.openWindow(destino);
    })
  );
});
