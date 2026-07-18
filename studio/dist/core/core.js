/**
 * core/core.js — núcleo: memoria + LogicEngine + MainController (sin auto-boot).
 * Depende de: config.js
 * Periféricos se cargan después (VoiceCore, VisionAgent, HomeGateway).
 */
(function (global) {
  "use strict";

  global.SalomonCore = global.SalomonCore || {};

  /* ── HistoryBuffer ── */
  var HKEY = "salomon_core_history_v1";
  global.SalomonCore.HistoryBuffer = {
    push: function (rol, texto) {
      var arr = [];
      try {
        arr = JSON.parse(localStorage.getItem(HKEY) || "[]") || [];
      } catch (e) {}
      arr.push({ at: Date.now(), rol: rol, texto: String(texto || "").slice(0, 2000) });
      try {
        localStorage.setItem(HKEY, JSON.stringify(arr.slice(-60)));
      } catch (e2) {}
    },
    recent: function (n) {
      try {
        return (JSON.parse(localStorage.getItem(HKEY) || "[]") || []).slice(-(n || 12));
      } catch (e) {
        return [];
      }
    },
  };

  /* ── SemanticThreads ── */
  var TKEY = "salomon_core_threads_v1";
  global.SalomonCore.SemanticThreads = {
    note: function (sessionId, text, area) {
      var map = {};
      try {
        map = JSON.parse(localStorage.getItem(TKEY) || "{}") || {};
      } catch (e) {}
      var sid = sessionId || "default";
      map[sid] = map[sid] || { area: area || "razonamiento", notes: [] };
      map[sid].notes.push({ at: Date.now(), text: String(text || "").slice(0, 500), area: area });
      if (map[sid].notes.length > 40) map[sid].notes = map[sid].notes.slice(-40);
      try {
        localStorage.setItem(TKEY, JSON.stringify(map));
      } catch (e2) {}
    },
  };

  /* ── LogicEngine ── */
  var locked = true;
  var originalFetch = null;
  global.SalomonCore.LogicEngine = {
    lockLocalAgents: function () {
      locked = true;
      global.__SalomonExternalWebLocked = true;
      if (!originalFetch && typeof global.fetch === "function") {
        originalFetch = global.fetch.bind(global);
        global.fetch = function (input, init) {
          init = init || {};
          var url = typeof input === "string" ? input : (input && input.url) || "";
          if (locked && String(url).indexOf("/api/busqueda") >= 0) {
            return Promise.resolve(
              new Response(
                JSON.stringify({
                  ok: false,
                  error: "logic_engine_lock",
                  detalle: "Usa: Busca en la web sobre…",
                }),
                { status: 423, headers: { "Content-Type": "application/json" } }
              )
            );
          }
          return originalFetch(input, init);
        };
      }
      console.info("[LogicEngine] lockLocalAgents()");
      return true;
    },
    locked: function () {
      return locked;
    },
  };

  /* ── MainController (sin auto-init; main.js lo dispara) ── */
  var booted = false;
  var lastError = null;

  function requireMod(name, hint) {
    var mod = global.SalomonCore[name];
    if (!mod) {
      lastError = "Falta módulo " + name + " — cargar " + hint + " antes de main.js";
      console.error("[MainController]", lastError);
      return null;
    }
    return mod;
  }

  function dispatchGreetingUi(frase, audioBase64, audioMime) {
    try {
      global.SalomonCore.HistoryBuffer.push("asistente", frase);
      global.SalomonCore.SemanticThreads.note("boot", frase, "razonamiento");
      global.dispatchEvent(
        new CustomEvent("salomon:core-greeting", {
          detail: { frase: frase, audio_base64: audioBase64, audio_mime: audioMime, modo: "energetico" },
        })
      );
      var step = document.getElementById("splash-step");
      if (step && frase) step.textContent = String(frase).slice(0, 90);
    } catch (e) {}
  }

  global.SalomonCore.MainController = {
    version: "1.1.0-kernel",
    lastError: function () {
      return lastError;
    },
    booted: function () {
      return booted;
    },
    initializeGreeting: function (modo) {
      var Gateway = requireMod("HomeGateway", "/core/peripherals/HomeGateway.js");
      if (!Gateway) return Promise.reject(new Error(lastError));
      return Gateway.startSession(null).then(function (data) {
        var frase =
          (data && data.mensaje) ||
          "¡Israel! Aquí estoy — Salomón en línea, mente unificada y a tu disposición total.";
        dispatchGreetingUi(frase, data && data.audio_base64, data && data.audio_mime);
        global.__SalomonCoreGreeting = { frase: frase, at: Date.now(), tts: !!(data && data.audio_base64) };
        return data;
      });
    },
    init: function () {
      lastError = null;
      var VoiceCore = requireMod("VoiceCore", "/core/peripherals/VoiceCore.js");
      var VisionAgent = requireMod("VisionAgent", "/core/peripherals/VisionAgent.js");
      var LogicEngine = requireMod("LogicEngine", "/core/core.js");
      requireMod("HomeGateway", "/core/peripherals/HomeGateway.js");
      if (!VoiceCore || !VisionAgent || !LogicEngine) {
        return Promise.reject(new Error(lastError || "módulos incompletos"));
      }

      // Noise gate SOLO tras permiso de audio
      var perms = global.__SalomonPermissions || {};
      var chain = Promise.resolve();
      if (perms.mic) {
        chain = chain.then(function () {
          return VoiceCore.enableNoiseGate(true).then(function (ok) {
            if (VoiceCore.warm) return VoiceCore.warm();
            return ok;
          });
        });
      } else {
        console.warn("[MainController] sin permiso mic — noiseGate diferido");
      }

      chain = chain
        .then(function () {
          VisionAgent.activate();
        })
        .then(function () {
          LogicEngine.lockLocalAgents();
        })
        .then(function () {
          return global.SalomonCore.MainController.initializeGreeting("enérgetico");
        });

      return chain
        .then(function () {
          booted = true;
          global.__SalomonKernelBooted = true;
          console.info("[MainController] init() COMPLETO");
          return { ok: true };
        })
        .catch(function (err) {
          lastError = err && err.message ? err.message : String(err);
          console.error("[MainController] init() ERROR", lastError);
          return { ok: false, error: lastError };
        });
    },
  };

  console.info("[core] núcleo SalomonCore listo (espera peripherals + main.js)");
})(typeof window !== "undefined" ? window : globalThis);
