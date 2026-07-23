/**
 * PROTOCOLO 4 CAPAS — reparación SIN secuestrar clics.
 * Causa del fallo anterior: capture + stopPropagation mataba settings/camera/SmartButton.
 * Esta versión SOLO limpia overlays y precarga el cerebro; no intercepta eventos.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  function log() {
    try {
      console.info.apply(console, ["[SalomonReconexion]"].concat([].slice.call(arguments)));
    } catch (_) {}
  }

  /** [1/4] DOM — quitar capas/overlays que bloquean toques */
  function repararCapaBaseDom() {
    log("[1/4] Capa Base / DOM");
    var body = document.body;
    if (!body) return;

    var camAlive =
      window.SalomonCamera &&
      window.SalomonCamera.isActive &&
      window.SalomonCamera.isActive();

    body.classList.remove(
      "input-sheet-open",
      "control-layer-open",
      "chat-drawer-open",
      "ai-active",
      "salomon-processing"
    );
    if (!camAlive) {
      body.classList.remove(
        "vision-immersive",
        "vision-mode-active",
        "camera-ui-elevated"
      );
      body.removeAttribute("data-vision");
    }
    body.setAttribute("data-ai-active", "false");

    var stage = document.getElementById("camera-stage");
    if (stage && !camAlive) {
      stage.classList.remove(
        "is-visible",
        "is-immersive",
        "is-flash",
        "is-mirror",
        "is-selfie"
      );
      stage.setAttribute("aria-hidden", "true");
      /* Sin cssText sticky: el CSS (camera_hud) ya oculta :not(.is-visible) */
      try {
        stage.removeAttribute("style");
      } catch (_) {}
    }

    var hud = document.getElementById("camera-controls-container");
    if (hud && !camAlive) {
      try {
        hud.style.pointerEvents = "none";
      } catch (_) {}
    }

    ["control-layer", "chat-history-drawer", "chat-drawer"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.classList.remove("is-open");
    });
    try {
      document.querySelectorAll(".chat-drawer.is-open").forEach(function (el) {
        el.classList.remove("is-open");
      });
    } catch (_) {}

    var input = document.getElementById("input-layer");
    if (input) {
      input.classList.remove("is-open");
      input.setAttribute("aria-hidden", "true");
    }

    var wrap = document.getElementById("cam-wrap");
    if (wrap && !camAlive) wrap.classList.remove("is-active", "is-elevated");

    /* Liberar lock de IA atascado (sin destruir cámara activa) */
    try {
      if (
        window.SalomonAILock &&
        window.SalomonAILock.isActive &&
        window.SalomonAILock.isActive()
      ) {
        if (window.SalomonAILock.release) {
          window.SalomonAILock.release("ui_reconnect_boot");
          log("AI lock liberado");
        }
      }
      try {
        document.body.classList.remove("ai-active", "salomon-processing");
      } catch (_) {}
    } catch (_) {}
  }

  /** [2/4] Listeners — NO hijack; solo verificar que los nodos existen */
  function repararCapaEventListeners() {
    log("[2/4] Capa de Event Listeners (sin interceptar)");
    var ids = [
      "btn-cam",
      "btn-aa",
      "btn-settings",
      "btn-nav-back",
      "smart-button",
      "btn-dock-flip",
    ];
    ids.forEach(function (id) {
      var el = document.getElementById(id);
      log("  nodo", id, el ? "OK" : "FALTA");
      if (!el) return;
      el.style.pointerEvents = "auto";
      el.style.visibility = "visible";
      el.removeAttribute("disabled");
      el.setAttribute("aria-disabled", "false");
    });
  }

  /** [3/4] UI / z-index — refuerzo hit-test del dock */
  function repararCapaUiEstilos() {
    log("[3/4] Capa de UI / Estilos");
    var dock = document.getElementById("nav_bar_container");
    if (dock) {
      dock.style.pointerEvents = "auto";
      dock.style.opacity = "1";
      dock.style.visibility = "visible";
      dock.style.zIndex = "100055";
    }
    [
      "btn-cam",
      "btn-aa",
      "btn-settings",
      "btn-nav-back",
      "smart-button",
    ].forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      el.style.pointerEvents = "auto";
      el.style.zIndex = "100060";
      el.style.opacity = "1";
    });
  }

  function load(src) {
    return new Promise(function (resolve, reject) {
      if (window.SalomonMain && window.SalomonMain.loadScript) {
        window.SalomonMain.loadScript(src).then(resolve).catch(reject);
        return;
      }
      var key = src.split("?")[0];
      var existing = document.querySelector('script[data-salomon-src="' + key + '"]');
      if (existing && existing.dataset.ready === "1") {
        resolve();
        return;
      }
      var s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.dataset.salomonSrc = key;
      s.onload = function () {
        s.dataset.ready = "1";
        resolve();
      };
      s.onerror = reject;
      (document.body || document.documentElement).appendChild(s);
    });
  }

  /** [4/4] Inicialización — precargar cerebro; bindings nativos de cada módulo */
  function repararCapaInicializacionJs() {
    log("[4/4] Capa de Inicialización JS");
    var core = [
      "/static/js/ai_state_lock.js",
      "/static/js/settings_manager.js",
      "/static/js/back_button.js",
      "/static/js/ui_controller.js",
      "/static/js/components/SmartButton.js",
      "/static/js/ui_manager.js",
      "/static/js/script.js",
      "/static/js/input_engine.js",
      "/static/js/camera_logic.js",
      "/static/js/camera_full.js",
      "/static/js/camera_toggle_ui.js",
    ];

    var chain = Promise.resolve();
    core.forEach(function (src) {
      chain = chain.then(function () {
        return load(src).catch(function (err) {
          log("warn load", src, err && err.message);
        });
      });
    });

    return chain.then(function () {
      /* NO re-init si ya está vivo (evita listeners duplicados = open/close instantáneo) */
      log(">>> [EXITO] Cerebro enlazado", {
        settings: !!window.SalomonSettings,
        camera: !!window.SalomonCamera,
        ui: !!window.SalomonUiManager,
        back: !!window.SalomonBack,
        smart: !!window.SalomonSmartButton,
        lock: !!window.SalomonAILock,
      });
    });
  }

  function forzarReconexionBotones() {
    log(">>> [ALERTA] Reconexion profesional (sin hijack de clics)");
    repararCapaBaseDom();
    repararCapaEventListeners();
    repararCapaUiEstilos();
    return repararCapaInicializacionJs();
  }

  function installGlobalErrorNet() {
    if (window.__salomonErrorNet) return;
    window.__salomonErrorNet = true;
    function maybeClearStuck(why) {
      try {
        var body = document.body;
        if (
          !body ||
          !(
            body.classList.contains("ai-active") ||
            body.classList.contains("salomon-processing")
          )
        ) {
          return;
        }
        if (window.SalomonAILock && window.SalomonAILock.clearStuckUiLayers) {
          window.SalomonAILock.clearStuckUiLayers(why);
        } else {
          repararCapaBaseDom();
        }
      } catch (_) {}
    }
    window.addEventListener("error", function () {
      maybeClearStuck("window_error");
    });
    window.addEventListener("unhandledrejection", function () {
      maybeClearStuck("unhandledrejection");
    });
  }

  function installImmersiveWatchdog() {
    if (window.__salomonImmersiveWatch) return;
    window.__salomonImmersiveWatch = true;
    function clearIfCameraDead() {
      try {
        var body = document.body;
        if (!body || !body.classList.contains("vision-immersive")) return;
        var camAlive =
          window.SalomonCamera &&
          window.SalomonCamera.isActive &&
          window.SalomonCamera.isActive();
        if (!camAlive) {
          body.classList.remove(
            "vision-immersive",
            "vision-mode-active",
            "camera-ui-elevated"
          );
          body.removeAttribute("data-vision");
          log("watchdog: limpió vision-immersive (cámara inactiva)");
        }
      } catch (_) {}
    }
    setInterval(clearIfCameraDead, 2800);
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible") clearIfCameraDead();
    });
  }

  function boot() {
    installGlobalErrorNet();
    installImmersiveWatchdog();
    forzarReconexionBotones().then(function () {
      /* Re-limpia overlays a T+500ms solo si la cámara no está viva */
      setTimeout(function () {
        var camAlive =
          window.SalomonCamera &&
          window.SalomonCamera.isActive &&
          window.SalomonCamera.isActive();
        if (!camAlive) repararCapaBaseDom();
      }, 500);
    });
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
