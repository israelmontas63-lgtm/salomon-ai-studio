/**
 * Bridge blindado — Capa 1
 * NO reemplaza index-CJUgt2ya.css ni index-BdcDx9nN.js.
 * Solo: estados del núcleo, animaciones metálicas, cancelación, wrap de /api/chat.
 */
(function () {
  "use strict";

  var STATE = {
    IDLE: "IDLE",
    DICTATING: "DICTATING",
    CONVERSATION: "CONVERSATION",
    PROCESSING: "PROCESSING",
  };

  var state = STATE.IDLE;
  var btn = null;
  var abortControllers = new Set();
  var holdTimer = null;
  var pressed = false;
  var HOLD_MS = 300;

  function log() {
    try {
      console.info.apply(console, ["[Salomon Bridge]"].concat([].slice.call(arguments)));
    } catch (e) { /* noop */ }
  }

  function pulse(pattern) {
    try {
      if (!navigator.vibrate) return;
      // Chrome bloquea vibrate sin gesto de usuario (evita ruido en consola)
      if (navigator.userActivation && !navigator.userActivation.hasBeenActive) return;
      navigator.vibrate(pattern);
    } catch (e) { /* noop */ }
  }

  function ensureStructure(button) {
    if (!button || button.dataset.bridgeReady === "1") return button;
    button.dataset.bridgeReady = "1";
    button.classList.add("voice-btn");

    if (!button.querySelector(".voice-btn__clip")) {
      var glyphText = (button.textContent || "🎙").trim() || "🎙";
      button.textContent = "";
      var clip = document.createElement("span");
      clip.className = "voice-btn__clip";
      var fx = document.createElement("span");
      fx.className = "voice-btn__fx";
      fx.setAttribute("aria-hidden", "true");
      var glyph = document.createElement("span");
      glyph.className = "voice-btn__glyph";
      glyph.textContent = glyphText;
      clip.appendChild(fx);
      clip.appendChild(glyph);
      button.appendChild(clip);
    }

    // Contenedor fijo: no transformar el botón exterior
    button.style.transform = "none";
    return button;
  }

  function applyVisual(next) {
    if (!btn) return;
    btn.dataset.buttonState = next;
    btn.classList.toggle("voice-btn--spinning", next === STATE.DICTATING);
    btn.classList.toggle("voice-btn--shimmer", next === STATE.CONVERSATION);
    btn.classList.toggle("voice-btn--busy", next === STATE.PROCESSING);
    btn.classList.toggle("control-btn--recording", next !== STATE.IDLE);
  }

  function setState(next, reason) {
    if (state === next) return;
    state = next;
    applyVisual(next);
    log("estado →", next, reason || "");
    try {
      window.dispatchEvent(
        new CustomEvent("salomon:bridge-state", { detail: { state: next, reason: reason || "" } })
      );
    } catch (e) { /* noop */ }
  }

  function findButton() {
    return (
      document.querySelector("button.control-btn--main.voice-btn") ||
      document.querySelector("button.control-btn--main") ||
      document.querySelector(".controls-row .control-btn--main")
    );
  }

  function cancelAll(reason) {
    reason = reason || "user";
    abortControllers.forEach(function (ac) {
      try { ac.abort(); } catch (e) { /* noop */ }
    });
    abortControllers.clear();

    // Detener audio en reproducción
    document.querySelectorAll("audio").forEach(function (a) {
      try { a.pause(); } catch (e) { /* noop */ }
    });

    // Pedir al UI React que salga del modo voz (click = stopMode en el botón estable)
    if (btn && (btn.classList.contains("control-btn--recording") || state !== STATE.IDLE)) {
      try {
        btn.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, cancelable: true }));
        btn.click();
      } catch (e) {
        try { btn.click(); } catch (e2) { /* noop */ }
      }
    }

    setState(STATE.IDLE, "cancelAll:" + reason);
    pulse(25);
    log("cancelAll", reason);
  }

  function onPointerDown(e) {
    if (!btn || e.target !== btn && !btn.contains(e.target)) return;
    if (e.button != null && e.button !== 0) return;

    // Cancelación: toque mientras PROCESSING
    if (state === STATE.PROCESSING) {
      e.preventDefault();
      e.stopPropagation();
      cancelAll("tap-while-processing");
      return;
    }

    pressed = true;
    clearTimeout(holdTimer);
    holdTimer = setTimeout(function () {
      if (!pressed) return;
      // Hold visual = DICTATING (React también hace dictado con tap; hold refuerza visual)
      setState(STATE.DICTATING, "hold");
      pulse(12);
    }, HOLD_MS);
  }

  function onPointerUp(e) {
    if (!btn) return;
    clearTimeout(holdTimer);
    var wasHoldVisual = state === STATE.DICTATING && pressed;
    pressed = false;

    if (wasHoldVisual) {
      // Al soltar hold → idle visual; React gestiona el mic
      setTimeout(function () {
        if (state === STATE.DICTATING) setState(STATE.IDLE, "hold-end");
      }, 80);
      return;
    }

    // Si React pone recording, MutationObserver ajustará CONVERSATION/DICTATING
  }

  function syncFromReactClasses() {
    if (!btn) return;
    var recording = btn.classList.contains("control-btn--recording");
    var aria = btn.getAttribute("aria-pressed") === "true";

    if (state === STATE.PROCESSING) return; // fetch manda

    if (recording || aria) {
      // Sin hold activo: tratar como conversación/escucha (destellos)
      if (state !== STATE.DICTATING) {
        setState(STATE.CONVERSATION, "react-recording");
      }
    } else if (state === STATE.DICTATING || state === STATE.CONVERSATION) {
      setState(STATE.IDLE, "react-idle");
    }
  }

  function wrapFetch() {
    if (window.__salomonFetchWrapped) return;
    window.__salomonFetchWrapped = true;
    var orig = window.fetch.bind(window);

    window.fetch = function (input, init) {
      var url = typeof input === "string" ? input : (input && input.url) || "";
      var isChat =
        /\/api\/chat\b/.test(url) ||
        /\/api\/media\//.test(url) ||
        /\/api\/tts\b/.test(url);

      if (!isChat) return orig(input, init);

      var ac = null;
      try {
        ac = new AbortController();
        abortControllers.add(ac);
        init = init || {};
        if (!init.signal) {
          init = Object.assign({}, init, { signal: ac.signal });
        } else {
          // Encadenar abort externo
          var userSignal = init.signal;
          userSignal.addEventListener("abort", function () {
            try { ac.abort(); } catch (e) { /* noop */ }
          });
          init = Object.assign({}, init, { signal: ac.signal });
        }
      } catch (e) {
        ac = null;
      }

      setState(STATE.PROCESSING, "fetch:" + url);
      pulse(8);

      return orig(input, init).then(
        function (res) {
          if (ac) abortControllers.delete(ac);
          if (state === STATE.PROCESSING) setState(STATE.IDLE, "fetch-done");
          return res;
        },
        function (err) {
          if (ac) abortControllers.delete(ac);
          if (err && err.name === "AbortError") {
            setState(STATE.IDLE, "fetch-aborted");
          } else if (state === STATE.PROCESSING) {
            setState(STATE.IDLE, "fetch-error");
          }
          throw err;
        }
      );
    };
  }

  function bindButton(button) {
    btn = ensureStructure(button);
    applyVisual(state);

    btn.addEventListener("pointerdown", onPointerDown, true);
    btn.addEventListener("pointerup", onPointerUp, true);
    btn.addEventListener("pointercancel", function () {
      pressed = false;
      clearTimeout(holdTimer);
    }, true);

    var mo = new MutationObserver(syncFromReactClasses);
    mo.observe(btn, { attributes: true, attributeFilter: ["class", "aria-pressed"] });
    syncFromReactClasses();
    log("botón enlazado");
  }

  function boot() {
    wrapFetch();

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") cancelAll("escape");
    });

    var found = findButton();
    if (found) {
      bindButton(found);
    }

    // React monta después del splash/boot
    var rootMo = new MutationObserver(function () {
      if (btn && document.contains(btn)) return;
      var b = findButton();
      if (b) bindButton(b);
    });
    rootMo.observe(document.documentElement, { childList: true, subtree: true });
  }

  window.SalomonBridge = {
    getState: function () { return state; },
    STATES: STATE,
    cancelAll: cancelAll,
    version: "capa1-blindado-1",
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  log("cargado", window.SalomonBridge.version);
})();
