/**
 * core/peripherals/HomeGateway — puente UI ↔ API (inicio / mente / chat).
 */
(function (global) {
  "use strict";

  function api(path, opts) {
    return fetch(path, opts || {}).then(function (r) {
      return r.json().catch(function () {
        return { ok: false, status: r.status };
      });
    });
  }

  var HomeGateway = {
    pingMente: function () {
      return api("/api/mente/conexion");
    },
    pingPerceptivo: function () {
      return api("/api/nucleo/perceptivo");
    },
    startSession: function (sessionId) {
      var q = sessionId
        ? "/api/chat/nuevo?session_id=" + encodeURIComponent(sessionId)
        : "/api/chat/nuevo";
      return api(q, { method: "POST" });
    },
    chat: function (mensaje, sessionId) {
      return api("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mensaje: mensaje,
          session_id: sessionId || null,
          fase1: false,
        }),
      });
    },
  };

  global.SalomonCore = global.SalomonCore || {};
  global.SalomonCore.HomeGateway = HomeGateway;
})(typeof window !== "undefined" ? window : globalThis);
