/**
 * Bottom bar UX — elevación sincronizada + modos aislados (PWA templates).
 * No altera backend / 8 capas (muta_fuentes=false).
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  var LIFT_HOLD_MS = 120;
  var root = document.documentElement;
  var bar = null;
  var interacting = false;
  var lowerTimer = null;

  function el(id) {
    return document.getElementById(id);
  }

  function voiceActive() {
    var body = document.body;
    if (!body) return false;
    if (body.classList.contains("ai-active")) return true;
    if (body.classList.contains("salomon-processing")) return true;
    var sb = el("smart-button");
    if (!sb) return false;
    return (
      sb.classList.contains("is-listening") ||
      sb.classList.contains("is-recording") ||
      sb.classList.contains("is-busy") ||
      sb.getAttribute("aria-pressed") === "true"
    );
  }

  function cameraActive() {
    var body = document.body;
    if (body && body.classList.contains("vision-immersive")) return true;
    var stage = el("camera-stage");
    return Boolean(stage && stage.getAttribute("aria-hidden") === "false");
  }

  function textActive() {
    var layer = el("input-layer");
    return Boolean(layer && layer.classList.contains("is-open"));
  }

  function resolveMode() {
    if (cameraActive()) return "camera";
    if (voiceActive()) return "voice";
    if (textActive()) return "text";
    return "idle";
  }

  function applyMode(mode) {
    ["camera", "text", "voice"].forEach(function (m) {
      root.classList.remove("salomon-ui-mode-" + m);
    });
    if (mode && mode !== "idle") {
      root.classList.add("salomon-ui-mode-" + mode);
    }
    if (bar) bar.setAttribute("data-ui-mode", mode || "idle");
  }

  function setElevated(on) {
    if (!bar) return;
    bar.classList.toggle("is-controls-elevated", Boolean(on));
    root.classList.toggle("salomon-controls-elevated", Boolean(on));
  }

  function sync() {
    var mode = resolveMode();
    applyMode(mode);
    var hold = interacting || mode !== "idle";
    setElevated(hold);
  }

  function lift() {
    interacting = true;
    if (lowerTimer) {
      clearTimeout(lowerTimer);
      lowerTimer = null;
    }
    sync();
  }

  function scheduleLower() {
    interacting = false;
    if (lowerTimer) clearTimeout(lowerTimer);
    lowerTimer = setTimeout(function () {
      lowerTimer = null;
      sync();
    }, LIFT_HOLD_MS);
  }

  function bind() {
    bar = el("nav_bar_container");
    if (!bar) return;

    bar.addEventListener(
      "pointerdown",
      function () {
        lift();
      },
      { passive: true }
    );

    bar.addEventListener(
      "focusin",
      function () {
        lift();
      },
      true
    );

    document.addEventListener(
      "pointerdown",
      function (e) {
        if (!bar.contains(e.target)) {
          scheduleLower();
        }
      },
      true
    );

    // Observa modos existentes (cámara / input / AI) sin romper handlers
    var obs = new MutationObserver(function () {
      sync();
    });
    if (document.body) {
      obs.observe(document.body, {
        attributes: true,
        attributeFilter: ["class"],
      });
    }
    var layer = el("input-layer");
    if (layer) {
      obs.observe(layer, {
        attributes: true,
        attributeFilter: ["class", "aria-hidden"],
      });
    }
    var stage = el("camera-stage");
    if (stage) {
      obs.observe(stage, {
        attributes: true,
        attributeFilter: ["aria-hidden", "class"],
      });
    }
    var sb = el("smart-button");
    if (sb) {
      obs.observe(sb, {
        attributes: true,
        attributeFilter: ["class", "aria-pressed"],
      });
    }

    sync();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
