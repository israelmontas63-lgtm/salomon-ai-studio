/**
 * Salomón AI — Service Worker Premium v12 (Halo Blanco contraste)
 * Cachea capas static/; HTML/API en red; mensajes de actualización.
 * Created by Israel Monta - Salomón AI Studio
 */
const CACHE = "salomon-premium-v12";
const PRECACHE = [
  "/",
  "/manifest.json",
  "/static/css/styles.css",
  "/static/css/global.css",
  "/static/css/boton.css",
  "/static/css/camera_overlay.css",
  "/static/css/vision.css",
  "/static/css/camera_full.css",
  "/static/css/input_styles.css",
  "/static/css/update_styles.css",
  "/static/css/settings_layer.css",
  "/static/js/main.js",
  "/static/js/app.js",
  "/static/js/ui_controller.js",
  "/static/js/ui_manager.js",
  "/static/js/input_engine.js",
  "/static/js/camera_logic.js",
  "/static/js/camera_full.js",
  "/static/js/vision_engine.js",
  "/static/js/update_manager.js",
  "/static/js/settings_manager.js",
  "/static/js/components/SmartButton.js",
  "/static/js/pwa-register.js",
  "/static/js/workers/capture_worker.js",
  "/static/manifest.json",
  "/static/assets/master-255542.png",
  "/static/assets/icon-master.png",
  "/static/assets/icon-192.png",
  "/static/assets/icon-512.png",
  "/static/assets/icon-1024.png",
  "/static/assets/apple-touch-icon.png",
  "/static/assets/icon-halo-preview.png",
  "/static/assets/icon-settings.svg",
  "/static/assets/icon-camera.svg",
  "/static/assets/icon-mic.svg",
  "/static/assets/icon-flip.svg",
  "/static/assets/icon-shutter.svg",
];

function isApi(path) {
  return path.startsWith("/api/") || path === "/version.json";
}

function isStaticLayer(path) {
  return (
    path.startsWith("/static/css/") ||
    path.startsWith("/static/js/") ||
    path.startsWith("/static/assets/") ||
    path === "/static/manifest.json"
  );
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) =>
        Promise.all(
          PRECACHE.map((u) =>
            cache.add(u).catch(function () {
              /* opcional */
            })
          )
        )
      )
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("message", (event) => {
  const data = event.data || {};
  const reply = (payload) => {
    if (event.source && event.source.postMessage) {
      event.source.postMessage(payload);
    }
  };

  if (data.type === "SKIP_WAITING" || data.type === "FORCE_UPDATE") {
    event.waitUntil(self.skipWaiting().then(() => reply({ type: "SW_READY" })));
    return;
  }

  if (data.type === "CLEAR_CACHES" || data.type === "PURGE_AND_CLAIM") {
    event.waitUntil(
      caches
        .keys()
        .then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
        .then(() => self.skipWaiting())
        .then(() => self.clients.claim())
        .then(() => reply({ type: "CACHES_CLEARED" }))
    );
  }
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  const path = url.pathname;

  // API + version: siempre red (detección de deploy)
  if (isApi(path)) {
    event.respondWith(fetch(req, { cache: "no-store" }));
    return;
  }

  // Capas estáticas: stale-while-revalidate
  if (isStaticLayer(path)) {
    event.respondWith(
      caches.match(req).then((hit) => {
        const network = fetch(req).then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        });
        return hit || network;
      })
    );
    return;
  }

  // HTML / navegación: network-first
  if (req.mode === "navigate" || path === "/" || path.endsWith(".html")) {
    event.respondWith(
      fetch(req, { cache: "no-store" })
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => caches.match("/") || caches.match(req))
    );
    return;
  }

  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req))
  );
});
