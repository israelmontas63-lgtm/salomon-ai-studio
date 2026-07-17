/**
 * Hub neuronal de visión — une captura UI ↔ APIs ↔ chat.
 * Sin debounce; listeners en capture; sin UI fragmentada.
 */
(function () {
  "use strict";

  var SESSION_KEY = "salomon_session_id";
  var busy = false;
  var bootOnce = false;
  var pendingPhotos = [];

  function camModeActive() {
    return (
      document.documentElement.classList.contains("salomon-cam-mode") ||
      !!(window.SalomonUIShield && document.getElementById("ui-camera-overlay"))
    );
  }

  function processPhotoDetail(detail) {
    if (!detail || (!detail.blob && !detail.dataUrl)) return;
    if (busy) {
      pendingPhotos.push(detail);
      return;
    }
    busy = true;
    var mode = detail.mode || "photo";
    queueMicrotask(function () {
      var job = mode === "vdcp" ? sendVdcp(detail) : sendPhotoVision(detail);
      job
        .catch(function (err) {
          var msg =
            err && err.message === "api_key"
              ? "Se requiere API key para visión."
              : "No pude procesar la captura.";
          injectBubbles(null, msg);
          console.warn("[Salomon Vision]", err && err.message);
        })
        .then(function () {
          busy = false;
          if (pendingPhotos.length) {
            processPhotoDetail(pendingPhotos.shift());
          }
        });
    });
  }

  function onPhoto(ev) {
    var detail = (ev && ev.detail) || {};
    if (!detail.blob && !detail.dataUrl) return;
    // Mientras la cámara está activa: cola — el chat/asistente no entra
    if (camModeActive() || detail.deferChat) {
      pendingPhotos.push(detail);
      console.info("[Salomon Vision] foto en cola (modo cámara)");
      return;
    }
    processPhotoDetail(detail);
  }

  function flushPendingOnCamClose() {
    if (!pendingPhotos.length) return;
    console.info("[Salomon Vision] cámara cerrada → procesar", pendingPhotos.length);
    var next = pendingPhotos.shift();
    processPhotoDetail(next);
  }

  function boot() {
    if (bootOnce) return;
    bootOnce = true;
    window.addEventListener("salomon:ui-photo", onPhoto, true);
    window.addEventListener("salomon:camera-close", flushPendingOnCamClose);
    window.SalomonVision = {
      version: "neural-sync-2-cam-queue",
      open: function (mode) {
        waitShieldThenOpen(mode || "photo");
      },
      openVdcp: function () {
        waitShieldThenOpen("vdcp");
      },
      close: function () {
        if (shield()) shield().closeCamera();
      },
      capture: function () {
        if (shield()) shield().capturePhoto();
      },
      toggle: function () {
        if (shield()) shield().toggleCameraDirection();
      },
    };
    console.info("[Salomon Vision] hub neuronal sincronizado (cola cámara)");
  }

  function apiKey() {
    return (
      localStorage.getItem("salomon_api_key_ui") ||
      window.__SALOMON_API_KEY__ ||
      ""
    );
  }

  function headers(json) {
    var h = {};
    if (json) h["Content-Type"] = "application/json";
    var k = apiKey();
    if (k) h["X-API-Key"] = k;
    var meta = document.querySelector('meta[name="salomon-api-key"]');
    if (meta && meta.content) h["X-API-Key"] = meta.content;
    return h;
  }

  function sessionId() {
    return localStorage.getItem(SESSION_KEY) || null;
  }

  function shield() {
    return window.SalomonUIShield || null;
  }

  function openNeural(mode) {
    var s = shield();
    if (s && typeof s.openNeuralCamera === "function") {
      s.openNeuralCamera({ mode: mode || "photo" });
      return true;
    }
    return false;
  }

  function waitShieldThenOpen(mode) {
    if (openNeural(mode)) return;
    var tries = 0;
    var id = setInterval(function () {
      tries += 1;
      if (openNeural(mode) || tries >= 20) clearInterval(id);
    }, 50);
  }

  function injectBubbles(userText, aiText) {
    if (
      document.documentElement.classList.contains("salomon-cam-mode") ||
      document.documentElement.getAttribute("data-salomon-camera-only") === "1"
    ) {
      console.info("[Salomon Vision] burbujas diferidas (modo cámara)");
      return;
    }
    var scroll =
      document.querySelector(".chat-scroll") ||
      document.querySelector(".messages") ||
      document.querySelector("[class*='chat-scroll']");
    if (!scroll) return;
    function row(role, text) {
      var wrap = document.createElement("div");
      wrap.className = "bubble-row bubble-row--" + (role === "user" ? "user" : "ai");
      var b = document.createElement("div");
      b.className = "bubble bubble--" + (role === "user" ? "user" : "ai");
      var t = document.createElement("div");
      t.className = "bubble__text";
      t.textContent = text;
      b.appendChild(t);
      wrap.appendChild(b);
      return wrap;
    }
    if (userText) scroll.appendChild(row("user", userText));
    if (aiText) scroll.appendChild(row("ai", aiText));
    scroll.scrollTop = scroll.scrollHeight;
  }

  function speakIfPossible(data) {
    // Nunca hablar mientras la cámara está activa (modo solo cámara)
    if (
      document.documentElement.classList.contains("salomon-cam-mode") ||
      document.documentElement.getAttribute("data-salomon-camera-only") === "1" ||
      document.getElementById("ui-camera-overlay")
    ) {
      console.info("[Salomon Vision] TTS bloqueado (modo cámara)");
      return;
    }
    if (!data) return;
    if (window.SalomonBridge && typeof window.SalomonBridge.ensureVoiceOut === "function") {
      window.SalomonBridge.ensureVoiceOut(data);
      return;
    }
    if (data.audio_base64) {
      try {
        var a = new Audio(
          "data:" + (data.audio_mime || "audio/mpeg") + ";base64," + data.audio_base64
        );
        a.play().catch(function () {});
      } catch (e) {}
    }
  }

  async function sendPhotoVision(detail) {
    var b64 = "";
    if (detail.dataUrl) b64 = String(detail.dataUrl).split(",")[1] || "";
    else if (detail.blob) {
      b64 = await new Promise(function (resolve, reject) {
        var r = new FileReader();
        r.onload = function () {
          resolve(String(r.result || "").split(",")[1] || "");
        };
        r.onerror = reject;
        r.readAsDataURL(detail.blob);
      });
    }
    if (!b64) throw new Error("sin_imagen");

    var res = await fetch("/api/cognicion/vision", {
      method: "POST",
      headers: headers(true),
      body: JSON.stringify({
        imagen_base64: b64,
        imagen_mime: "image/jpeg",
        contexto: "Analiza esta captura y dime qué ves con claridad.",
        session_id: sessionId(),
      }),
    });
    if (res.status === 401) throw new Error("api_key");
    var data = await res.json();
    if (data.session_id) localStorage.setItem(SESSION_KEY, data.session_id);
    injectBubbles("📷 Captura enviada a Salomón", data.texto || "Sin lectura visual.");
    speakIfPossible(data);
    window.dispatchEvent(new CustomEvent("salomon:vision-result", { detail: data }));
    return data;
  }

  async function sendVdcp(detail) {
    var b64 = "";
    if (detail.dataUrl) b64 = String(detail.dataUrl).split(",")[1] || "";
    else if (detail.blob) {
      b64 = await new Promise(function (resolve, reject) {
        var r = new FileReader();
        r.onload = function () {
          resolve(String(r.result || "").split(",")[1] || "");
        };
        r.onerror = reject;
        r.readAsDataURL(detail.blob);
      });
    }
    if (!b64) throw new Error("sin_imagen");

    var res = await fetch("/api/cognicion/vdcp", {
      method: "POST",
      headers: headers(true),
      body: JSON.stringify({
        imagen_base64: b64,
        max_foveas: 8,
        session_id: sessionId(),
      }),
    });
    if (res.status === 401) throw new Error("api_key");
    var data = await res.json();
    var texto =
      data.narrativa_consolidada ||
      (data.textos || []).join(" / ") ||
      data.error ||
      "Sin lectura VDCP";
    injectBubbles("◎ Captura VDCP", texto);
    window.dispatchEvent(new CustomEvent("salomon:vdcp-result", { detail: data }));
    if (shield() && shield().closeCamera) shield().closeCamera();
    return data;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
