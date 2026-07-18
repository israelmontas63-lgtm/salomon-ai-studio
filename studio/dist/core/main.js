/**
 * core/main.js — controlador final: permisos → MainController.init()
 * Orden requerido: config → permissions_check → core → Voice/Vision → HomeGateway → main
 */
(function (global) {
  "use strict";

  function boot() {
    var step = document.getElementById("splash-step");
    if (step) step.textContent = "Conectando kernel…";

    var ensure =
      global.SalomonPermissions && typeof global.SalomonPermissions.ensure === "function"
        ? global.SalomonPermissions.ensure()
        : Promise.resolve({ mic: false, camera: false });

    ensure
      .then(function (perms) {
        console.info("[main] permisos", perms);
        if (!global.SalomonCore || !global.SalomonCore.MainController) {
          throw new Error(
            "MainController ausente — verifica orden index.html (core.js antes de main.js)"
          );
        }
        if (!global.SalomonCore.VoiceCore) {
          throw new Error("VoiceCore ausente — carga VoiceCore.js antes de main.js");
        }
        if (!global.SalomonCore.VisionAgent) {
          throw new Error("VisionAgent ausente — carga VisionAgent.js antes de main.js");
        }
        if (!global.SalomonCore.HomeGateway) {
          throw new Error("HomeGateway ausente — carga HomeGateway.js antes de main.js");
        }
        // Si mic OK, enableNoiseGate dentro de init(); si no, init sigue con saludo
        return global.SalomonCore.MainController.init();
      })
      .then(function (res) {
        console.info("[main] kernel boot", res);
        if (step && res && res.ok) step.textContent = "Salomón listo";
      })
      .catch(function (err) {
        console.error("[main] BOOT BLOQUEADO:", err && err.message ? err.message : err);
        if (step) {
          step.textContent =
            "Error kernel: " + (err && err.message ? err.message : "ver consola");
        }
      });
  }

  // Desactivar auto-boot legado si existiera
  global.__SalomonKernelAuto = false;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(typeof window !== "undefined" ? window : globalThis);
