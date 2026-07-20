/**
 * Salomón AI — Registro Service Worker (instalabilidad PWA).
 * updateViaCache:none + SKIP_WAITING agresivo para hot-update inmediato.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  if (!("serviceWorker" in navigator)) {
    console.warn("[SalomonPWA] serviceWorker no soportado en este navegador");
    return;
  }

  // Bump con cada release de CACHE en service-worker.js
  var SW_URL = "/service-worker.js?v=40";

  function registerSw() {
    navigator.serviceWorker
      .register(SW_URL, { scope: "/", updateViaCache: "none" })
      .then(function (reg) {
        console.info("[SalomonPWA] SW registrado", reg.scope);
        if (reg.update) reg.update();
        if (reg.waiting) {
          reg.waiting.postMessage({ type: "SKIP_WAITING" });
        }
        // Hot-loader: revisar SW cada 4s (sin frenos)
        setInterval(function () {
          if (reg.update) reg.update().catch(function () {});
        }, 4000);
        reg.addEventListener("updatefound", function () {
          var nw = reg.installing;
          if (!nw) return;
          nw.addEventListener("statechange", function () {
            if (nw.state === "installed") {
              if (reg.waiting) {
                reg.waiting.postMessage({ type: "SKIP_WAITING" });
              }
              window.dispatchEvent(
                new CustomEvent("salomon:deploy-notify", {
                  detail: { build: "sw", source: "pwa_register", instant: true },
                })
              );
              if (window.SalomonUpdate && window.SalomonUpdate.applyUpdateNow) {
                window.SalomonUpdate.applyUpdateNow("sw");
              } else if (window.SalomonUpdate && window.SalomonUpdate.showUpdateToast) {
                window.SalomonUpdate.showUpdateToast("sw");
              }
            }
          });
        });
      })
      .catch(function (err) {
        console.error("[SalomonPWA] Fallo al registrar SW:", err);
      });

    var refreshing = false;
    navigator.serviceWorker.addEventListener("controllerchange", function () {
      if (refreshing) return;
      refreshing = true;
      if (window.SalomonUpdate && window.SalomonUpdate._hardReload) {
        window.SalomonUpdate._hardReload();
      } else {
        var url = new URL(window.location.href);
        url.searchParams.set("v", String(Date.now()));
        window.location.replace(url.toString());
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", registerSw, { once: true });
  } else {
    registerSw();
  }
})();
