/* Service worker PWA — no bloquea API ni el boot */
const CACHE = "salomon-v4";
const PRECACHE = [
  "/manifest.json",
  "/manifest.webmanifest",
  "/icon-192.png",
  "/icon-512.png",
  "/icon.svg",
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

  // API y boot: siempre red (rutas relativas /api/...)
  if (
    url.pathname.startsWith("/api/") ||
    url.pathname.endsWith("standalone-boot.js") ||
    url.pathname === "/" ||
    url.pathname.endsWith("index.html")
  ) {
    event.respondWith(fetch(req));
    return;
  }

  event.respondWith(
    caches.match(req).then((hit) => hit || fetch(req).catch(() => caches.match("/")))
  );
});
