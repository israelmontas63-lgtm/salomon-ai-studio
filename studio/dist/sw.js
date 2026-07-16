/* Service worker PWA — CI/CD: actualiza desde Render sin atrapar voz/API */
const CACHE = "salomon-v11-cicd";
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
  "/salomon-theme.css",
  "/splash.css",
];

function networkOnlyPaths(path) {
  return (
    path.startsWith("/api/") ||
    path.endsWith("standalone-boot.js") ||
    path === "/" ||
    path.endsWith("index.html") ||
    path.includes("salomon-ui-shield") ||
    path.includes("vision-overlay") ||
    path.includes("salomon-orchestrator-bridge") ||
    path.includes("salomon-update") ||
    path.includes("voice-orchestrator")
  );
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
  if (data.type === "SKIP_WAITING" || data.type === "FORCE_UPDATE") {
    event.waitUntil(self.skipWaiting());
  }
  if (data.type === "CLEAR_CACHES") {
    event.waitUntil(clearAllCaches());
  }
  if (data.type === "PURGE_AND_CLAIM") {
    event.waitUntil(
      clearAllCaches().then(() => self.skipWaiting()).then(() => self.clients.claim())
    );
  }
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const path = url.pathname;

  // API, index, motor de voz/visión/update: siempre red (Render fresco)
  if (networkOnlyPaths(path)) {
    event.respondWith(fetch(req));
    return;
  }

  event.respondWith(
    caches.match(req).then((hit) => hit || fetch(req).catch(() => caches.match("/")))
  );
});
