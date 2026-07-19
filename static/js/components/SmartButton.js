/**
 * Salomón AI — Smart Button (micrófono / cámara)
 * Círculo central 80px — área de comandos.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  const MODES = ["idle", "mic", "camera"];
  const ICONS = {
    idle: "/static/assets/icon-mic.svg",
    mic: "/static/assets/icon-mic.svg",
    camera: "/static/assets/icon-camera.svg",
  };

  class SmartButton {
    constructor(root) {
      this.root = root;
      this.mode = "idle";
      this.stream = null;
      this.recognition = null;
      this.icon = root.querySelector(".smart-button__icon");
      this.label = root.querySelector(".smart-button__label");
      this.root.addEventListener("click", () => this.cycle());
      this._render();
    }

    cycle() {
      const idx = MODES.indexOf(this.mode);
      const next = MODES[(idx + 1) % MODES.length];
      this.setMode(next);
    }

    async setMode(mode) {
      await this._stopAll();
      this.mode = mode;
      this._render();

      if (mode === "mic") {
        await this._startMic();
      } else if (mode === "camera") {
        await this._startCamera();
      }

      this.root.dispatchEvent(
        new CustomEvent("smartbutton:mode", {
          detail: { mode: this.mode },
          bubbles: true,
        })
      );
    }

    _render() {
      this.root.classList.toggle("is-active", this.mode !== "idle");
      this.root.classList.toggle("is-listening", this.mode === "mic");
      this.root.classList.toggle("is-camera", this.mode === "camera");
      if (this.icon) {
        this.icon.src = ICONS[this.mode] || ICONS.idle;
        this.icon.alt = this.mode;
      }
      if (this.label) {
        const texts = {
          idle: "Smart Button — tocar para micrófono",
          mic: "Escuchando — tocar para cámara",
          camera: "Cámara activa — tocar para idle",
        };
        this.label.textContent = texts[this.mode] || texts.idle;
        this.root.setAttribute("aria-label", this.label.textContent);
      }
    }

    async _startMic() {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SR) {
        this._notify("Micrófono de voz no disponible en este navegador.");
        this.mode = "idle";
        this._render();
        return;
      }
      try {
        this.recognition = new SR();
        this.recognition.lang = "es-DO";
        this.recognition.interimResults = false;
        this.recognition.continuous = false;
        this.recognition.onresult = (ev) => {
          const text = (ev.results[0] && ev.results[0][0] && ev.results[0][0].transcript) || "";
          if (text) {
            const input = document.getElementById("input-msg");
            if (input) {
              input.value = text;
              input.dispatchEvent(new Event("input", { bubbles: true }));
            }
            const form = document.getElementById("form-chat");
            if (form) form.requestSubmit();
          }
          this.setMode("idle");
        };
        this.recognition.onerror = () => this.setMode("idle");
        this.recognition.onend = () => {
          if (this.mode === "mic") this.setMode("idle");
        };
        this.recognition.start();
      } catch (err) {
        this._notify("No se pudo iniciar el micrófono.");
        this.mode = "idle";
        this._render();
      }
    }

    async _startCamera() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        this._notify("Cámara no disponible en este dispositivo.");
        this.mode = "idle";
        this._render();
        return;
      }
      try {
        this.stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
          audio: false,
        });
        let video = document.getElementById("smart-camera-preview");
        if (!video) {
          video = document.createElement("video");
          video.id = "smart-camera-preview";
          video.setAttribute("playsinline", "");
          video.muted = true;
          video.style.cssText =
            "position:fixed;left:50%;bottom:120px;transform:translateX(-50%);width:min(280px,80vw);border-radius:16px;border:2px solid #D4AF37;z-index:40;background:#000;";
          document.body.appendChild(video);
        }
        video.srcObject = this.stream;
        await video.play();
        video.hidden = false;
      } catch (err) {
        this._notify("Permiso de cámara denegado o no disponible.");
        this.mode = "idle";
        this._render();
      }
    }

    async _stopAll() {
      if (this.recognition) {
        try {
          this.recognition.onend = null;
          this.recognition.stop();
        } catch (_) {}
        this.recognition = null;
      }
      if (this.stream) {
        this.stream.getTracks().forEach((t) => t.stop());
        this.stream = null;
      }
      const video = document.getElementById("smart-camera-preview");
      if (video) {
        video.srcObject = null;
        video.hidden = true;
      }
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
