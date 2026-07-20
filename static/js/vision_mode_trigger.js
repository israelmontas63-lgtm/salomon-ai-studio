/**
 * Salomón AI — Vision Mode Trigger
 * Gatillo verbal ("modo visión", "ojos activos") + sync táctil con cámara/elevación.
 * AISLAMIENTO: no toca el botón de retroceso ni el neutralizador.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  var RE_TRIGGER =
    /\b(activa(r)?\s+(el\s+)?modo\s+visi[oó]n|modo\s+visi[oó]n|ojos\s+activos|activa(r)?\s+(mis\s+)?ojos|activa(r)?\s+visi[oó]n|visi[oó]n\s+activa|enciende\s+(la\s+)?c[aá]mara|abre\s+(la\s+)?c[aá]mara)\b/i;

  var REPLY =
    "Modo visión activo. Mis ojos están encendidos — puedes decir «mira» o «qué ves» cuando quieras que analice la escena.";

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
      // Fallback mínimo si main aún no exportó
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
     * Enciende cámara + elevación UI. No toca el neutralizador Back.
     */
    async engage(opts) {
      opts = opts || {};
      var source = opts.source || "unknown";

      var gate =
        window.request_ui_action ||
        (window.SalomonAILock && window.SalomonAILock.request_ui_action);
      if (gate && !gate("camera")) {
        return { ok: false, blocked: true, reason: "ai_lock" };
      }

      await this.ensureCameraStack();

      var cam = window.SalomonCamera;
      if (!cam || !cam.openCamera) {
        return { ok: false, reason: "camera_unavailable" };
      }

      if (!cam.isActive || !cam.isActive()) {
        await cam.openCamera();
      }

      // Elevación (capa UI aislada)
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
          detail: { active: true, source: source, via: "vision_mode_trigger" },
        })
      );

      return { ok: true, texto: REPLY, source: source };
    },

    /** Para handlers de chat/voz: engage + mensaje listo */
    async handleCommand(mensaje, opts) {
      if (!this.matches(mensaje)) return { handled: false };
      var result = await this.engage(opts || { source: "command" });
      return {
        handled: true,
        ok: !!result.ok,
        texto: result.texto || REPLY,
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
