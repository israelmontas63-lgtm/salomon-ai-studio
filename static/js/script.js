/**
 * Salomón AI — script.js (puente UI ↔ backend)
 * enviarMensaje() → POST /api/chat → Gemini vía FastAPI (sin exponer API keys).
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  var API_CHAT = "/api/chat";
  var busy = false;
  var sessionId = localStorage.getItem("salomon_session_id") || null;

  function $(id) {
    return document.getElementById(id);
  }

  function chatEl() {
    return $("chat");
  }

  function inputEl() {
    return $("input-msg");
  }

  function sendBtn() {
    return $("input-send");
  }

  function addBubble(text, role, extraClass) {
    var chat = chatEl();
    if (!chat) return null;
    var el = document.createElement("div");
    el.className = "bubble " + (role === "user" ? "user" : "bot");
    if (extraClass) el.classList.add(extraClass);
    el.textContent = text;
    chat.appendChild(el);
    chat.scrollTop = chat.scrollHeight;
    return el;
  }

  function setLoading(on) {
    busy = !!on;
    document.body.classList.toggle("salomon-processing", busy);
    var btn = sendBtn();
    var input = inputEl();
    if (btn) {
      btn.disabled = busy;
      btn.classList.toggle("is-loading", busy);
      btn.setAttribute("aria-busy", busy ? "true" : "false");
    }
    if (input) input.disabled = busy;
  }

  function formatError(data, status) {
    if (!data) return "Error " + status + ". ¿Lo intentamos de nuevo?";
    var detail = data.detail;
    if (typeof detail === "string" && detail) return detail;
    if (Array.isArray(detail) && detail.length) {
      return detail
        .map(function (d) {
          return d.msg || d.message || JSON.stringify(d);
        })
        .join(" · ");
    }
    if (data.mensaje) return String(data.mensaje);
    return "No pude completar la respuesta. ¿Lo intentamos de nuevo?";
  }

  /**
   * Función principal: click ▶ o Enter.
   * Flujo: texto → POST /api/chat → insertar respuesta en el historial.
   */
  async function enviarMensaje() {
    if (document.body.classList.contains("control-layer-open")) return;
    // ui_layer_manager: chat Aa bloqueado mientras IA central procesa
    var gateChat =
      window.request_ui_action ||
      (window.SalomonAILock && window.SalomonAILock.request_ui_action);
    if (gateChat && !gateChat("chat_form")) return;
    if (busy) return;

    var input = inputEl();
    var msg = (input && input.value ? input.value : "").trim();
    if (!msg) return;

    // Gatillo Modo Visión (voz/texto) — independiente del neutralizador Back
    if (
      window.SalomonVisionModeTrigger &&
      window.SalomonVisionModeTrigger.matches(msg)
    ) {
      addBubble(msg, "user");
      if (input) input.value = "";
      setLoading(true);
      try {
        var eng = await window.SalomonVisionModeTrigger.handleCommand(msg, {
          source: "chat_aa",
        });
        addBubble((eng && eng.texto) || "Modo visión activo.", "bot");
      } catch (_) {
        addBubble("No pude activar el modo visión.", "bot");
      } finally {
        setLoading(false);
        if (window.SalomonUiManager) window.SalomonUiManager.hide();
      }
      return;
    }

    // Comandos de visión (si el módulo está cargado)
    if (window.SalomonVision && window.SalomonVision.parseCommand(msg).handled) {
      addBubble(msg, "user");
      if (input) input.value = "";
      setLoading(true);
      try {
        await window.SalomonVision.handleChatCommand(msg);
      } catch (_) {
        addBubble("No pude procesar el comando de visión.", "bot");
      } finally {
        setLoading(false);
        if (window.SalomonUiManager) window.SalomonUiManager.hide();
      }
      return;
    }

    addBubble(msg, "user");
    if (input) input.value = "";
    if (window.SalomonUiManager) window.SalomonUiManager.hide();

    setLoading(true);
    var typing = addBubble("Salomón está escribiendo…", "bot", "typing");
    if (typing) {
      typing.innerHTML =
        '<span class="typing-label">Salomón está escribiendo</span>' +
        '<span class="typing-dots" aria-hidden="true"><i></i><i></i><i></i></span>';
    }

    try {
      var payload = { mensaje: msg, session_id: sessionId };
      if (
        window.SalomonVision &&
        window.SalomonVision.isActive() &&
        window.SalomonVision.session &&
        window.SalomonVision.session.lastFrameDataUrl
      ) {
        payload.imagen_base64 = window.SalomonVision.session.lastFrameDataUrl.replace(
          /^data:image\/\w+;base64,/,
          ""
        );
        payload.imagen_mime = "image/jpeg";
      }

      var res = await fetch(API_CHAT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        credentials: "same-origin",
      });
      var data = await res.json().catch(function () {
        return {};
      });

      if (typing && typing.parentNode) typing.parentNode.removeChild(typing);

      if (data.session_id) {
        sessionId = data.session_id;
        localStorage.setItem("salomon_session_id", sessionId);
      }

      if (res.ok && data.exito !== false && data.texto) {
        addBubble(data.texto, "bot");
        reproducirAudioRespuesta(data);
      } else {
        addBubble(formatError(data, res.status), "bot");
      }
    } catch (_) {
      if (typing && typing.parentNode) typing.parentNode.removeChild(typing);
      addBubble("Hubo un problema de conexión con el servidor. ¿Reintentamos?", "bot");
    } finally {
      setLoading(false);
    }
  }

  var _audioActual = null;

  function reproducirAudioRespuesta(data) {
    if (!data || !data.audio_base64) {
      if (data && data.tts_disponible === false) {
        console.warn("[SalomonTTS] sin audio:", data.error || "tts_disponible=false");
      }
      return;
    }
    try {
      var mime = data.audio_mime || "audio/mpeg";
      var src = "data:" + mime + ";base64," + data.audio_base64;
      if (_audioActual) {
        try {
          _audioActual.pause();
        } catch (_) {}
      }
      var audio = new Audio(src);
      _audioActual = audio;
      var playPromise = audio.play();
      if (playPromise && typeof playPromise.catch === "function") {
        playPromise.catch(function (err) {
          console.warn("[SalomonTTS] autoplay bloqueado o fallo de reproducción:", err);
        });
      }
    } catch (err) {
      console.warn("[SalomonTTS] error al reproducir stream:", err);
    }
  }

  function wireEvents() {
    var form = $("form-chat");
    var input = inputEl();
    var btn = sendBtn();

    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        enviarMensaje();
      });
    }
    if (input) {
      input.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          enviarMensaje();
        }
      });
    }
    if (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        enviarMensaje();
      });
    }
  }

  function boot() {
    wireEvents();
    window.enviarMensaje = enviarMensaje;
    window.SalomonChat = { enviarMensaje: enviarMensaje };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
