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

  function addBubble(text, role, extraClass, mediaUrl) {
    var chat = chatEl();
    if (!chat) return null;
    var el = document.createElement("div");
    el.className = "bubble " + (role === "user" ? "user" : "bot");
    if (extraClass) el.classList.add(extraClass);
    if (text) {
      var span = document.createElement("div");
      span.className = "bubble-text";
      span.textContent = text;
      el.appendChild(span);
    }
    if (mediaUrl) {
      var img = document.createElement("img");
      img.className = "bubble-gen-image";
      img.src = mediaUrl;
      img.alt = "Imagen generada por Salomón";
      img.loading = "lazy";
      el.appendChild(img);
    }
    chat.appendChild(el);
    chat.scrollTop = chat.scrollHeight;
    return el;
  }

  function mediaUrlFromResponse(data) {
    if (!data) return null;
    if (data.imagen_url) return data.imagen_url;
    var meta = data.metadata || {};
    var cog = meta.cognicion || {};
    var gen = cog.imagen_generada || meta.imagen_generada || null;
    if (gen && gen.url) return gen.url;
    if (data.url_relativa) return data.url_relativa;
    return null;
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

    // Comandos de visión (asegurar stack cámara antes de parsear)
    try {
      if (window.SalomonMain && window.SalomonMain.ensureCameraStack) {
        await window.SalomonMain.ensureCameraStack();
      }
    } catch (_) {}
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
      try {
        var prep =
          (window.SalomonAILock && window.SalomonAILock.prepareVisionPayload) ||
          null;
        if (prep) {
          var visPack = await prep(msg);
          if (visPack && visPack.imagen_base64) {
            payload.imagen_base64 = visPack.imagen_base64;
            payload.image_frame = visPack.image_frame || visPack.imagen_base64;
            payload.imagen_mime = visPack.imagen_mime || "image/jpeg";
          }
        } else if (
          window.SalomonVision &&
          window.SalomonVision.isActive &&
          window.SalomonVision.isActive()
        ) {
          var fresh =
            window.SalomonVision.captureCurrentFrame &&
            window.SalomonVision.captureCurrentFrame(0.82);
          var dataUrl =
            fresh ||
            (window.SalomonVision.session &&
              window.SalomonVision.session.lastFrameDataUrl);
          if (dataUrl) {
            payload.imagen_base64 = String(dataUrl).replace(
              /^data:image\/[\w.+-]+;base64,/i,
              ""
            );
            payload.image_frame = payload.imagen_base64;
            payload.imagen_mime = "image/jpeg";
          }
        }
      } catch (_) {}

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
        addBubble(data.texto, "bot", null, mediaUrlFromResponse(data));
        reproducirAudioRespuesta(data);
        window.dispatchEvent(
          new CustomEvent("salomon:chat-turn", {
            detail: {
              session_id: sessionId,
              preview: msg,
              mensaje: msg,
            },
          })
        );
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
    if (window.SalomonVoiceLayer && window.SalomonVoiceLayer.playFromResponse) {
      window.SalomonVoiceLayer.playFromResponse(data);
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
    window.SalomonChat = {
      enviarMensaje: enviarMensaje,
      getSessionId: function () {
        return sessionId;
      },
      setSessionId: function (sid) {
        sessionId = sid || null;
        if (sid) localStorage.setItem("salomon_session_id", sid);
        else localStorage.removeItem("salomon_session_id");
      },
      clearBubbles: function () {
        var chat = chatEl();
        if (chat) chat.innerHTML = "";
      },
      renderHistory: function (mensajes, sid) {
        if (sid) {
          sessionId = sid;
          localStorage.setItem("salomon_session_id", sid);
        }
        var chat = chatEl();
        if (!chat) return;
        chat.innerHTML = "";
        (mensajes || []).forEach(function (m) {
          if (!m || !m.contenido) return;
          if (m.rol !== "usuario" && m.rol !== "asistente") return;
          addBubble(m.contenido, m.rol === "usuario" ? "user" : "bot");
        });
        if (!mensajes || !mensajes.length) {
          addBubble("Conversación lista. ¿En qué te ayudo, Israel?", "bot");
        }
      },
      startFresh: function (sid, welcome) {
        if (sid) {
          sessionId = sid;
          localStorage.setItem("salomon_session_id", sid);
        } else {
          sessionId = null;
          localStorage.removeItem("salomon_session_id");
        }
        var chat = chatEl();
        if (chat) chat.innerHTML = "";
        addBubble(
          welcome || "Nuevo chat listo. ¿En qué te ayudo?",
          "bot"
        );
      },
      hydrateFromServer: async function () {
        if (!sessionId) return;
        try {
          var res = await fetch(
            "/api/historial?session_id=" +
              encodeURIComponent(sessionId) +
              "&t=" +
              Date.now(),
            { cache: "no-store", credentials: "same-origin" }
          );
          if (!res.ok) return;
          var data = await res.json();
          var msgs = (data.mensajes || []).filter(function (m) {
            return m.rol === "usuario" || m.rol === "asistente";
          });
          if (msgs.length) {
            window.SalomonChat.renderHistory(msgs, sessionId);
          }
        } catch (_) {}
      },
    };

    // Hidratar historial del session_id actual (si existe)
    setTimeout(function () {
      if (window.SalomonChat && window.SalomonChat.hydrateFromServer) {
        window.SalomonChat.hydrateFromServer();
      }
    }, 400);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
