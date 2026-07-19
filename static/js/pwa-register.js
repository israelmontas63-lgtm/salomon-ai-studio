/**
 * Salomón AI — Registro inmediato del Service Worker (instalabilidad PWA).
 * Se ejecuta al parsear el script (defer = DOM listo); no espera window.load.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  if (!("serviceWorker" in navigator)) return;

  var SW_URL = "/service-worker.js?v=14";

  function registerSw() {
    navigator.serviceWorker
      .register(SW_URL, { scope: "/" })
      .then(function (reg) {
        // Chequeo temprano de actualización tras hard-reset
        if (reg.update) reg.update();
        if (reg.waiting) {
          reg.waiting.postMessage({ type: "SKIP_WAITING" });
        }
        reg.addEventListener("updatefound", function () {
          var nw = reg.installing;
          if (!nw) return;
          nw.addEventListener("statechange", function () {
            if (nw.state === "installed" && navigator.serviceWorker.controller) {
              if (window.SalomonUpdate && window.SalomonUpdate.showUpdateToast) {
                window.SalomonUpdate.showUpdateToast("sw");
              }
            }
          });
        });
      })
      .catch(function () {
        /* silencioso: no romper la UI Premium */
      });
  }

  // Registro instantáneo: defer ya garantiza DOM parseado
  registerSw();
})();
