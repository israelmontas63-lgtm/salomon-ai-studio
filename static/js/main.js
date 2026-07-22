/**
 * Salomón AI — main.js (Performance Overhaul)
 * Code splitting: UI mínima primero; módulos pesados lazy.
 * Cámara: JS bajo demanda al primer toque (sin getUserMedia anticipado).
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  var loaded = Object.create(null);
  var cameraReady = null;
  var inputReady = null;

  function loadScript(src) {
    if (loaded[src]) return loaded[src];
    loaded[src] = new Promise(function (resolve, reject) {
      var existing = document.querySelector('script[data-salomon-src="' + src + '"]');
      if (existing) {
        if (existing.dataset.ready === "1") {
          resolve();
          return;
        }
        existing.addEventListener("load", function () {
          resolve();
        });
        existing.addEventListener("error", reject);
        return;
      }
      var s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.dataset.salomonSrc = src;
      s.onload = function () {
        s.dataset.ready = "1";
        resolve();
      };
      s.onerror = function () {
        delete loaded[src];
        reject(new Error("fail " + src));
      };
      document.body.appendChild(s);
    });
    return loaded[src];
  }

  function idle(fn, timeout) {
    if (typeof requestIdleCallback === "function") {
      requestIdleCallback(fn, { timeout: timeout || 1200 });
    } else {
      setTimeout(fn, 1);
    }
  }

  function afterPaint(fn) {
    requestAnimationFrame(function () {
      requestAnimationFrame(fn);
    });
  }

  /** Defer trabajo >1 frame fuera del critical path */
  function deferHeavy(fn) {
    idle(function () {
      try {
        fn();
      } catch (_) {}
    }, 800);
  }

  function ensureCore() {
    // pwa-register.js va en index.html (eager) — no duplicar aquí
    return Promise.all([
      loadScript("/static/js/ui_controller.js"),
      loadScript("/static/js/settings_manager.js"),
      loadScript("/static/js/chat_history_drawer.js"),
      loadScript("/static/js/back_button.js"),
      loadScript("/static/js/vision_mode_trigger.js"),
      loadScript("/static/js/voice_layer.js"),
      loadScript("/static/js/ai_state_lock.js"),
      loadScript("/static/js/components/SmartButton.js"),
    ]);
  }

  function ensureInputStack() {
    if (inputReady) return inputReady;
    // script.js primero: enviarMensaje() → /api/chat
    inputReady = Promise.all([
      loadScript("/static/js/ui_manager.js"),
      loadScript("/static/js/script.js"),
      loadScript("/static/js/input_engine.js"),
      loadScript("/static/js/update_manager.js"),
      loadScript("/static/js/realtime_notification_badge.js"),
    ]);
    return inputReady;
  }

  /** Cámara + visión: solo cuando el usuario toca cam/flip o tras idle suave */
  function ensureCameraStack() {
    if (cameraReady) return cameraReady;
    cameraReady = Promise.all([
      loadScript("/static/js/camera_logic.js"),
      loadScript("/static/js/camera_toggle_ui.js"),
      loadScript("/static/js/camera_full.js"),
      loadScript("/static/js/vision_engine.js"),
    ]);
    return cameraReady;
  }

  function wireLazyTriggers() {
    var btnCam = document.getElementById("btn-cam");
    var btnFlip =
      document.getElementById("btn-dock-flip") ||
      document.getElementById("btn-flip");
    var btnAa = document.getElementById("btn-aa");

    if (btnCam) {
      btnCam.addEventListener(
        "pointerdown",
        function () {
          ensureCameraStack();
        },
        { passive: true }
      );
      btnCam.addEventListener(
        "click",
        function (e) {
          if (window.SalomonCamera) return;
          e.preventDefault();
          e.stopImmediatePropagation();
          ensureCameraStack().then(function () {
            if (window.SalomonCamera && window.SalomonCamera.toggleCamera) {
              window.SalomonCamera.toggleCamera();
            }
          });
        },
        true
      );
    }

    if (btnFlip) {
      btnFlip.addEventListener(
        "pointerdown",
        function () {
          ensureCameraStack();
        },
        { passive: true }
      );
    }

    if (btnAa) {
      btnAa.addEventListener(
        "pointerdown",
        function () {
          ensureInputStack();
        },
        { passive: true }
      );
      btnAa.addEventListener(
        "click",
        function (e) {
          if (window.SalomonUiManager) return;
          e.preventDefault();
          e.stopImmediatePropagation();
          ensureInputStack().then(function () {
            if (window.SalomonUiManager && window.SalomonUiManager.toggle) {
              window.SalomonUiManager.toggle();
            }
          });
        },
        true
      );
    }

    var toastBtn = document.getElementById("update-toast-btn");
    if (toastBtn) {
      toastBtn.addEventListener(
        "pointerdown",
        function () {
          ensureInputStack();
        },
        { passive: true }
      );
    }
  }

  function boot() {
    document.documentElement.classList.add("salomon-perf");

    ensureCore()
      .then(function () {
        wireLazyTriggers();
        // Tras primer paint: input + update (milisegundos)
        afterPaint(function () {
          ensureInputStack();
        });
        // Cámara: SOLO al toque del usuario (sin prefetch de getUserMedia ni JS de cámara)
      })
      .catch(function () {
        /* degradación silenciosa */
      });
  }

  window.SalomonMain = {
    loadScript: loadScript,
    ensureCameraStack: ensureCameraStack,
    ensureInputStack: ensureInputStack,
    deferHeavy: deferHeavy,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
