/**
 * Registra el Service Worker Premium (scope /).
 */
(function () {
  if (!("serviceWorker" in navigator)) return;
  window.addEventListener("load", function () {
    navigator.serviceWorker
      .register("/service-worker.js", { scope: "/" })
      .catch(function () {
        /* silencioso en dev */
      });
  });
})();
