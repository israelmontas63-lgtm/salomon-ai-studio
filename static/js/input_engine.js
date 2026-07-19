/**
 * Salomón AI — Input Engine (motor activo)
 * Botón ▶ / Enter → POST /api/process (alias /api/ai-process)
 * Loading + errores sin colgar la UI.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  var API_PROCESS = "/api/process";

  const InputEngine = {
    form: null,
    input: null,
    sendBtn: null,
    chat: null,
    sessionId: null,
    busy: false,

    init() {
      this.form = document.getElementById("form-chat");
      this.input = document.getElementById("input-msg");
      this.sendBtn = document.getElementById("input-send");
      this.chat = document.getElementById("chat");
      this.sessionId = localStorage.getItem("salomon_session_id") || null;
      if (!this.form || !this.input) return;

      this.form.addEventListener("submit", (e) => {
        e.preventDefault();
        this.submit();
      });

      this.input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.submit();
        }
      });

      if (this.sendBtn) {
        this.sendBtn.addEventListener("click", (e) => {
          e.preventDefault();
          this.submit();
        });
      }

      window.SalomonInput = this;
      this._probeMotor();
    },

    _probeMotor() {
      fetch("/api/motor/estado", { cache: "no-store" })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          window.SalomonMotor = data;
          if (data && data.listo === false) {
            console.warn("[SalomonMotor]", data.mensaje || "API key no configurada");
          } else {
            console.info("[SalomonMotor] listo", data && data.provider);
          }
        })
        .catch(function () {
          /* silencioso en boot */
        });
    },

    setLoading(on) {
      this.busy = !!on;
      document.body.classList.toggle("salomon-processing", this.busy);
      if (this.sendBtn) {
        this.sendBtn.disabled = this.busy;
        this.sendBtn.classList.toggle("is-loading", this.busy);
        this.sendBtn.setAttribute("aria-busy", this.busy ? "true" : "false");
      }
      if (this.input) {
        this.input.disabled = this.busy;
      }
    },

    addBubble(text, role) {
      if (!this.chat) return null;
      const el = document.createElement("div");
      el.className = "bubble " + (role === "user" ? "user" : "bot");
      el.textContent = text;
      this.chat.appendChild(el);
      this.chat.scrollTop = this.chat.scrollHeight;
      return el;
    },

    clearField() {
      if (this.input) this.input.value = "";
    },

    _formatError(data, status) {
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
      if (data.texto) return String(data.texto);
      return "No pude completar la respuesta. ¿Lo intentamos de nuevo?";
    },

    async submit() {
      if (document.body.classList.contains("control-layer-open")) return;
      const msg = (this.input && this.input.value ? this.input.value : "").trim();
      if (!msg || this.busy) return;

      // Visión: mira / macro / micro
      if (window.SalomonVision && window.SalomonVision.parseCommand(msg).handled) {
        this.addBubble(msg, "user");
        this.clearField();
        this.setLoading(true);
        try {
          await window.SalomonVision.handleChatCommand(msg);
        } catch (_) {
          this.addBubble("No pude procesar el comando de visión.", "bot");
        } finally {
          this.setLoading(false);
          if (window.SalomonUiManager) window.SalomonUiManager.hide();
        }
        return;
      }

      this.setLoading(true);
      this.addBubble(msg, "user");
      this.clearField();
      if (window.SalomonUiManager) window.SalomonUiManager.hide();

      const typing = this.addBubble("Salomón está pensando…", "bot");
      if (typing) typing.classList.add("typing");

      try {
        const payload = { mensaje: msg, session_id: this.sessionId };
        if (
          window.SalomonVision &&
          window.SalomonVision.isActive() &&
          window.SalomonVision.session.lastFrameDataUrl
        ) {
          payload.imagen_base64 = window.SalomonVision.session.lastFrameDataUrl.replace(
            /^data:image\/\w+;base64,/,
            ""
          );
          payload.imagen_mime = "image/jpeg";
        }

        const res = await fetch(API_PROCESS, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          credentials: "same-origin",
        });
        const data = await res.json().catch(function () {
          return {};
        });
        if (typing) typing.remove();

        if (data.session_id) {
          this.sessionId = data.session_id;
          localStorage.setItem("salomon_session_id", data.session_id);
        }

        if (res.ok && data.exito !== false && data.texto) {
          this.addBubble(data.texto, "bot");
        } else if (res.status === 503 || (data && data.listo === false)) {
          this.addBubble(
            "El motor no tiene API key configurada. Añade GEMINI_API_KEY en .env o en Render Environment.",
            "bot"
          );
        } else {
          this.addBubble(this._formatError(data, res.status), "bot");
        }
      } catch (_) {
        if (typing) typing.remove();
        this.addBubble("Hubo un problema de conexión con el servidor. ¿Reintentamos?", "bot");
      } finally {
        this.setLoading(false);
      }
    },
  };

  function boot() {
    InputEngine.init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
