/* Service worker PWA — instalable en Android (Chrome) */
const CACHE = "salomon-v3";
const PRECACHE = [
  "/",
  "/manifest.json",
  "/manifest.webmanifest",
  "/icon.svg",
  "/icon-192.png",
  "/icon-512.png",
  "/apple-touch-icon.png",
  "/salomon-theme.css",
  "/splash.css",
  "/drawers.css",
  "/standalone-boot.js",
  "/drawers.js",
  "/vision-overlay.js",
  "/media-panel.js",
  "/bca-indicator.js",
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
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(fetch(req));
    return;
  }
  event.respondWith(
    caches.match(req).then((hit) => hit || fetch(req).catch(() => caches.match("/")))
  );
});
