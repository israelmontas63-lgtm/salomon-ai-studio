/**
 * Salomón AI — Service Worker Premium (alineado a app version)
 * Cachea capas static/; HTML/API en red; mensajes de actualización.
 * Created by Israel Monta - Salomón AI Studio
 */
const CACHE = "salomon-premium-v97";

function cacheMatchFlexible(req) {
  return caches.match(req).then(function (hit) {
    if (hit) return hit;
    try {
      var u = new URL(req.url);
      u.search = "";
      return caches.match(u.pathname);
    } catch (_) {
      return undefined;
    }
  });
}
const PRECACHE = [
  "/",
  "/manifest.json",
  "/static/css/styles.css",
  "/static/css/global.css",
  "/static/css/boton.css",
  "/static/css/camera_overlay.css",
  "/static/css/vision.css",
  "/static/css/camera_full.css",
  "/static/css/camera_hud.css",
  "/static/css/camera_toggle_ui.css",
  "/static/css/input_styles.css",
  "/static/css/update_styles.css",
  "/static/css/settings_layer.css",
  "/static/css/chat_history_drawer.css",
  "/static/css/back_button.css",
  "/static/css/ui_hit_repair.css",
  "/static/css/bottom_bar_ux.css",
  "/static/js/main.js",
  "/static/js/app.js",
  "/static/js/ui_controller.js",
  "/static/js/ui_manager.js",
  "/static/js/script.js",
  "/static/js/input_engine.js",
  "/static/js/camera_logic.js",
  "/static/js/camera_toggle_ui.js",
  "/static/js/camera_full.js",
  "/static/js/vision_engine.js",
  "/static/js/vision_mode_trigger.js",
  "/static/js/update_manager.js",
  "/static/js/realtime_notification_badge.js",
  "/static/js/settings_manager.js",
  "/static/js/chat_history_drawer.js",
  "/static/js/back_button.js",
  "/static/js/ui_boot_reconnect.js",
  "/static/js/button_brain_bind.js",
  "/static/js/ai_state_lock.js",
  "/static/js/components/SmartButton.js",
  "/static/js/voice_layer.js",
  "/static/js/pwa-register.js",
  "/static/js/workers/capture_worker.js",
  "/static/manifest.json",
  "/static/icons/design_tokens.json",
  "/static/icons/255542.png",
  "/static/icons/android-chrome-192x192.png",
  "/static/icons/android-chrome-512x512.png",
  "/static/icons/android-chrome-192x192-maskable.png",
  "/static/icons/android-chrome-512x512-maskable.png",
  "/static/icons/apple-touch-icon.png",
  "/static/icons/mstile-150x150.png",
  "/static/icons/favicon-32x32.png",
  "/static/icons/favicon-16x16.png",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/js/pwa-register.js",
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
    path.startsWith("/static/icons/") ||
    path === "/static/manifest.json" ||
    path === "/manifest.json"
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
      .then(() => self.clients.matchAll({ type: "window", includeUncontrolled: true }))
      .then((clients) => {
        // Informativo: NO forzar hot-reload (evita bucles en primer install)
        clients.forEach(function (client) {
          client.postMessage({
            type: "SW_ACTIVATED",
            cache: CACHE,
            event: "SW_ACTIVATED",
            forceUpdate: false,
          });
        });
      })
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

  // JS + CSS críticos: network-first (evita PWA con UI muerta tras deploy)
  if (path.startsWith("/static/js/") || path.startsWith("/static/css/")) {
    event.respondWith(
      fetch(req, { cache: "no-store" })
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            const bareCopy = res.clone();
            caches.open(CACHE).then((c) => {
              c.put(req, copy);
              /* también cachear sin query para offline match flexible */
              try {
                c.put(new Request(path), bareCopy);
              } catch (_) {}
            });
          }
          return res;
        })
        .catch(() => cacheMatchFlexible(req))
    );
    return;
  }

  // assets: stale-while-revalidate
  if (isStaticLayer(path)) {
    event.respondWith(
      cacheMatchFlexible(req).then((hit) => {
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
