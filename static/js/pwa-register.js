/**
 * Salomón AI — Registro Service Worker (instalabilidad PWA).
 * Registro eager en scope '/'. Errores visibles en consola.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  if (!("serviceWorker" in navigator)) {
    console.warn("[SalomonPWA] serviceWorker no soportado en este navegador");
    return;
  }

  // Sin querystring en el path del SW (evita rarezas de scope/caché)
  var SW_URL = "/service-worker.js";

  function registerSw() {
    navigator.serviceWorker
      .register(SW_URL, { scope: "/", updateViaCache: "none" })
      .then(function (reg) {
        console.info("[SalomonPWA] SW registrado", reg.scope);
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
      .catch(function (err) {
        console.error("[SalomonPWA] Fallo al registrar SW:", err);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", registerSw, { once: true });
  } else {
    registerSw();
  }
})();
