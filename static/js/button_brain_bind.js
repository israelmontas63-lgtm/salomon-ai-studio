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

  window.__salomonTap = {
    cam: function () {
      ensureCamera().then(function () {
        if (window.SalomonCamera && window.SalomonCamera.toggleCamera) {
          window.SalomonCamera.toggleCamera();
        }
      });
    },
    aa: function () {
      ensureUi().then(function () {
        if (window.SalomonUiManager && window.SalomonUiManager.toggle) {
          window.SalomonUiManager.toggle();
        }
      });
    },
    settings: function () {
      ensureSettings().then(function () {
        if (window.SalomonSettings && window.SalomonSettings.toggle) {
          window.SalomonSettings.toggle();
        }
      });
    },
    back: function () {
      ensureBack().then(function () {
        if (window.SalomonBack && window.SalomonBack.onBackTap) {
          window.SalomonBack.onBackTap();
        } else if (window.SalomonBack && window.SalomonBack.neutralize) {
          window.SalomonBack.neutralize();
        }
      });
    },
    flip: function () {
      ensureCamera().then(function () {
        if (window.SalomonCamera && window.SalomonCamera.flipCamera) {
          window.SalomonCamera.flipCamera();
        }
      });
    },
  };

  console.info("[SalomonBind] __salomonTap listo (cam/aa/settings/back/flip)");
})();
