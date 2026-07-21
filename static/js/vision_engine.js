/**
 * Salomón AI — Vision Engine (ojos del agente)
 * Conecta frames de video → cerebro (/api/vision/brain-bridge).
 * Session State: al cerrar cámara se corta todo flujo visual.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  const VisionEngine = {
    /** Session State — privacidad */
    session: {
      active: false,
      /** standby: frames en buffer, cerebro en silencio cognitivo */
      mode: "off", // off | standby | analytical
      visionChannel: false,
      analyticalStreaming: false,
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
        // Standby: solo buffer — NO llamar al modelo hasta comando de voz
        this.session.lastFrameDataUrl = dataUrl;
        this.session.lastFacing =
          (ev.detail && ev.detail.facingMode) || this.session.lastFacing;
      });
    },

    isActive() {
      return !!this.session.active;
    },

    _onVisionOpen(facingMode) {
      this.session.active = true;
      this.session.mode = "standby";
      this.session.analyticalStreaming = false;
      this.session.visionChannel = true;
      this.session.lastFacing = facingMode || "environment";
      this._startVisionChannel();
      try {
        document.body.classList.add("vision-standby");
        document.body.classList.remove("vision-analytical");
      } catch (_) {}
    },

    _onVisionClose() {
      // Corte inmediato de flujo visual (batería + privacidad)
      this.session.active = false;
      this.session.mode = "off";
      this.session.analyticalStreaming = false;
      this.session.visionChannel = false;
      this.session.lastFrameDataUrl = null;
      this._stopVisionChannel();
      try {
        document.body.classList.remove("vision-standby", "vision-analytical");
      } catch (_) {}
    },

    /**
     * Comando voz: "Activa el modo visión" / "¿puedes ver lo que está frente a mí?"
     * Activa streaming analítico + una mirada + TTS (Adam vía brain).
     */
    async engageAnalyticalStreaming(prompt) {
      const cam = window.SalomonCamera;
      if (window.SalomonAILock && window.SalomonAILock.activate) {
        try {
          window.SalomonAILock.activate("vision_analytical", { keepCamera: true });
        } catch (_) {}
      }
      if (!this.session.active) {
        if (cam && cam.openCamera) {
          try {
            await cam.openCamera();
          } catch (_) {}
        }
        await new Promise(function (r) {
          setTimeout(r, 350);
        });
        if (cam && cam._waitForVideoReady) {
          try {
            await cam._waitForVideoReady(2000);
          } catch (_) {}
        }
      }
      if (!this.session.active) {
        this._bubble(
          "bot",
          "No pude abrir la cámara. Activa el botón Cámara y repite el comando."
        );
        return {
          texto:
            "No pude abrir la cámara. Activa el botón Cámara y repite el comando.",
          exito: false,
        };
      }
      this.session.mode = "analytical";
      this.session.analyticalStreaming = true;
      this.session.visionChannel = true;
      this._startVisionChannel();
      try {
        document.body.classList.add("vision-analytical", "vision-mode-active");
        document.body.classList.remove("vision-standby");
      } catch (_) {}
      if (cam && cam.ensureSharpFocus) {
        try {
          await cam.ensureSharpFocus();
        } catch (_) {}
      }
      const texto =
        prompt ||
        "Salomón, ¿puedes ver lo que está frente a mí? Describe con precisión la escena " +
          "en primera persona («Sí, Israel, estoy viendo…»). Sé exacto; no inventes.";
      return this.lookNow(texto);
    },

    /**
     * "Okay, Salomón, desactiva el modo visual"
     */
    async disengageVisualMode() {
      this.session.analyticalStreaming = false;
      this.session.mode = this.session.active ? "standby" : "off";
      this.session.lastFrameDataUrl = null;
      this._stopVisionChannel();
      try {
        document.body.classList.remove("vision-analytical");
        if (this.session.active) document.body.classList.add("vision-standby");
      } catch (_) {}
      const cam = window.SalomonCamera;
      if (cam && cam.isActive && cam.isActive() && cam.closeCamera) {
        try {
          await cam.closeCamera();
        } catch (_) {}
      }
      this._bubble(
        "bot",
        "Modo visual desactivado. Vuelvo al chat — puedes enviarme una foto cuando quieras."
      );
      return true;
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

    /** Captura frame actual del video sin cortar el stream (JPEG/WebP comprimido). */
    captureCurrentFrame(quality) {
      if (!this.session.active) return null;
      const cam = window.SalomonCamera;
      if (!cam || !cam.video) return null;
      const video = cam.video;
      if (!video.videoWidth) return null;
      try {
        const w = video.videoWidth;
        const h = video.videoHeight;
        let tw = w;
        let th = h;
        const maxSide = 1280;
        if (Math.max(w, h) > maxSide) {
          const scale = maxSide / Math.max(w, h);
          tw = Math.round(w * scale);
          th = Math.round(h * scale);
        }
        const canvas = document.createElement("canvas");
        canvas.width = tw;
        canvas.height = th;
        const ctx = canvas.getContext("2d");
        const facing = cam.facingMode || this.session.lastFacing;
        if (facing === "user") {
          ctx.translate(tw, 0);
          ctx.scale(-1, 1);
        }
        ctx.drawImage(video, 0, 0, tw, th);
        const q = quality == null ? 0.82 : quality;
        let dataUrl = null;
        try {
          dataUrl = canvas.toDataURL("image/webp", q);
          if (!dataUrl || dataUrl.indexOf("image/webp") === -1) {
            dataUrl = canvas.toDataURL("image/jpeg", q);
          }
        } catch (_) {
          dataUrl = canvas.toDataURL("image/jpeg", q);
        }
        return dataUrl;
      } catch (_) {
        return null;
      }
    },

    /** Payload cross-modal: consulta + frame fresco para Flask. */
    async buildCrossModalPayload(mensaje) {
      const lock = window.SalomonAILock;
      if (lock && lock.prepareVisionPayload) {
        return lock.prepareVisionPayload(mensaje || "");
      }
      const frame = this.captureCurrentFrame(0.82);
      if (!frame) return null;
      const mimeMatch = String(frame).match(/^data:(image\/[\w.+-]+);base64,/i);
      const mime = mimeMatch ? mimeMatch[1] : "image/jpeg";
      const raw = String(frame).replace(/^data:image\/[\w.+-]+;base64,/i, "");
      this.session.lastFrameDataUrl = frame;
      return {
        imagen_base64: raw,
        image_frame: raw,
        imagen_mime: mime,
        vision_active: true,
      };
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
      // Autofocus inteligente según el contexto verbal (letra cerca / roca lejos)
      const cam = window.SalomonCamera;
      if (cam && cam.autoFocusFromText) {
        await cam.autoFocusFromText(prompt || "");
      }
      if (cam && cam.ensureSharpFocus) {
        try {
          await cam.ensureSharpFocus();
        } catch (_) {}
      }
      // Breve estabilización del zoom antes de capturar
      await new Promise(function (r) {
        setTimeout(r, 180);
      });
      const frame = this.captureCurrentFrame(0.9) || this.session.lastFrameDataUrl;
      if (!frame) {
        var failMsg =
          "Aún no tengo un frame claro. Espera un instante e inténtalo de nuevo.";
        this._bubble("bot", failMsg);
        return { texto: failMsg, exito: false };
      }
      this.session.lastFrameDataUrl = frame;
      const texto =
        prompt ||
        "Salomón, mira: describe con detalle lo que ves ahora mismo con tus ojos (cámara). " +
          "Responde en primera persona («Sí, Israel, estoy viendo…»).";
      return this.sendFrameToBrain(texto, frame);
    },

    async sendFrameToBrain(contexto, dataUrl) {
      if (!this.session.active) return null;
      if (this.session.busy) return null;
      this.session.busy = true;

      const mimeMatch = String(dataUrl || "").match(
        /^data:(image\/[\w.+-]+);base64,/i
      );
      const mime = mimeMatch ? mimeMatch[1] : "image/jpeg";
      const raw = String(dataUrl || "").replace(
        /^data:image\/[\w.+-]+;base64,/i,
        ""
      );
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
            imagen_mime: mime,
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
          // Dual: texto + Adam TTS (audio del bridge o /api/tts)
          try {
            if (
              window.SalomonVoiceLayer &&
              window.SalomonVoiceLayer.ensureSpeak
            ) {
              await window.SalomonVoiceLayer.ensureSpeak(data);
            } else if (data.audio_base64) {
              if (
                window.SalomonVoiceLayer &&
                window.SalomonVoiceLayer.playFromResponse
              ) {
                window.SalomonVoiceLayer.playFromResponse(data);
              } else {
                var mime = data.audio_mime || "audio/mpeg";
                var audio = new Audio(
                  "data:" + mime + ";base64," + data.audio_base64
                );
                audio.play().catch(function () {});
              }
            }
          } catch (_) {}
          return data;
        }
        var fail =
          data.detail
            ? String(data.detail)
            : "No pude interpretar la imagen. ¿Reintentamos?";
        this._bubble("bot", fail);
        return { texto: fail, exito: false };
      } catch (_) {
        if (typing) typing.remove();
        var errMsg = "Error de visión. Revisa la conexión.";
        this._bubble("bot", errMsg);
        return { texto: errMsg, exito: false };
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

      // Desactivar modo visual (voz)
      if (
        /\b(desactiva(r)?\s+(el\s+)?modo\s+visual|apaga\s+(el\s+)?modo\s+visual|desactiva(r)?\s+(la\s+)?visi[oó]n|okay,?\s*salom[oó]n,?\s*desactiva)\b/.test(
          low
        )
      ) {
        return { handled: true, type: "desactivar_visual", rest: t };
      }

      // Activar streaming analítico: "¿puedes ver lo que está frente a mí?"
      if (
        /\bpuedes\s+ver\b/.test(low) &&
        /\b(frente\s+a\s+m[ií]|delante\s+de\s+m[ií]|lo\s+que\s+est[aá])\b/.test(low)
      ) {
        return { handled: true, type: "ver_frente", rest: t };
      }
      if (
        /\b(salom[oó]n,?\s*)?(mira\s+lo\s+que\s+tengo\s+delante|observa\s+lo\s+que\s+est[aá]\s+frente)\b/.test(
          low
        )
      ) {
        return { handled: true, type: "ver_frente", rest: t };
      }

      if (
        window.SalomonVisionModeTrigger &&
        window.SalomonVisionModeTrigger.matches(t)
      ) {
        return { handled: true, type: "modo_vision", rest: t };
      }
      if (
        /\b(activa(r)?\s+(el\s+)?modo\s+visi[oó]n|modo\s+visi[oó]n|ojos\s+activos)\b/.test(
          low
        )
      ) {
        return { handled: true, type: "modo_vision", rest: t };
      }
      if (/\b(salom[oó]n,?\s*)?mira\b/.test(low) || /\bqu[eé]\s+ves\b/.test(low)) {
        return { handled: true, type: "mira", rest: t };
      }
      // micro / macro: solo comandos explícitos (evita secuestrar chat casual)
      if (/\b(enfoque\s+)?micro\b/.test(low) || /\benfoque\s+cerca\b/.test(low)) {
        return { handled: true, type: "micro", rest: t };
      }
      if (
        /\b(enfoque\s+)?macro\b/.test(low) ||
        /\benfoque\s+lejano\b/.test(low) ||
        /\bzoom\s+(lejos|lejano|distancia)\b/.test(low)
      ) {
        return { handled: true, type: "macro", rest: t };
      }
      return { handled: false };
    },

    async handleChatCommand(mensaje) {
      const cmd = this.parseCommand(mensaje);
      if (!cmd.handled) return false;

      if (cmd.type === "desactivar_visual") {
        await this.disengageVisualMode();
        return true;
      }

      if (cmd.type === "ver_frente") {
        await this.engageAnalyticalStreaming(cmd.rest);
        return true;
      }

      if (cmd.type === "modo_vision") {
        // "Activa el modo visión" → canal de fotogramas + descripción inmediata + Adam
        if (window.SalomonVisionModeTrigger) {
          await window.SalomonVisionModeTrigger.handleCommand(mensaje, {
            source: "vision_engine",
            analyze: true,
          });
          return true;
        }
        await this.engageAnalyticalStreaming(cmd.rest);
        return true;
      }

      if (cmd.type === "mira") {
        if (!this.session.analyticalStreaming) {
          this.session.analyticalStreaming = true;
          this.session.mode = "analytical";
        }
        await this.lookNow(cmd.rest);
        return true;
      }
      if (cmd.type === "macro" || cmd.type === "micro") {
        const cam = window.SalomonCamera;
        if (!cam || !cam.isActive()) {
          this._bubble(
            "bot",
            "Activa la cámara para ajustar el zoom " +
              (cmd.type === "micro" ? "de detalle (micro)" : "a distancia (macro)") +
              "."
          );
          return true;
        }
        const ok = await cam.setFocusMode(cmd.type);
        const zoom = cam.zoomLevel ? cam.zoomLevel.toFixed(1) + "x" : "";
        this._bubble(
          "bot",
          ok
            ? (cmd.type === "micro"
                ? "Enfoque micro (detalle cercano) "
                : "Enfoque macro (objeto lejano) ") +
                zoom +
                ". ¿Quieres que mire ahora?"
            : "Apliqué zoom digital; este dispositivo no expone control óptico de foco."
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
    try {
      window.addEventListener("salomon:camera-error", function (ev) {
        var detail = (ev && ev.detail) || {};
        var msg =
          detail.message ||
          "No pude usar la cámara. Revisa permisos — puedes seguir por texto.";
        VisionEngine._bubble("bot", msg);
      });
    } catch (_) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
