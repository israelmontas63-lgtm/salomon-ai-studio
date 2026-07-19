/**
 * Registra Service Worker Premium (scope /) + hook de update.
 */
(function () {
  if (!("serviceWorker" in navigator)) return;

  window.addEventListener("load", function () {
    navigator.serviceWorker
      .register("/service-worker.js?v=8", { scope: "/" })
      .then(function (reg) {
        reg.update();
        if (reg.waiting) {
          reg.waiting.postMessage({ type: "SKIP_WAITING" });
        }
        reg.addEventListener("updatefound", function () {
          const nw = reg.installing;
          if (!nw) return;
          nw.addEventListener("statechange", function () {
            if (nw.state === "installed" && navigator.serviceWorker.controller) {
              if (window.SalomonUpdate) {
                window.SalomonUpdate.showUpdateToast("sw");
              }
            }
          });
        });
      })
      .catch(function () {
        /* silencioso */
      });
  });
})();
