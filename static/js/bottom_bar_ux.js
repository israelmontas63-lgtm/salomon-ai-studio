/**
 * Bottom bar UX — elevación SOLO al tocar; reposo al soltar.
 * No desplaza permanentemente la barra por modos.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  var root = document.documentElement;
  var bar = null;
  var pointersDown = 0;

  function el(id) {
    return document.getElementById(id);
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

  function voiceActive() {
    var sb = el("smart-button");
    if (!sb) return false;
    return (
      sb.classList.contains("is-listening") ||
      sb.classList.contains("is-recording") ||
      sb.classList.contains("is-busy")
    );
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

  function syncModeOnly() {
    applyMode(resolveMode());
  }

  function bind() {
    bar = el("nav_bar_container");
    if (!bar) return;

    // Garantizar ancla fija en DOM (refuerzo por si CSS llega tarde)
    bar.style.setProperty("position", "fixed", "important");
    bar.style.setProperty("left", "50%", "important");
    bar.style.setProperty("bottom", "max(20px, env(safe-area-inset-bottom, 0px))", "important");
    bar.style.setProperty("z-index", "100040", "important");
    bar.style.setProperty("overflow", "visible", "important");

    function onDown(e) {
      if (!bar.contains(e.target)) return;
      pointersDown += 1;
      setElevated(true);
    }

    function onUp() {
      pointersDown = Math.max(0, pointersDown - 1);
      if (pointersDown === 0) setElevated(false);
    }

    bar.addEventListener("pointerdown", onDown, { passive: true });
    window.addEventListener("pointerup", onUp, { passive: true });
    window.addEventListener("pointercancel", onUp, { passive: true });
    window.addEventListener(
      "pointerdown",
      function (e) {
        if (!bar.contains(e.target) && pointersDown === 0) {
          setElevated(false);
        }
      },
      true
    );

    var obs = new MutationObserver(syncModeOnly);
    if (document.body) {
      obs.observe(document.body, { attributes: true, attributeFilter: ["class"] });
    }
    var layer = el("input-layer");
    if (layer) {
      obs.observe(layer, { attributes: true, attributeFilter: ["class", "aria-hidden"] });
    }
    var stage = el("camera-stage");
    if (stage) {
      obs.observe(stage, { attributes: true, attributeFilter: ["aria-hidden", "class"] });
    }
    var sb = el("smart-button");
    if (sb) {
      obs.observe(sb, { attributes: true, attributeFilter: ["class"] });
    }

    setElevated(false);
    syncModeOnly();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
