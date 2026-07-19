/**
 * Salomón AI — Smart Button (solo micrófono en IDLE)
 * Cuando Cámara Inteligente está activa: mic BLOQUEADO; el click es gatillo (camera_logic).
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  class SmartButton {
    constructor(root) {
      this.root = root;
      this.recognition = null;
      this.root.addEventListener("click", (e) => this.onClick(e));
    }

    onClick(e) {
      // Zero-Conflict: Control Layer abierto → silencio total
      if (document.body.classList.contains("control-layer-open")) return;
      if (window.SalomonSettings && window.SalomonSettings.isOpen()) return;
      // Aislamiento: cámara activa → no micrófono
      if (window.SalomonUI && window.SalomonUI.isMicBlocked()) {
        return;
      }
      if (window.SalomonCamera && window.SalomonCamera.isActive()) {
        return;
      }
      e.preventDefault();
      this.toggleMic();
    }

    toggleMic() {
      if (this.recognition) {
        this._stopMic();
        return;
      }
      this._startMic();
    }

    _startMic() {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SR) {
        this._notify("Micrófono de voz no disponible en este navegador.");
        return;
      }
      try {
        this.recognition = new SR();
        this.recognition.lang = "es-DO";
        this.recognition.interimResults = false;
        this.recognition.continuous = false;
        this.root.classList.add("is-listening", "is-active");
        this.recognition.onresult = (ev) => {
          const text =
            (ev.results[0] && ev.results[0][0] && ev.results[0][0].transcript) || "";
          if (text) {
            const input = document.getElementById("input-msg");
            if (input) {
              input.value = text;
              input.dispatchEvent(new Event("input", { bubbles: true }));
            }
            const form = document.getElementById("form-chat");
            if (form) form.requestSubmit();
          }
          this._stopMic();
        };
        this.recognition.onerror = () => this._stopMic();
        this.recognition.onend = () => this._stopMic();
        this.recognition.start();
      } catch (_) {
        this._notify("No se pudo iniciar el micrófono.");
        this._stopMic();
      }
    }

    _stopMic() {
      if (this.recognition) {
        try {
          this.recognition.onend = null;
          this.recognition.stop();
        } catch (_) {}
        this.recognition = null;
      }
      this.root.classList.remove("is-listening", "is-active");
    }

    _notify(msg) {
      const chat = document.getElementById("chat");
      if (!chat) return;
      const el = document.createElement("div");
      el.className = "bubble bot";
      el.textContent = msg;
      chat.appendChild(el);
      chat.scrollTop = chat.scrollHeight;
    }
  }

  function boot() {
    const root = document.getElementById("smart-button");
    if (!root) return;
    window.SalomonSmartButton = new SmartButton(root);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
