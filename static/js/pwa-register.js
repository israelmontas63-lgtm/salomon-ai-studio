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

  // Bump con cada release de CACHE en service-worker.js (v97 ↔ app 110.22.23)
  var SW_URL = "/service-worker.js?v=97";

  function registerSw() {
    navigator.serviceWorker
      .register(SW_URL, { scope: "/", updateViaCache: "none" })
      .then(function (reg) {
        console.info("[SalomonPWA] SW registrado", reg.scope);
        if (reg.update) reg.update();
        if (reg.waiting) {
          reg.waiting.postMessage({ type: "SKIP_WAITING" });
        }
        // Revisar SW cada 8s; el UpdateManager decide si hay build nuevo
        setInterval(function () {
          if (reg.update) reg.update().catch(function () {});
        }, 8000);
        reg.addEventListener("updatefound", function () {
          var nw = reg.installing;
          if (!nw) return;
          nw.addEventListener("statechange", function () {
            if (nw.state === "installed" && reg.waiting) {
              // Activar SW nuevo; reload solo via controllerchange + build gate
              reg.waiting.postMessage({ type: "SKIP_WAITING" });
              window.dispatchEvent(
                new CustomEvent("salomon:deploy-notify", {
                  detail: { build: "sw", source: "pwa_register", instant: false },
                })
              );
              if (window.SalomonUpdate && window.SalomonUpdate.checkForUpdate) {
                window.SalomonUpdate.checkForUpdate();
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
      if (window.__salomon_sw_refreshing) return;
      // Solo recargar si hotPatch pidió claim (evita loop en primer control)
      if (!window.__salomon_awaiting_sw_claim) return;
      refreshing = true;
      window.__salomon_sw_refreshing = true;
      window.__salomon_awaiting_sw_claim = false;
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
