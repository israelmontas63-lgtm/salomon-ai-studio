/**
 * Salomón Autónomo — Fase 1 (Estado Vivo)
 * - Intercepta /api/chat → SSE solo para imagen o investigación
 * - Conversación / saludos → /api/chat (cerebro · INSTRUCCION_SISTEMA)
 * - Burbujas de estado: "Estoy pensando…", "buscando…", "sintetizando…"
 */
(function () {
  "use strict";

  var VERSION = "fase1-estado-vivo-1.1.0";
  var enabled = true;
  var statusEl = null;
  var lastInterim = "";

  function log() {
    try {
      console.info.apply(console, ["[Salomon Fase1]"].concat([].slice.call(arguments)));
    } catch (e) {}
  }

  function ensureStatusHost() {
    if (statusEl && document.body.contains(statusEl)) return statusEl;
    statusEl = document.getElementById("salomon-fase1-status");
    if (!statusEl) {
      statusEl = document.createElement("div");
      statusEl.id = "salomon-fase1-status";
      statusEl.setAttribute("role", "status");
      statusEl.setAttribute("aria-live", "polite");
      document.body.appendChild(statusEl);
    }
    return statusEl;
  }

  function showStatus(msg, etapa) {
    if (!msg) return;
    var el = ensureStatusHost();
    el.textContent = msg;
    el.dataset.etapa = etapa || "";
    el.classList.add("is-visible");
    clearTimeout(showStatus._t);
    showStatus._t = setTimeout(function () {
      if (el.dataset.etapa === "done") el.classList.remove("is-visible");
    }, 12000);
  }

  function hideStatus() {
    var el = document.getElementById("salomon-fase1-status");
    if (el) {
      el.classList.remove("is-visible");
      el.dataset.etapa = "done";
    }
  }

  function injectChatHint(text) {
    if (!text) return;
    var host =
      document.querySelector(".chat-body") ||
      document.querySelector("[data-chat-body]") ||
      document.querySelector(".messages") ||
      document.getElementById("root");
    if (!host) return;
    var prev = document.getElementById("salomon-fase1-bubble");
    if (prev) prev.remove();
    var bubble = document.createElement("div");
    bubble.id = "salomon-fase1-bubble";
    bubble.className = "salomon-fase1-bubble";
    bubble.textContent = text;
    host.appendChild(bubble);
    try {
      bubble.scrollIntoView({ block: "end", behavior: "smooth" });
    } catch (e) {}
  }

  function clearChatHint() {
    var prev = document.getElementById("salomon-fase1-bubble");
    if (prev) prev.remove();
  }

  function parseSseChunk(buffer, onEvent) {
    var parts = buffer.split("\n\n");
    var rest = parts.pop() || "";
    for (var i = 0; i < parts.length; i++) {
      var block = parts[i];
      var lines = block.split("\n");
      for (var j = 0; j < lines.length; j++) {
        var line = lines[j];
        if (line.indexOf("data:") === 0) {
          var raw = line.slice(5).trim();
          if (!raw) continue;
          try {
            onEvent(JSON.parse(raw));
          } catch (e) {}
        }
      }
    }
    return rest;
  }

  async function streamFase1(bodyObj, signal) {
    showStatus("Estoy pensando…", "pensando");
    injectChatHint("Estoy pensando…");

    var res = await fetch("/api/autonoma/fase1/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(bodyObj),
      signal: signal,
      credentials: "same-origin",
    });
    if (!res.ok || !res.body) {
      throw new Error("fase1_stream_http_" + res.status);
    }

    var reader = res.body.getReader();
    var decoder = new TextDecoder();
    var buf = "";
    var finalPayload = null;

    while (true) {
      var step = await reader.read();
      if (step.done) break;
      buf += decoder.decode(step.value, { stream: true });
      buf = parseSseChunk(buf, function (ev) {
        if (!ev) return;
        if (ev.type === "status") {
          var msg = ev.mensaje || "Trabajando…";
          showStatus(msg, ev.etapa || "status");
          injectChatHint(msg);
          try {
            window.dispatchEvent(
              new CustomEvent("salomon:fase1-status", { detail: ev })
            );
          } catch (e) {}
        } else if (ev.type === "done") {
          finalPayload = ev;
        }
      });
    }

    clearChatHint();
    hideStatus();

    if (!finalPayload) {
      throw new Error("fase1_stream_sin_done");
    }

    // Forma compatible con ChatResponse que espera el React bundle
    return {
      texto: finalPayload.texto || "",
      exito: !!finalPayload.exito,
      session_id: finalPayload.session_id || bodyObj.session_id || null,
      metadata: Object.assign({ fase1: true }, finalPayload.metadata || {}),
      audio_base64: null,
      audio_mime: "audio/mpeg",
      tts_disponible: false,
    };
  }

  function isConversational(m) {
    var t = String(m || "").trim().toLowerCase();
    if (!t) return true;
    if (t.length < 12) return true;
    return /^(hola|hi|hey|buenas|buen[oa]s?\s|saludos|qué tal|que tal|cómo estás|como estas|buenos días|buenos dias|buenas tardes|buenas noches)/.test(
      t
    );
  }

  function looksLikeResearch(m) {
    var t = String(m || "").trim().toLowerCase();
    return /(qué es|que es|busca|investiga|según|segun|wikipedia|explica|analiza|cómo funciona|como funciona|fuentes|definición|definicion|por qué|porque)/.test(
      t
    );
  }

  function shouldUseFase1(url, init) {
    if (!enabled) return false;
    if (!url || String(url).indexOf("/api/chat") < 0) return false;
    if (String(url).indexOf("/api/chat/nuevo") >= 0) return false;
    if (!init || String(init.method || "GET").toUpperCase() !== "POST") return false;
    try {
      var body = typeof init.body === "string" ? JSON.parse(init.body) : null;
      if (!body) return false;
      if (body.fase1 === false) return false;
      if (body.fase1 === true) return true;
      // Foto → percepción Fase 1
      if (body.imagen_base64) return true;
      var m = String(body.mensaje || "").trim();
      // Conversación / saludo → cerebro (Estado Vivo / HD Cognitiva)
      if (isConversational(m)) return false;
      // Investigación con sustancia → Fase 1 (síntesis bajo núcleo)
      if (looksLikeResearch(m) || m.length >= 28) return true;
    } catch (e) {
      return false;
    }
    return false;
  }

  function installFetchBridge() {
    if (window.__salomonFase1Fetch) return;
    window.__salomonFase1Fetch = true;
    var orig = window.fetch.bind(window);
    window.fetch = function (input, init) {
      var url = typeof input === "string" ? input : (input && input.url) || "";
      init = init || {};
      if (!shouldUseFase1(url, init)) {
        return orig(input, init);
      }
      var bodyObj = {};
      try {
        bodyObj = JSON.parse(init.body || "{}");
      } catch (e) {
        return orig(input, init);
      }
      log("chat → fase1 stream");
      return streamFase1(bodyObj, init.signal).then(function (data) {
        return new Response(JSON.stringify(data), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      });
    };
  }

  function installSpeechInterim() {
    // Feedback en vivo sin romper el SpeechRecognition del bundle.
    window.addEventListener("salomon:fase1-escuchando", function (ev) {
      var t = (ev && ev.detail && ev.detail.texto) || "";
      if (!t) return;
      lastInterim = t;
      showStatus("Escuchando… " + String(t).slice(0, 42), "escuchando");
    });
    // Best-effort: fuerza interimResults en prototipo si existe
    try {
      var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SR && SR.prototype) {
        var desc = Object.getOwnPropertyDescriptor(SR.prototype, "interimResults");
        if (!desc || desc.writable || desc.set) {
          /* instancias nuevas pueden setear true desde VoiceButton / bridge */
        }
      }
    } catch (e) {}
    log("speech interim listener activo");
  }

  function injectCss() {
    if (document.getElementById("salomon-fase1-css")) return;
    var s = document.createElement("style");
    s.id = "salomon-fase1-css";
    s.textContent =
      "#salomon-fase1-status{position:fixed;left:50%;top:calc(58px + env(safe-area-inset-top,0px));" +
      "transform:translateX(-50%);z-index:120000;max-width:92vw;padding:8px 14px;border-radius:999px;" +
      "background:rgba(8,8,10,.82);border:1px solid rgba(212,175,55,.45);color:#f0d78c;" +
      "font:500 12px/1.3 Inter,system-ui,sans-serif;letter-spacing:.02em;opacity:0;pointer-events:none;" +
      "transition:opacity .25s ease;backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px)}" +
      "#salomon-fase1-status.is-visible{opacity:1}" +
      ".salomon-fase1-bubble{margin:8px 16px;padding:10px 14px;border-radius:14px;" +
      "border:1px solid rgba(212,175,55,.35);background:rgba(0,0,0,.35);color:rgba(240,215,140,.92);" +
      "font:500 13px/1.4 Inter,system-ui,sans-serif;animation:fase1Pulse 1.6s ease-in-out infinite}" +
      "@keyframes fase1Pulse{0%,100%{opacity:.7}50%{opacity:1}}";
    document.head.appendChild(s);
  }

  function boot() {
    injectCss();
    installFetchBridge();
    installSpeechInterim();
    window.SalomonFase1 = {
      version: VERSION,
      enable: function () {
        enabled = true;
      },
      disable: function () {
        enabled = false;
      },
      stream: streamFase1,
      status: showStatus,
    };
    log("activo", VERSION);
    try {
      fetch("/api/autonoma/fase1/estado", { cache: "no-store" })
        .then(function (r) {
          return r.json();
        })
        .then(function (d) {
          log("estado", d && d.fase, d && d.capacidades);
        })
        .catch(function () {});
    } catch (e) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
