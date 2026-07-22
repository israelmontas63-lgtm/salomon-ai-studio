/**
 * PROTOCOLO DE RECONEXIÓN NEURONAL — 4 capas
 * DOM → Event Listeners → UI/Z-index → Inicialización JS
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  var WIRED = false;

  function log() {
    try {
      console.info.apply(console, ["[SalomonReconexion]"].concat([].slice.call(arguments)));
    } catch (_) {}
  }

  /** Capa 1 — DOM / capas atascadas / overlays */
  function repararCapaBaseDom() {
    log("[1/4] Capa Base / DOM");
    var body = document.body;
    if (!body) return;
    body.classList.remove(
      "vision-immersive",
      "input-sheet-open",
      "control-layer-open",
      "ai-active",
      "camera-ui-elevated",
      "has-back-context",
      "neutralizer-armed"
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
      stage.style.display = "none";
      stage.style.pointerEvents = "none";
    }

    var hud = document.getElementById("camera-controls-container");
    if (hud) {
      hud.style.pointerEvents = "none";
    }

    ["control-layer", "chat-drawer", "input-layer"].forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      el.classList.remove("is-open");
      if (id === "input-layer") el.setAttribute("aria-hidden", "true");
    });

    var wrap = document.getElementById("cam-wrap");
    if (wrap) wrap.classList.remove("is-active", "is-elevated");

    /* Forzar hit-test en controles */
    [
      "btn-cam",
      "btn-aa",
      "btn-settings",
      "btn-nav-back",
      "btn-dock-flip",
      "smart-button",
      "nav_bar_container",
    ].forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      el.style.pointerEvents = "auto";
      el.style.visibility = "visible";
      el.style.opacity = "1";
      el.style.zIndex = id === "nav_bar_container" ? "100055" : "100060";
    });
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
      s.src = src + (src.indexOf("?") >= 0 ? "&" : "?") + "r=" + Date.now();
      s.async = true;
      s.dataset.salomonSrc = src;
      s.onload = function () {
        s.dataset.ready = "1";
        resolve();
      };
      s.onerror = function () {
        reject(new Error("fail " + src));
      };
      (document.body || document.documentElement).appendChild(s);
    });
  }

  function ensureCoreBrain() {
    return Promise.all([
      load("/static/js/ai_state_lock.js"),
      load("/static/js/settings_manager.js"),
      load("/static/js/back_button.js"),
      load("/static/js/ui_controller.js"),
      load("/static/js/components/SmartButton.js"),
      load("/static/js/ui_manager.js"),
      load("/static/js/script.js"),
      load("/static/js/input_engine.js"),
    ]).catch(function (err) {
      log("ensureCoreBrain partial", err && err.message);
    });
  }

  function ensureCameraBrain() {
    if (window.SalomonMain && window.SalomonMain.ensureCameraStack) {
      return window.SalomonMain.ensureCameraStack();
    }
    return Promise.all([
      load("/static/js/camera_logic.js"),
      load("/static/js/camera_full.js"),
      load("/static/js/camera_toggle_ui.js"),
      load("/static/js/vision_engine.js"),
    ]);
  }

  /** Capa 2 — Event listeners (delegación en captura) */
  function repararCapaEventListeners() {
    log("[2/4] Capa de Event Listeners");
    if (WIRED) return;
    WIRED = true;

    function handle(id, ev) {
      ev.preventDefault();
      ev.stopPropagation();
      log("tap", id);

      if (id === "btn-settings") {
        ensureCoreBrain().then(function () {
          if (window.SalomonSettings && window.SalomonSettings.toggle) {
            window.SalomonSettings.toggle();
          }
        });
        return;
      }
      if (id === "btn-aa") {
        ensureCoreBrain().then(function () {
          if (window.SalomonUiManager && window.SalomonUiManager.toggle) {
            window.SalomonUiManager.toggle();
          }
        });
        return;
      }
      if (id === "btn-cam" || id === "btn-dock-flip") {
        ensureCameraBrain().then(function () {
          if (id === "btn-dock-flip") {
            if (window.SalomonCamera && window.SalomonCamera.flipCamera) {
              window.SalomonCamera.flipCamera();
            }
            return;
          }
          if (window.SalomonCamera && window.SalomonCamera.toggleCamera) {
            window.SalomonCamera.toggleCamera();
          }
        });
        return;
      }
      if (id === "btn-nav-back") {
        ensureCoreBrain().then(function () {
          if (window.SalomonBack && window.SalomonBack.onBackTap) {
            window.SalomonBack.onBackTap();
          } else if (window.SalomonBack && window.SalomonBack.neutralize) {
            window.SalomonBack.neutralize();
          }
        });
        return;
      }
      if (id === "smart-button") {
        /* SmartButton tiene gestos propios; solo asegurar cerebro */
        ensureCoreBrain();
        return;
      }
    }

    document.addEventListener(
      "click",
      function (ev) {
        var t = ev.target;
        if (!t || !t.closest) return;
        var hit = t.closest(
          "#btn-cam, #btn-aa, #btn-settings, #btn-nav-back, #btn-dock-flip, #smart-button"
        );
        if (!hit || !hit.id) return;
        /* smart-button: no interceptar si ya tiene motor sináptico */
        if (hit.id === "smart-button" && hit.dataset.gestureEngine) {
          ensureCoreBrain();
          return;
        }
        handle(hit.id, ev);
      },
      true
    );

    document.addEventListener(
      "pointerup",
      function (ev) {
        var t = ev.target;
        if (!t || !t.closest) return;
        var hit = t.closest("#btn-cam, #btn-aa, #btn-settings, #btn-nav-back");
        if (!hit) return;
        /* refuerzo móvil: algunos WebViews tragan click */
        if (ev.pointerType === "touch") {
          handle(hit.id, ev);
        }
      },
      true
    );
  }

  /** Capa 3 — UI / z-index (refuerzo runtime) */
  function repararCapaUiEstilos() {
    log("[3/4] Capa de UI / Estilos (Z-index / Overlays)");
    repararCapaBaseDom();
  }

  /** Capa 4 — Inicialización JS / cerebro */
  function repararCapaInicializacionJs() {
    log("[4/4] Capa de Inicialización JS");
    ensureCoreBrain().then(function () {
      log("cerebro UI listo", {
        settings: !!window.SalomonSettings,
        ui: !!window.SalomonUiManager,
        back: !!window.SalomonBack,
        lock: !!window.SalomonAILock,
      });
    });
  }

  function forzarReconexionBotones() {
    log(">>> [ALERTA] Reconexion neuronal forzada");
    repararCapaBaseDom();
    repararCapaEventListeners();
    repararCapaUiEstilos();
    repararCapaInicializacionJs();
    log(">>> [EXITO] Botones enlazados al cerebro");
  }

  function boot() {
    forzarReconexionBotones();
    setTimeout(repararCapaBaseDom, 300);
    setTimeout(repararCapaBaseDom, 1000);
    setTimeout(repararCapaInicializacionJs, 500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.SalomonUiReconnect = {
    forzarReconexionBotones: forzarReconexionBotones,
    clearStuckLayers: repararCapaBaseDom,
    reconnect: forzarReconexionBotones,
  };
})();
