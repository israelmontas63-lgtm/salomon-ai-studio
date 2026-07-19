/**
 * Salomón AI — Input Engine
 * Delega el envío a script.js → enviarMensaje() → POST /api/chat
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  function boot() {
    // script.js ya cablea click/Enter → enviarMensaje()
    // Aquí solo exponemos compatibilidad con el resto del sistema.
    window.SalomonInput = {
      submit: function () {
        if (typeof window.enviarMensaje === "function") {
          return window.enviarMensaje();
        }
      },
      sessionId: localStorage.getItem("salomon_session_id") || null,
    };

    fetch("/api/motor/estado", { cache: "no-store" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        window.SalomonMotor = data;
        if (data && data.listo === false) {
          console.warn("[SalomonMotor]", data.mensaje || "API key no configurada");
        } else {
          console.info("[SalomonMotor] listo", data && data.provider);
        }
      })
      .catch(function () {});
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
