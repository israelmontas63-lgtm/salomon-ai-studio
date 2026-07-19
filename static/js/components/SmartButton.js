/**
 * Salomón AI — Smart Button (control directo del cerebro + state lock)
 * IDLE: activa is_ai_active → mic → POST /api/ai-process (sin middleware UI).
 * CÁMARA: el gatillo sigue en camera_logic (capture); AI lock bloquea cámara al activarse.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  function lock() {
    return window.SalomonAILock || null;
  }

  class SmartButton {
    constructor(root) {
      this.root = root;
      this.recognition = null;
      this.root.addEventListener("click", (e) => this.onClick(e));
      window.addEventListener("salomon:ai-lock", (ev) => {
        var d = (ev && ev.detail) || {};
        if (d.action === "release") {
          this.root.classList.remove("is-ai-locked");
        }
        if (d.action === "activate") {
          this.root.classList.add("is-ai-locked");
        }
      });
    }

    onClick(e) {
      // Control Layer abierto → silencio
      if (document.body.classList.contains("control-layer-open")) return;
      if (window.SalomonSettings && window.SalomonSettings.isOpen()) return;

      // Cámara activa: el shutter lo maneja camera_logic (capture); no IA
      if (window.SalomonUI && window.SalomonUI.isMicBlocked()) return;
      if (window.SalomonCamera && window.SalomonCamera.isActive()) return;

      e.preventDefault();
      e.stopPropagation();

      var L = lock();
      // Segundo toque con IA activa → cierre / restauración
      if (L && L.isActive() && this.recognition) {
        this._stopMic();
        L.release("smart_button_cancel");
        return;
      }
      if (L && L.isActive() && !this.recognition) {
        L.release("smart_button_close");
        this.root.classList.remove("is-active", "is-listening", "is-ai-locked");
        return;
      }

      // Prioridad: activar state lock de inmediato
      if (L) L.activate("smart_button");
      this.root.classList.add("is-ai-locked", "is-active");
      this.toggleMic();
    }

    toggleMic() {
      if (this.recognition) {
        this._stopMic();
        var L = lock();
        if (L) L.release("mic_stop");
        return;
      }
      this._startMic();
    }

    _startMic() {
      var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SR) {
        // Sin mic: aún así priorizamos IA — si hay texto en input, cerebro directo
        this._sendFromInputOrNotify();
        return;
      }
      try {
        this.recognition = new SR();
        this.recognition.lang = "es-DO";
        this.recognition.interimResults = false;
        this.recognition.continuous = false;
        this.root.classList.add("is-listening", "is-active");
        this.recognition.onresult = (ev) => {
          var text =
            (ev.results[0] && ev.results[0][0] && ev.results[0][0].transcript) || "";
          this._stopMic(true);
          if (text) {
            this._callBrain(text);
          } else {
            var L = lock();
            if (L) L.release("empty_transcript");
          }
        };
        this.recognition.onerror = () => {
          this._stopMic(true);
          var L = lock();
          if (L) L.release("mic_error");
        };
        this.recognition.onend = () => {
          if (this.recognition) this._stopMic(true);
        };
        this.recognition.start();
      } catch (_) {
        this._notify("No se pudo iniciar el micrófono.");
        this._stopMic(true);
        var L2 = lock();
        if (L2) L2.release("mic_exception");
      }
    }

    _stopMic(keepLock) {
      if (this.recognition) {
        try {
          this.recognition.onend = null;
          this.recognition.stop();
        } catch (_) {}
        this.recognition = null;
      }
      this.root.classList.remove("is-listening");
      if (!keepLock) {
        this.root.classList.remove("is-active", "is-ai-locked");
      }
    }

    async _callBrain(text) {
      var L = lock();
      var chat = document.getElementById("chat");
      if (chat) {
        var userEl = document.createElement("div");
        userEl.className = "bubble user";
        userEl.textContent = text;
        chat.appendChild(userEl);
        var typing = document.createElement("div");
        typing.className = "bubble bot typing";
        typing.innerHTML =
          '<span class="typing-label">Salomón está pensando</span>' +
          '<span class="typing-dots" aria-hidden="true"><i></i><i></i><i></i></span>';
        chat.appendChild(typing);
        chat.scrollTop = chat.scrollHeight;
      }

      document.body.classList.add("salomon-processing");

      var result =
        L && L.callBrainDirect
          ? await L.callBrainDirect({ mensaje: text, reason: "smart_button_voice" })
          : await this._fallbackFetch(text);

      document.body.classList.remove("salomon-processing");
      this.root.classList.remove("is-active", "is-listening", "is-ai-locked");

      if (chat) {
        var typingEl = chat.querySelector(".bubble.typing");
        if (typingEl) typingEl.remove();
        var bot = document.createElement("div");
        bot.className = "bubble bot";
        var data = (result && result.data) || {};
        bot.textContent =
          (result && result.ok && data.texto) ||
          data.detail ||
          "No pude completar la respuesta. ¿Lo intentamos de nuevo?";
        chat.appendChild(bot);
        chat.scrollTop = chat.scrollHeight;
      }

      // Reproducir audio si el cerebro lo envió
      if (result && result.data && result.data.audio_base64) {
        try {
          var mime = result.data.audio_mime || "audio/mpeg";
          var audio = new Audio("data:" + mime + ";base64," + result.data.audio_base64);
          audio.play().catch(function () {});
        } catch (_) {}
      }
    }

    async _fallbackFetch(text) {
      try {
        var res = await fetch("/api/ai-process", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mensaje: text }),
          credentials: "same-origin",
        });
        var data = await res.json().catch(function () {
          return {};
        });
        return { ok: res.ok, data: data };
      } catch (_) {
        return { ok: false, data: {} };
      } finally {
        var L = lock();
        if (L) L.release("fallback_done");
      }
    }

    _sendFromInputOrNotify() {
      var input = document.getElementById("input-msg");
      var text = (input && input.value ? input.value : "").trim();
      if (text) {
        if (input) input.value = "";
        this._callBrain(text);
        return;
      }
      this._notify("Micrófono no disponible. Escribe con Aa o usa un navegador con voz.");
      var L = lock();
      if (L) L.release("no_speech_api");
      this.root.classList.remove("is-active", "is-ai-locked");
    }

    _notify(msg) {
      var chat = document.getElementById("chat");
      if (!chat) return;
      var el = document.createElement("div");
      el.className = "bubble bot";
      el.textContent = msg;
      chat.appendChild(el);
      chat.scrollTop = chat.scrollHeight;
    }
  }

  function boot() {
    var root = document.getElementById("smart-button");
    if (!root) return;
    window.SalomonSmartButton = new SmartButton(root);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
