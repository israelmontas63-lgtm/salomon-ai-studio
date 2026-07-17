/* Service worker PWA — force-fresh: JS/CSS/API siempre desde Render */
const CACHE = "salomon-v14-purge";
const PRECACHE = [
  "/manifest.json",
  "/manifest.webmanifest",
  "/icon-192-v2.png",
  "/icon-512-v2.png",
  "/icon-192-maskable-v2.png",
  "/icon-512-maskable-v2.png",
  "/icon-v2.svg",
  "/apple-touch-icon-v2.png",
  "/favicon-v2.ico",
];

function mustNetwork(path) {
  if (path.startsWith("/api/")) return true;
  if (path.endsWith("version.json") || path === "/version.json") return true;
  if (path === "/" || path.endsWith("/index.html") || path.endsWith("index.html")) return true;
  // Nunca cachear scripts/estilos (Actualizar debe traer UI fresca al instante)
  if (path.endsWith(".js") || path.endsWith(".css") || path.endsWith(".mjs")) return true;
  if (path.includes("salomon-") || path.includes("vision-") || path.includes("voice-")) return true;
  if (path.includes("standalone-boot") || path.includes("drawers") || path.includes("header-logo")) {
    return true;
  }
  return false;
}

async function clearAllCaches() {
  const keys = await caches.keys();
  await Promise.all(keys.map((k) => caches.delete(k)));
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((c) => c.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    clearAllCaches()
      .then(() => caches.open(CACHE).then((c) => c.addAll(PRECACHE)))
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
  if (data.type === "CLEAR_CACHES") {
    event.waitUntil(clearAllCaches().then(() => reply({ type: "CACHES_CLEARED" })));
    return;
  }
  if (data.type === "PURGE_AND_CLAIM" || data.type === "FORCE_RELOAD_PREP") {
    event.waitUntil(
      clearAllCaches()
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
  const path = url.pathname;

  if (mustNetwork(path)) {
    event.respondWith(
      fetch(req, { cache: "no-store" }).catch(() => fetch(req))
    );
    return;
  }

  event.respondWith(
    fetch(req)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      })
      .catch(() => caches.match(req).then((hit) => hit || caches.match("/")))
  );
});
