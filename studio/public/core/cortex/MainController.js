/**
 * core/cortex/MainController — kernel hard-linked.
 * init() fuerza: VoiceCore → VisionAgent → Greeting → LogicEngine.lock
 */
(function (global) {
  "use strict";

  var booted = false;
  var lastError = null;

  function C() {
    return global.SalomonCore || {};
  }

  function requireMod(name, pathHint) {
    var mod = C()[name];
    if (!mod) {
      lastError = "Falta módulo " + name + " — cargar " + pathHint + " antes de MainController";
      console.error("[MainController]", lastError);
      return null;
    }
    return mod;
  }

  function dispatchGreetingUi(frase, audioBase64, audioMime) {
    try {
      var HB = C().HistoryBuffer;
      if (HB) HB.push("asistente", frase);
      var ST = C().SemanticThreads;
      if (ST) ST.note("boot", frase, "razonamiento");
      global.dispatchEvent(
        new CustomEvent("salomon:core-greeting", {
          detail: {
            frase: frase,
            audio_base64: audioBase64 || null,
            audio_mime: audioMime || "audio/wav",
            modo: "energetico",
          },
        })
      );
      // Hint visible si React aún no montó
      var step = document.getElementById("splash-step");
      if (step && frase) step.textContent = String(frase).slice(0, 80);
    } catch (e) {
      console.warn("[MainController] greeting UI", e && e.message);
    }
  }

  var MainController = {
    version: "1.0.0-kernel",
    lastError: function () {
      return lastError;
    },
    booted: function () {
      return booted;
    },

    initializeGreeting: function (modo) {
      var Gateway = requireMod("HomeGateway", "/core/peripherals/HomeGateway.js");
      if (!Gateway) return Promise.reject(new Error(lastError));

      var energetic = String(modo || "enérgetico").toLowerCase().indexOf("energ") >= 0;
      console.info("[MainController] initializeGreeting(", modo, ")");

      return Gateway.startSession(null)
        .then(function (data) {
          var frase =
            (data && data.mensaje) ||
            (energetic
              ? "¡Israel! Aquí estoy — Salomón en línea, mente unificada y a tu disposición total."
              : "Israel, aquí estoy.");
          dispatchGreetingUi(frase, data && data.audio_base64, data && data.audio_mime);
          // Si la UI React tiene iniciarSesion propia, el evento permite sincronizar
          global.__SalomonCoreGreeting = {
            frase: frase,
            at: Date.now(),
            tts: !!(data && data.audio_base64),
          };
          return data;
        })
        .catch(function (err) {
          lastError =
            "initializeGreeting bloqueado: " +
            (err && err.message ? err.message : String(err)) +
            " — revisar HomeGateway.startSession → /api/chat/nuevo";
          console.error("[MainController]", lastError);
          // Fallback local para no dejar UI muda
          dispatchGreetingUi(
            "¡Israel! Aquí estoy — Salomón listo (saludo local). Conectando núcleo…",
            null,
            null
          );
          throw err;
        });
    },

    /**
     * Bloque init() obligatorio del kernel.
     */
    init: function () {
      lastError = null;
      console.info("[MainController] init() — hard-link kernel");

      var VoiceCore = requireMod("VoiceCore", "/core/peripherals/VoiceCore.js");
      var VisionAgent = requireMod("VisionAgent", "/core/peripherals/VisionAgent.js");
      var LogicEngine = requireMod("LogicEngine", "/core/cortex/LogicEngine.js");
      requireMod("HistoryBuffer", "/core/memory/HistoryBuffer.js");
      requireMod("SemanticThreads", "/core/memory/SemanticThreads.js");
      requireMod("HomeGateway", "/core/peripherals/HomeGateway.js");

      if (!VoiceCore || !VisionAgent || !LogicEngine) {
        return Promise.reject(new Error(lastError || "módulos incompletos"));
      }

      var chain = Promise.resolve();

      // 1) VoiceCore.enableNoiseGate(true)
      chain = chain.then(function () {
        return VoiceCore.enableNoiseGate(true).then(function (ok) {
          if (!ok) {
            console.warn(
              "[MainController] VoiceCore.enableNoiseGate — mic no otorgado aún (no bloquea saludo)"
            );
          }
          // Liberar device para STT del React VoiceButton
          if (VoiceCore.warm) return VoiceCore.warm();
          return ok;
        });
      });

      // 2) VisionAgent.activate()
      chain = chain.then(function () {
        VisionAgent.activate();
      });

      // 3) LogicEngine.lockLocalAgents()
      chain = chain.then(function () {
        LogicEngine.lockLocalAgents();
      });

      // 4) MainController.initializeGreeting("enérgetico")
      chain = chain.then(function () {
        return MainController.initializeGreeting("enérgetico");
      });

      return chain
        .then(function () {
          booted = true;
          global.__SalomonKernelBooted = true;
          console.info("[MainController] init() COMPLETO — kernel conectado");
          return { ok: true, booted: true };
        })
        .catch(function (err) {
          booted = false;
          if (!lastError) {
            lastError = "init() falló: " + (err && err.message ? err.message : String(err));
          }
          console.error("[MainController] init() ERROR →", lastError);
          return { ok: false, booted: false, error: lastError };
        });
    },
  };

  global.SalomonCore = global.SalomonCore || {};
  global.SalomonCore.MainController = MainController;

  // Auto-boot tras DOM
  function auto() {
    if (global.__SalomonKernelAuto === false) return;
    MainController.init();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", auto);
  } else {
    setTimeout(auto, 0);
  }
})(typeof window !== "undefined" ? window : globalThis);
