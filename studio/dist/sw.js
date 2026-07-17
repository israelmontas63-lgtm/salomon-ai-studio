/**
 * Salomon PWA Nativa v103 — Service Worker (Sellado Final)
 * Shell cache-first; API chat/media siempre red.
 * Identidad + inmune + arquitecto: stale-while-revalidate.
 * Created by Israel Monta - Salomon AI Studio
 */
const CACHE = "salomon-pwa-v104";
const PRECACHE = [
  "/",
  "/manifest.json",
  "/manifest.webmanifest",
  "/icon-192-v2.png",
  "/icon-512-v2.png",
  "/icon-192-maskable-v2.png",
  "/icon-512-maskable-v2.png",
  "/icon-v2.svg",
  "/apple-touch-icon-v2.png",
  "/favicon-v2.ico",
  "/salomon-theme.css?v=104",
  "/splash.css?v=104",
  "/thinking-animation-spec.css?v=104",
  "/salomon-ui-shield.css?v=104",
  "/standalone-boot.js?v=104",
  "/salomon-update.js?v=104",
  "/pwa-nativa.js?v=104",
  "/reconexion-perifericos.js?v=104",
  "/visual-progress.js?v=70",
  "/api/identidad",
  "/api/inmune",
  "/api/conectividad",
  "/api/web/arquitecto",
  "/api/eficiencia",
];

function pathOf(url) {
  try {
    return new URL(url).pathname;
  } catch (_) {
    return url || "";
  }
}

function isApiNetworkOnly(path) {
  if (!path.startsWith("/api/")) return false;
  // Nucleo identidad/inmune/conectividad/web: pueden usarse desde cache PWA
  if (
    path === "/api/identidad" ||
    path === "/api/inmune" ||
    path === "/api/conectividad" ||
    path === "/api/web/arquitecto" ||
    path === "/api/eficiencia" ||
    path === "/api/cognicion/multimodal" ||
    path === "/api/agentes/estado"
  ) {
    return false;
  }
  // chat / media / busqueda / reconexion activa → siempre red
  return true;
}

function isShellAsset(path, fullUrl) {
  if (
    path === "/" ||
    path.endsWith("/index.html") ||
    path.endsWith(".png") ||
    path.endsWith(".ico") ||
    path.endsWith(".svg") ||
    path.endsWith(".webmanifest") ||
    path.endsWith("manifest.json")
  ) {
    return true;
  }
  // CSS/JS de shell (no camera-engine hot path exclusivo)
  if (path.endsWith(".css") || path.endsWith(".js")) {
    if (path.includes("camera-engine") || path.includes("camera-v13")) {
      return false; // network-first para no congelar Golden State stale
    }
    return true;
  }
  return false;
}

async function precache() {
  const c = await caches.open(CACHE);
  await Promise.all(
    PRECACHE.map((u) =>
      c.add(u).catch(() => {
        /* ignore missing optional */
      })
    )
  );
}

self.addEventListener("install", (event) => {
  event.waitUntil(precache().then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
      await precache();
      await self.clients.claim();
    })()
  );
});

self.addEventListener("message", (event) => {
  const data = event.data || {};
  const reply = (payload) => {
    if (event.source && event.source.postMessage) event.source.postMessage(payload);
  };
  if (data.type === "SKIP_WAITING" || data.type === "FORCE_UPDATE") {
    event.waitUntil(self.skipWaiting().then(() => reply({ type: "SW_READY" })));
    return;
  }
  if (data.type === "CLEAR_CACHES") {
    event.waitUntil(
      caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k)))).then(() =>
        reply({ type: "CACHES_CLEARED" })
      )
    );
    return;
  }
  if (data.type === "PURGE_AND_CLAIM" || data.type === "FORCE_RELOAD_PREP") {
    event.waitUntil(
      caches
        .keys()
        .then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
        .then(() => self.skipWaiting())
        .then(() => self.clients.claim())
        .then(() => reply({ type: "PURGE_DONE" }))
    );
  }
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  // CRÍTICO v104: no interceptar orígenes externos (gateway web, APIs remotas)
  if (url.origin !== self.location.origin) return;
  const path = url.pathname;

  // Chat / media / mutaciones cognitivas: siempre red
  if (isApiNetworkOnly(path)) {
    event.respondWith(fetch(req, { cache: "no-store" }).catch(() => caches.match(req)));
    return;
  }

  // Identidad / inmune / conectividad / web: stale-while-revalidate
  if (
    path === "/api/identidad" ||
    path === "/api/inmune" ||
    path === "/api/conectividad" ||
    path === "/api/web/arquitecto" ||
    path === "/api/eficiencia"
  ) {
    event.respondWith(
      caches.open(CACHE).then(async (cache) => {
        const cached = await cache.match(req);
        const network = fetch(req)
          .then((res) => {
            if (res && res.ok) cache.put(req, res.clone());
            return res;
          })
          .catch(() => cached);
        return cached || network;
      })
    );
    return;
  }

  // Shell: cache-first → instant open
  if (isShellAsset(path, url.href) || path === "/") {
    event.respondWith(
      caches.match(req).then((hit) => {
        if (hit) {
          // Refresh in background
          fetch(req)
            .then((res) => {
              if (res && res.ok) caches.open(CACHE).then((c) => c.put(req, res));
            })
            .catch(() => {});
          return hit;
        }
        return fetch(req)
          .then((res) => {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
            return res;
          })
          .catch(() => caches.match("/"));
      })
    );
    return;
  }

  // Default: network, fallback cache
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res && res.ok && req.method === "GET") {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        }
        return res;
      })
      .catch(() => caches.match(req).then((hit) => hit || caches.match("/")))
  );
});
