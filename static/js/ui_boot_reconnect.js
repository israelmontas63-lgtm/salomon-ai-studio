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

    body.classList.remove(
      "vision-immersive",
      "input-sheet-open",
      "control-layer-open",
      "ai-active",
      "camera-ui-elevated"
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
      stage.style.cssText =
        "display:none!important;pointer-events:none!important;width:0!important;height:0!important;z-index:-9999!important;";
    }

    var hud = document.getElementById("camera-controls-container");
    if (hud) hud.style.pointerEvents = "none";

    ["control-layer", "chat-drawer"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.classList.remove("is-open");
    });

    var input = document.getElementById("input-layer");
    if (input) {
      input.classList.remove("is-open");
      input.setAttribute("aria-hidden", "true");
    }

    var wrap = document.getElementById("cam-wrap");
    if (wrap) wrap.classList.remove("is-active", "is-elevated");

    /* Liberar lock de IA atascado (sin destruir el núcleo) */
    try {
      if (
        window.SalomonAILock &&
        window.SalomonAILock.isActive &&
        window.SalomonAILock.isActive() &&
        window.SalomonAILock.release
      ) {
        window.SalomonAILock.release("ui_reconnect_boot");
        log("AI lock liberado");
      }
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

  function boot() {
    forzarReconexionBotones().then(function () {
      setTimeout(repararCapaBaseDom, 500);
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
