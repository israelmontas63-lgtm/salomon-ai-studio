/**
 * core/peripherals/VisionAgent — visión en el flujo de entrada.
 */
(function (global) {
  "use strict";

  var active = false;

  var VisionAgent = {
    activate: function () {
      active = true;
      global.__SalomonVisionPort = global.__SalomonVisionPort || {};
      global.__SalomonVisionPort.activa = true;
      global.__SalomonVisionPort.inInputFlow = true;
      global.__SalomonVisionPort.engine = "camera-engine / MediaStreamManager";
      document.documentElement.dataset.visionAgent = "1";
      console.info("[VisionAgent] activate() — visión en flujo de entrada");
      // No abrir UI de cámara sola (evita ruido); queda lista para instrucción visual
      try {
        if (global.SalomonCameraV20 && typeof global.SalomonCameraV20.engine === "function") {
          /* engine disponible */
        }
      } catch (e) {}
      return true;
    },
    deactivate: function () {
      active = false;
      document.documentElement.dataset.visionAgent = "0";
    },
    isActive: function () {
      return active;
    },
    openCameraIfRequested: function () {
      if (!active) return false;
      try {
        if (global.SalomonCameraV20 && typeof global.SalomonCameraV20.open === "function") {
          global.SalomonCameraV20.open();
          return true;
        }
      } catch (e) {}
      return false;
    },
  };

  global.SalomonCore = global.SalomonCore || {};
  global.SalomonCore.VisionAgent = VisionAgent;
})(typeof window !== "undefined" ? window : globalThis);
