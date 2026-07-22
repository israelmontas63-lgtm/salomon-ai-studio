/**
 * Boot de reconexión UI — limpia capas atascadas y re-enlaza botones.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  function clearStuckLayers() {
    var body = document.body;
    if (!body) return;
    body.classList.remove(
      "vision-immersive",
      "input-sheet-open",
      "control-layer-open",
      "ai-active",
      "camera-ui-elevated",
      "has-back-context"
    );
    body.removeAttribute("data-vision");

    var stage = document.getElementById("camera-stage");
    if (stage) {
      stage.classList.remove(
        "is-visible",
        "is-immersive",
        "is-flash",
        "is-mirror",
        "is-selfie"
      );
      stage.setAttribute("aria-hidden", "true");
    }

    var wrap = document.getElementById("cam-wrap");
    if (wrap) wrap.classList.remove("is-active", "is-elevated");

    var input = document.getElementById("input-layer");
    if (input) {
      input.classList.remove("is-open");
      input.setAttribute("aria-hidden", "true");
    }

    var layer = document.getElementById("control-layer");
    if (layer) layer.classList.remove("is-open");

    var drawer = document.getElementById("chat-drawer");
    if (drawer) drawer.classList.remove("is-open");
  }

  function load(src) {
    return new Promise(function (resolve, reject) {
      var existing = document.querySelector('script[data-salomon-src="' + src + '"]');
      if (existing && existing.dataset.ready === "1") {
        resolve();
        return;
      }
      if (window.SalomonMain && window.SalomonMain.loadScript) {
        window.SalomonMain.loadScript(src).then(resolve).catch(reject);
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
      s.onerror = reject;
      document.body.appendChild(s);
    });
  }

  function wire(id, handler) {
    var el = document.getElementById(id);
    if (!el || el.dataset.uiReconnected === "1") return;
    el.dataset.uiReconnected = "1";
    el.addEventListener(
      "click",
      function (e) {
        e.preventDefault();
        e.stopPropagation();
        try {
          handler(e);
        } catch (err) {
          console.error("[ui_boot_reconnect]", id, err);
        }
      },
      false
    );
  }

  function reconnect() {
    clearStuckLayers();

    wire("btn-settings", function () {
      function open() {
        if (window.SalomonSettings && window.SalomonSettings.toggle) {
          window.SalomonSettings.toggle();
        }
      }
      if (window.SalomonSettings) open();
      else load("/static/js/settings_manager.js").then(open);
    });

    wire("btn-aa", function () {
      function open() {
        if (window.SalomonUiManager && window.SalomonUiManager.toggle) {
          window.SalomonUiManager.toggle();
        }
      }
      if (window.SalomonUiManager) open();
      else {
        Promise.all([
          load("/static/js/ui_manager.js"),
          load("/static/js/script.js"),
          load("/static/js/input_engine.js"),
        ]).then(open);
      }
    });

    wire("btn-cam", function () {
      function go() {
        if (window.SalomonCamera && window.SalomonCamera.toggleCamera) {
          window.SalomonCamera.toggleCamera();
        }
      }
      if (window.SalomonCamera) go();
      else if (window.SalomonMain && window.SalomonMain.ensureCameraStack) {
        window.SalomonMain.ensureCameraStack().then(go);
      } else {
        Promise.all([
          load("/static/js/camera_logic.js"),
          load("/static/js/camera_full.js"),
          load("/static/js/camera_toggle_ui.js"),
        ]).then(go);
      }
    });

    wire("btn-nav-back", function () {
      if (window.SalomonBack && window.SalomonBack.onBackTap) {
        window.SalomonBack.onBackTap();
      } else if (window.SalomonBack && window.SalomonBack.neutralize) {
        window.SalomonBack.neutralize();
      }
    });

    /* Smart button: no duplicar gestos; solo asegurar módulo */
    var smart = document.getElementById("smart-button");
    if (smart && !window.SalomonSmartButton) {
      load("/static/js/components/SmartButton.js").catch(function () {});
    }
  }

  function boot() {
    clearStuckLayers();
    reconnect();
    /* Segunda pasada tras lazy load de main.js */
    setTimeout(reconnect, 400);
    setTimeout(clearStuckLayers, 800);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.SalomonUiReconnect = { clearStuckLayers: clearStuckLayers, reconnect: reconnect };
})();
