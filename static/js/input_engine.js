/**
 * Salomón AI — Input Engine
 * Limpia el campo, Enter + triángulo de envío → /api/ai-process
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
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

    async submit() {
      // Zero-Conflict: Control Layer abierto → no chat
      if (document.body.classList.contains("control-layer-open")) return;
      const msg = (this.input && this.input.value ? this.input.value : "").trim();
      if (!msg || this.busy) return;

      // Visión: mira / macro / micro
      if (window.SalomonVision && window.SalomonVision.parseCommand(msg).handled) {
        this.addBubble(msg, "user");
        this.clearField();
        this.busy = true;
        try {
          await window.SalomonVision.handleChatCommand(msg);
        } finally {
          this.busy = false;
          if (window.SalomonUiManager) window.SalomonUiManager.hide();
        }
        return;
      }

      this.busy = true;
      this.addBubble(msg, "user");
      this.clearField();
      // Reposo inmediato del sheet (estilo WhatsApp)
      if (window.SalomonUiManager) window.SalomonUiManager.hide();

      const typing = this.addBubble("Pensando…", "bot");
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

        const res = await fetch("/api/ai-process", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json().catch(function () {
          return {};
        });
        if (typing) typing.remove();
        if (data.session_id) {
          this.sessionId = data.session_id;
          localStorage.setItem("salomon_session_id", data.session_id);
        }
        if (res.ok && data.texto) {
          this.addBubble(data.texto, "bot");
        } else {
          this.addBubble(
            data.detail
              ? String(data.detail)
              : "No pude completar la respuesta. ¿Lo intentamos de nuevo?",
            "bot"
          );
        }
      } catch (_) {
        if (typing) typing.remove();
        this.addBubble("Hubo un problema de conexión. ¿Reintentamos?", "bot");
      } finally {
        this.busy = false;
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
