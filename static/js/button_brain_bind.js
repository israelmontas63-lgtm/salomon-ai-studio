/**
 * Binding neuronal directo — un botón = una función al cerebro.
 * Usa bubble (no capture) y NO hace stopPropagation (no mata otros handlers).
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  function load(src) {
    if (window.SalomonMain && window.SalomonMain.loadScript) {
      return window.SalomonMain.loadScript(src);
    }
    return new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.onload = resolve;
      s.onerror = reject;
      document.body.appendChild(s);
    });
  }

  function ensureCamera() {
    if (window.SalomonCamera) return Promise.resolve();
    if (window.SalomonMain && window.SalomonMain.ensureCameraStack) {
      return window.SalomonMain.ensureCameraStack();
    }
    return Promise.all([
      load("/static/js/camera_logic.js"),
      load("/static/js/camera_full.js"),
      load("/static/js/camera_toggle_ui.js"),
    ]);
  }

  function ensureUi() {
    if (window.SalomonUiManager) return Promise.resolve();
    return Promise.all([
      load("/static/js/ui_manager.js"),
      load("/static/js/script.js"),
      load("/static/js/input_engine.js"),
    ]);
  }

  function ensureSettings() {
    if (window.SalomonSettings) return Promise.resolve();
    return load("/static/js/settings_manager.js");
  }

  function ensureBack() {
    if (window.SalomonBack) return Promise.resolve();
    return load("/static/js/back_button.js");
  }

  function ensureSmart() {
    if (window.SalomonSmartButton) return Promise.resolve();
    return Promise.all([
      load("/static/js/ai_state_lock.js"),
      load("/static/js/components/SmartButton.js"),
    ]);
  }

  window.__salomonTap = {
    cam: function () {
      ensureCamera().then(function () {
        if (window.SalomonCamera && window.SalomonCamera.toggleCamera) {
          window.SalomonCamera.toggleCamera();
        }
      }).catch(function (err) {
        console.warn("[SalomonBind] cam load failed", err);
      });
    },
    aa: function () {
      ensureUi().then(function () {
        if (window.SalomonUiManager && window.SalomonUiManager.toggle) {
          window.SalomonUiManager.toggle();
        }
      }).catch(function (err) {
        console.warn("[SalomonBind] aa load failed", err);
      });
    },
    settings: function () {
      ensureSettings().then(function () {
        if (window.SalomonSettings && window.SalomonSettings.toggle) {
          window.SalomonSettings.toggle();
        }
      }).catch(function (err) {
        console.warn("[SalomonBind] settings load failed", err);
      });
    },
    back: function () {
      ensureBack().then(function () {
        if (window.SalomonBack && window.SalomonBack.onBackTap) {
          window.SalomonBack.onBackTap();
        } else if (window.SalomonBack && window.SalomonBack.neutralize) {
          window.SalomonBack.neutralize();
        }
      }).catch(function (err) {
        console.warn("[SalomonBind] back load failed", err);
      });
    },
    flip: function () {
      ensureCamera().then(function () {
        if (window.SalomonCamera && window.SalomonCamera.flipCamera) {
          window.SalomonCamera.flipCamera();
        }
      }).catch(function (err) {
        console.warn("[SalomonBind] flip load failed", err);
      });
    },
    smart: function () {
      // API pública — NUNCA el.click() (recursión con onclick=__salomonTap.smart)
      ensureSmart().then(function () {
        var sb = window.SalomonSmartButton;
        if (!sb) return;
        try {
          // Si el gesto pointer acaba de manejar el toque, no duplicar
          if (Date.now() < (sb._ignoreClickUntil || 0)) return;
          if (typeof sb._isActiveMode === "function" && sb._isActiveMode()) {
            if (typeof sb.neutralize === "function") {
              sb.neutralize("brain_bind_tap");
              return;
            }
          }
          if (typeof sb.toggleMic === "function") {
            sb.toggleMic();
            return;
          }
          if (typeof sb.onClick === "function") {
            sb.onClick({
              preventDefault: function () {},
              stopPropagation: function () {},
              detail: 0,
            });
          }
        } catch (err) {
          console.warn("[SalomonBind] smart invoke failed", err);
        }
      }).catch(function (err) {
        console.warn("[SalomonBind] smart load failed", err);
      });
    },
  };

  /** Listeners bubble de refuerzo (sin stopPropagation) para ids críticos */
  function attachBubbleFallbacks() {
    if (window.__salomonBrainBubble) return;
    window.__salomonBrainBubble = true;
    var map = {
      "btn-cam": "cam",
      "btn-aa": "aa",
      "btn-settings": "settings",
      "btn-nav-back": "back",
      "btn-dock-flip": "flip",
      "smart-button": "smart",
    };
    Object.keys(map).forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      var fn = map[id];
      el.addEventListener(
        "click",
        function () {
          if (!window.__salomonTap || !window.__salomonTap[fn]) return;
          // Con data-brain-bind el onclick HTML ya dispara; bubble solo si falta
          if (el.getAttribute("data-brain-bind") === "1") return;
          window.__salomonTap[fn]();
        },
        false
      );
    });
  }

  function bootBubble() {
    attachBubbleFallbacks();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootBubble, { once: true });
  } else {
    bootBubble();
  }

  console.info("[SalomonBind] __salomonTap listo (cam/aa/settings/back/flip/smart)");
})();
