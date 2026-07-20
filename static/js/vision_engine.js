/**
 * Salomón AI — Vision Engine (ojos del agente)
 * Conecta frames de video → cerebro (/api/cognicion/vision).
 * Session State: al cerrar cámara se corta todo flujo visual.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  const VisionEngine = {
    /** Session State — privacidad */
    session: {
      active: false,
      visionChannel: false,
      lastFrameDataUrl: null,
      lastFacing: "environment",
      channelTimer: null,
      sessionId: null,
      busy: false,
    },

    init() {
      this.session.sessionId = localStorage.getItem("salomon_session_id") || null;

      window.addEventListener("salomon:camera-state", (ev) => {
        const state = (ev.detail && ev.detail.state) || "IDLE";
        if (state === "CAMARA_ACTIVA" || state === "DISPARO") {
          this._onVisionOpen(ev.detail.facingMode);
        } else if (state === "OFF" || state === "IDLE") {
          this._onVisionClose();
        }
      });

      window.addEventListener("salomon:camera-capture", (ev) => {
        if (!this.session.active) return;
        const dataUrl = ev.detail && ev.detail.dataUrl;
        if (!dataUrl) return;
        this.session.lastFrameDataUrl = dataUrl;
        this.session.lastFacing = (ev.detail && ev.detail.facingMode) || this.session.lastFacing;
        // Gatillo de Visión: envía captura al cerebro
        this.sendFrameToBrain(
          "Analiza esta captura de mis ojos (cámara). Describe con precisión lo que ves.",
          dataUrl
        );
      });
    },

    isActive() {
      return !!this.session.active;
    },

    _onVisionOpen(facingMode) {
      this.session.active = true;
      this.session.visionChannel = true;
      this.session.lastFacing = facingMode || "environment";
      this._startVisionChannel();
    },

    _onVisionClose() {
      // Corte inmediato de flujo visual (batería + privacidad)
      this.session.active = false;
      this.session.visionChannel = false;
      this.session.lastFrameDataUrl = null;
      this._stopVisionChannel();
    },

    _startVisionChannel() {
      this._stopVisionChannel();
      // Canal de visión: refresca frame en memoria cada ~1.2s (no spam al API)
      this.session.channelTimer = setInterval(() => {
        if (!this.session.active || !this.session.visionChannel) return;
        const frame = this.captureCurrentFrame();
        if (frame) this.session.lastFrameDataUrl = frame;
      }, 1200);
    },

    _stopVisionChannel() {
      if (this.session.channelTimer) {
        clearInterval(this.session.channelTimer);
        this.session.channelTimer = null;
      }
    },

    /** Captura frame actual del video sin cortar el stream */
    captureCurrentFrame(quality) {
      if (!this.session.active) return null;
      const cam = window.SalomonCamera;
      if (!cam || !cam.video) return null;
      const video = cam.video;
      if (!video.videoWidth) return null;
      try {
        const w = video.videoWidth;
        const h = video.videoHeight;
        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        const facing = cam.facingMode || this.session.lastFacing;
        if (facing === "user") {
          ctx.translate(w, 0);
          ctx.scale(-1, 1);
        }
        ctx.drawImage(video, 0, 0, w, h);
        return canvas.toDataURL("image/jpeg", quality == null ? 0.85 : quality);
      } catch (_) {
        return null;
      }
    },

    /**
     * "Salomón, mira" — procesa el frame actual en tiempo real.
     */
    async lookNow(prompt) {
      if (!this.session.active) {
        this._bubble(
          "bot",
          "Activa mis ojos primero (botón Cámara) y luego dime «Salomón, mira»."
        );
        return null;
      }
      const frame = this.captureCurrentFrame(0.9) || this.session.lastFrameDataUrl;
      if (!frame) {
        this._bubble("bot", "Aún no tengo un frame claro. Espera un instante e inténtalo de nuevo.");
        return null;
      }
      this.session.lastFrameDataUrl = frame;
      const texto =
        prompt ||
        "Salomón, mira: describe con detalle lo que ves ahora mismo con tus ojos (cámara).";
      return this.sendFrameToBrain(texto, frame);
    },

    async sendFrameToBrain(contexto, dataUrl) {
      if (!this.session.active) return null;
      if (this.session.busy) return null;
      this.session.busy = true;

      const raw = (dataUrl || "").replace(/^data:image\/\w+;base64,/, "");
      const typing = this._bubble("bot", "Mirando…");
      if (typing) typing.classList.add("typing");

      try {
        var focusMode =
          (window.SalomonCamera && window.SalomonCamera.focusMode) || "continuous";
        // brain_bridge: canal rápido al núcleo (macro/micro + exclusividad AI)
        const res = await fetch("/api/vision/brain-bridge", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            imagen_base64: raw,
            imagen_mime: "image/jpeg",
            contexto: contexto,
            session_id: this.session.sessionId,
            focus_mode: focusMode,
            via_brain_bridge: true,
          }),
        });
        const data = await res.json().catch(function () {
          return {};
        });
        if (typing) typing.remove();
        if (data.session_id) {
          this.session.sessionId = data.session_id;
          localStorage.setItem("salomon_session_id", data.session_id);
        }
        if (res.ok && data.texto) {
          this._bubble("bot", data.texto);
          return data.texto;
        }
        this._bubble(
          "bot",
          data.detail ? String(data.detail) : "No pude interpretar la imagen. ¿Reintentamos?"
        );
        return null;
      } catch (_) {
        if (typing) typing.remove();
        this._bubble("bot", "Error de visión. Revisa la conexión.");
        return null;
      } finally {
        this.session.busy = false;
      }
    },

    /**
     * Detecta comandos de visión / foco en el texto del usuario.
     * return { handled, type, rest }
     */
    parseCommand(mensaje) {
      const t = (mensaje || "").trim();
      const low = t.toLowerCase();
      if (!low) return { handled: false };

      if (/\b(salom[oó]n,?\s*)?mira\b/.test(low) || /\bqu[eé]\s+ves\b/.test(low)) {
        return { handled: true, type: "mira", rest: t };
      }
      if (/\bmacro\b/.test(low)) {
        return { handled: true, type: "macro", rest: t };
      }
      if (/\bmicro\b/.test(low) || /\benfoque\s+lejano\b/.test(low)) {
        return { handled: true, type: "micro", rest: t };
      }
      return { handled: false };
    },

    async handleChatCommand(mensaje) {
      const cmd = this.parseCommand(mensaje);
      if (!cmd.handled) return false;

      if (cmd.type === "mira") {
        await this.lookNow(cmd.rest);
        return true;
      }
      if (cmd.type === "macro" || cmd.type === "micro") {
        const cam = window.SalomonCamera;
        if (!cam || !cam.isActive()) {
          this._bubble("bot", "Activa la cámara para ajustar el foco (" + cmd.type + ").");
          return true;
        }
        const ok = await cam.setFocusMode(cmd.type);
        this._bubble(
          "bot",
          ok
            ? "Foco " + cmd.type + " aplicado. ¿Quieres que mire ahora?"
            : "Este dispositivo no expone control de foco; mantengo el enfoque automático."
        );
        return true;
      }
      return false;
    },

    _bubble(role, text) {
      const chat = document.getElementById("chat");
      if (!chat) return null;
      const el = document.createElement("div");
      el.className = "bubble " + (role === "user" ? "user" : "bot");
      el.textContent = text;
      chat.appendChild(el);
      chat.scrollTop = chat.scrollHeight;
      return el;
    },
  };

  function boot() {
    VisionEngine.init();
    window.SalomonVision = VisionEngine;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
