/**
 * Salomón AI — Vision Mode Trigger
 * "Activa el modo visión" → canal de fotogramas + análisis inmediato + Adam TTS.
 * AISLAMIENTO: no toca el botón de retroceso ni el neutralizador.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  var RE_TRIGGER =
    /\b(activa(r)?\s+(el\s+)?modo\s+visi[oó]n|modo\s+visi[oó]n|ojos\s+activos|activa(r)?\s+(mis\s+)?ojos|activa(r)?\s+visi[oó]n|visi[oó]n\s+activa|enciende\s+(la\s+)?c[aá]mara|abre\s+(la\s+)?c[aá]mara)\b/i;

  var ANALYZE_PROMPT =
    "Salomón, activa el modo visión. Mira lo que tengo frente a la cámara y " +
    "responde en primera persona de forma natural y exacta, por ejemplo: " +
    "«Sí, Israel, estoy viendo…» o «Sí, Israel, veo…». Identifica el objeto " +
    "principal (roca, árbol, planta, etc.) y un detalle concreto si es visible " +
    "(especie, color, forma). No inventes nada que no esté en el fotograma.";

  var VisionModeTrigger = {
    init() {
      // Sync táctil: botón cámara ya abre stream; marcamos modo visión + elevación
      window.addEventListener("salomon:camera-state", (ev) => {
        var state = (ev.detail && ev.detail.state) || "";
        var on = state === "CAMARA_ACTIVA" || state === "DISPARO";
        document.body.classList.toggle("vision-mode-active", on);
        if (on) {
          document.body.classList.add("vision-immersive");
        }
      });
      window.SalomonVisionModeTrigger = this;
    },

    matches(mensaje) {
      return RE_TRIGGER.test((mensaje || "").trim());
    },

    async ensureCameraStack() {
      if (window.SalomonMain && window.SalomonMain.ensureCameraStack) {
        await window.SalomonMain.ensureCameraStack();
        return;
      }
      var load = window.SalomonMain && window.SalomonMain.loadScript;
      if (!load) return;
      await Promise.all([
        load("/static/js/camera_logic.js"),
        load("/static/js/camera_toggle_ui.js"),
        load("/static/js/camera_full.js"),
        load("/static/js/vision_engine.js"),
      ]);
    },

    /**
     * Enciende cámara + elevación UI. analyze=true (default) → mira y describe.
     */
    async engage(opts) {
      opts = opts || {};
      var source = opts.source || "unknown";
      var analyze = opts.analyze !== false;

      // Durante dictado (keepCamera) permitir ojos; si no, respetar el portero
      var gate =
        window.request_ui_action ||
        (window.SalomonAILock && window.SalomonAILock.request_ui_action);
      var lock = window.SalomonAILock;
      var allowVision =
        lock &&
        typeof lock.allowsCameraDuringAi === "function" &&
        lock.allowsCameraDuringAi();
      if (gate && !allowVision && !gate("camera")) {
        return { ok: false, blocked: true, reason: "ai_lock" };
      }

      // Refuerzo keepCamera si la IA ya está en dictado
      if (lock && lock.activate) {
        lock.activate(source || "vision_mode_trigger", { keepCamera: true });
      }

      await this.ensureCameraStack();

      var cam = window.SalomonCamera;
      if (!cam || !cam.openCamera) {
        return { ok: false, reason: "camera_unavailable" };
      }

      if (!cam.isActive || !cam.isActive()) {
        await cam.openCamera();
      }

      if (window.SalomonCameraToggleUI && window.SalomonCameraToggleUI.elevate) {
        window.SalomonCameraToggleUI.elevate();
      } else {
        document.body.classList.add("camera-ui-elevated");
        var wrap = document.getElementById("cam-wrap");
        if (wrap) wrap.classList.add("is-elevated");
      }

      document.body.classList.add("vision-mode-active", "vision-immersive");

      window.dispatchEvent(
        new CustomEvent("salomon:vision-mode", {
          detail: {
            active: true,
            source: source,
            via: "vision_mode_trigger",
            analytical: !!analyze,
          },
        })
      );

      // Con cámara lista: abrir canal de fotogramas y describir lo que hay enfrente
      if (analyze && window.SalomonVision && window.SalomonVision.engageAnalyticalStreaming) {
        var pack = await window.SalomonVision.engageAnalyticalStreaming(
          opts.prompt || ANALYZE_PROMPT
        );
        var texto =
          (pack && pack.texto) ||
          (typeof pack === "string" ? pack : "") ||
          "Sí, Israel — estoy mirando lo que tienes frente a ti.";
        return {
          ok: true,
          texto: texto,
          audio_base64: pack && pack.audio_base64,
          audio_mime: pack && pack.audio_mime,
          source: source,
          analytical: true,
        };
      }

      return {
        ok: true,
        texto:
          "Modo visión activo. Estoy mirando — un momento mientras describo la escena.",
        source: source,
        analytical: false,
      };
    },

    /** Para handlers de chat/voz: engage + análisis + mensaje listo */
    async handleCommand(mensaje, opts) {
      if (!this.matches(mensaje)) return { handled: false };
      var o = Object.assign({ source: "command", analyze: true }, opts || {});
      var result = await this.engage(o);
      return {
        handled: true,
        ok: !!result.ok,
        texto: result.texto,
        audio_base64: result.audio_base64,
        audio_mime: result.audio_mime,
        result: result,
      };
    },
  };

  function boot() {
    VisionModeTrigger.init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
