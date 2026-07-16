/* Service worker PWA — no bloquea API, boot ni eventos de cámara (DOM/main thread) */
const CACHE = "salomon-v10-neural-sync";
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

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const path = url.pathname;

  // Cámara/visión/UI interactiva: siempre red (evita lag por JS/CSS stale en cache)
  // getUserMedia y touch* viven en el main thread; el SW nunca los intercepta.
  if (
    path.startsWith("/api/") ||
    path.endsWith("standalone-boot.js") ||
    path === "/" ||
    path.endsWith("index.html") ||
    path.includes("salomon-ui-shield") ||
    path.includes("vision-overlay") ||
    path.includes("salomon-orchestrator-bridge")
  ) {
    event.respondWith(fetch(req));
    return;
  }

  event.respondWith(
    caches.match(req).then((hit) => hit || fetch(req).catch(() => caches.match("/")))
  );
});
