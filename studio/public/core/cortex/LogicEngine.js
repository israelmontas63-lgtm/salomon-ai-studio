/**
 * core/cortex/LogicEngine — razonamiento local; bloquea agentes web externos.
 */
(function (global) {
  "use strict";

  var locked = true;
  var originalFetch = null;

  function looksLikeExternalSearch(url, init) {
    try {
      var u = String(url || "");
      if (u.indexOf("/api/busqueda") >= 0) return true;
      if (u.indexOf("/api/chat") < 0) return false;
      var body = init && typeof init.body === "string" ? JSON.parse(init.body) : null;
      var m = String((body && body.mensaje) || "").toLowerCase();
      // Solo permite web si orden canónica Cortex
      if (/\b(busca|buscar)\s+en\s+(la\s+web|internet|wikipedia)\s+sobre\b/.test(m)) {
        return false; // autorizado
      }
      // Fase1 research no canónica → bloquear rewrite agresivo
      if (body && body.fase1 === true && !/\bbusca\s+en\s+la\s+web\s+sobre\b/.test(m)) {
        body.fase1 = false;
        init.body = JSON.stringify(body);
      }
    } catch (e) {}
    return false;
  }

  var LogicEngine = {
    locked: function () {
      return locked;
    },
    lockLocalAgents: function () {
      locked = true;
      global.__SalomonExternalWebLocked = true;
      if (!originalFetch && typeof global.fetch === "function") {
        originalFetch = global.fetch.bind(global);
        global.fetch = function (input, init) {
          init = init || {};
          var url = typeof input === "string" ? input : (input && input.url) || "";
          if (locked && looksLikeExternalSearch(url, init)) {
            console.info("[LogicEngine] bloqueado: búsqueda externa no canónica");
            return Promise.resolve(
              new Response(
                JSON.stringify({
                  ok: false,
                  error: "logic_engine_lock",
                  detalle: "Contexto externo bloqueado — usa: Busca en la web sobre…",
                }),
                { status: 423, headers: { "Content-Type": "application/json" } }
              )
            );
          }
          return originalFetch(input, init);
        };
      }
      console.info("[LogicEngine] lockLocalAgents() — web externa prohibida salvo orden canónica");
      return true;
    },
    unlock: function () {
      locked = false;
      global.__SalomonExternalWebLocked = false;
    },
  };

  global.SalomonCore = global.SalomonCore || {};
  global.SalomonCore.LogicEngine = LogicEngine;
})(typeof window !== "undefined" ? window : globalThis);
