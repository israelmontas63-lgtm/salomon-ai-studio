/**
 * Salomón AI — Service Worker Premium (capas static/)
 * Cachea CSS/JS/assets; HTML y /api van a red (hot-reload en móvil).
 * Created by Israel Monta - Salomón AI Studio
 */
const CACHE = "salomon-premium-v6";
const PRECACHE = [
  "/",
  "/static/css/styles.css",
  "/static/css/boton.css",
  "/static/css/camera_overlay.css",
  "/static/css/vision.css",
  "/static/css/camera_full.css",
  "/static/css/input_styles.css",
  "/static/js/app.js",
  "/static/js/ui_controller.js",
  "/static/js/ui_manager.js",
  "/static/js/input_engine.js",
  "/static/js/camera_logic.js",
  "/static/js/camera_full.js",
  "/static/js/vision_engine.js",
  "/static/js/components/SmartButton.js",
  "/static/manifest.json",
  "/static/assets/logo-ss.svg",
  "/static/assets/icon-user.svg",
  "/static/assets/icon-settings.svg",
  "/static/assets/icon-camera.svg",
  "/static/assets/icon-mic.svg",
  "/static/assets/icon-flip.svg",
  "/static/assets/icon-shutter.svg",
];

function isApi(path) {
  return path.startsWith("/api/");
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

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  const path = url.pathname;

  // API y chat: siempre red
  if (isApi(path)) {
    event.respondWith(fetch(req, { cache: "no-store" }));
    return;
  }

  // Capas estáticas: cache-first + refresh
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

  // HTML / navegación: network-first (ver cambios al instante)
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
