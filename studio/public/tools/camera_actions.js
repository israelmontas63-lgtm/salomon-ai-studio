/**
 * Salomón AI — tools/camera_actions
 * Gatillos de captura de UI desconectados del flujo activo.
 * La captura en vivo queda SOLO en el botón de disparo (shutter).
 *
 * Re-activar (futuro): SalomonCameraActions.UI_AUTO_CAPTURE = true
 * y llamar bindLegacyUiCaptures(ctx).
 */
(function (global) {
  "use strict";

  var API = {
    version: "1.0.0",
    /** false = pantalla / stage / volumen NO disparan foto */
    UI_AUTO_CAPTURE: false,
    /** true = solo shutter / smart-button / API manual */
    SHUTTER_ONLY: true,

    /**
     * Handlers encapsulados (no borrados). ctx:
     * { canTakeShot, capturePhoto, isCamMode, isPrimaryGesture,
     *   isCaptureExemptTarget, isScreenShutterTarget, camera, CAPTURE_OPTS, log }
     */
    handlers: {
      screenShutter: function (ctx, e) {
        if (!ctx || !ctx.isCamMode()) return;
        if (ctx.camera && (ctx.camera.pinch.active || ctx.camera.pinch.moved)) return;
        if (ctx.isCaptureExemptTarget(e.target) && !ctx.isScreenShutterTarget(e.target)) return;
        if (!ctx.isPrimaryGesture(e)) return;
        if (!ctx.isScreenShutterTarget(e.target)) return;
        if (e.touches && e.touches.length > 0) return;
        if (e.changedTouches && e.changedTouches.length > 1) return;
        if (e.cancelable) e.preventDefault();
        e.stopImmediatePropagation();
        e.stopPropagation();
        if (!ctx.canTakeShot()) return;
        if (ctx.log) ctx.log("legacy pantalla → capturePhoto");
        ctx.capturePhoto();
      },

      volumeShutter: function (ctx, e) {
        if (!ctx || !ctx.isCamMode()) return;
        var k = e.key || "";
        var c = e.code || "";
        if (
          k !== "AudioVolumeUp" &&
          k !== "AudioVolumeDown" &&
          c !== "VolumeUp" &&
          c !== "VolumeDown" &&
          c !== "AudioVolumeUp" &&
          c !== "AudioVolumeDown"
        ) {
          return;
        }
        if (e.cancelable) e.preventDefault();
        e.stopImmediatePropagation();
        if (!ctx.canTakeShot()) return;
        if (ctx.log) ctx.log("legacy volumen → capturePhoto");
        ctx.capturePhoto();
      },

      stageShutter: function (ctx, e) {
        if (!ctx || !ctx.isCamMode()) return;
        if (ctx.camera && (ctx.camera.pinch.active || ctx.camera.pinch.moved)) return;
        if (e.target && e.target.closest && e.target.closest(".ui-smart-button, .ui-camera-close")) {
          return;
        }
        if (!ctx.isPrimaryGesture(e)) return;
        if (e.cancelable) e.preventDefault();
        e.stopImmediatePropagation();
        e.stopPropagation();
        if (!ctx.canTakeShot()) return;
        if (ctx.log) ctx.log("legacy stage → capturePhoto");
        ctx.capturePhoto();
      },

      /** Preview tap de camera-v13 (desconectado; shutter exclusivo) */
      previewTapCapture: function (takePicture) {
        if (typeof takePicture === "function") takePicture();
      },
    },

    /**
     * Vincula gatillos legacy SOLO si UI_AUTO_CAPTURE === true.
     * Por defecto no hace nada (flujo shutter-only).
     */
    bindLegacyUiCaptures: function (ctx) {
      if (!API.UI_AUTO_CAPTURE || !ctx) return { bound: false };
      var opts = ctx.CAPTURE_OPTS || { capture: true, passive: false };
      function onScreen(e) {
        API.handlers.screenShutter(ctx, e);
      }
      function onVol(e) {
        API.handlers.volumeShutter(ctx, e);
      }
      document.addEventListener("touchend", onScreen, opts);
      document.addEventListener("pointerup", onScreen, opts);
      document.addEventListener("keydown", onVol, true);
      document.addEventListener("keyup", onVol, true);
      if (ctx.log) ctx.log("camera_actions: legacy UI captures BOUND");
      return { bound: true, onScreen: onScreen, onVol: onVol };
    },

    bindLegacyStageShutter: function (stage, ctx) {
      if (!API.UI_AUTO_CAPTURE || !stage || !ctx) return null;
      var opts = ctx.CAPTURE_OPTS || { capture: true, passive: false };
      function onTap(e) {
        API.handlers.stageShutter(ctx, e);
      }
      ["touchend", "pointerup", "click"].forEach(function (type) {
        stage.addEventListener(type, onTap, type === "click" ? true : opts);
      });
      return onTap;
    },

    /** Orientación: solo visual / cooldown — NUNCA captura */
    onOrientationVisualOnly: function (ctx) {
      if (ctx && typeof ctx.suppressShotWindow === "function") {
        ctx.suppressShotWindow();
      }
      if (ctx && ctx.log) ctx.log("orientation → visual only (no capture)");
    },
  };

  global.SalomonCameraActions = API;
})(typeof window !== "undefined" ? window : globalThis);
