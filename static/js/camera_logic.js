/**
 * Salomón AI — Cámara Inteligente (State Machine)
 * IDLE ↔ CÁMARA_ACTIVA → DISPARO | OFF→IDLE
 * Gestiona stream + conmutación trasera/selfie.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  const States = Object.freeze({
    IDLE: "IDLE",
    CAMARA_ACTIVA: "CAMARA_ACTIVA",
    DISPARO: "DISPARO",
    OFF: "OFF",
  });

  const CameraLogic = {
    state: States.IDLE,
    stream: null,
    facingMode: "environment", // trasera por defecto
    video: null,
    stage: null,
    camWrap: null,
    btnCam: null,
    btnFlip: null,
    _switching: false,

    init() {
      this.btnCam = document.getElementById("btn-cam");
      this.btnFlip = document.getElementById("btn-flip");
      this.camWrap = document.getElementById("cam-wrap");
      this.stage = document.getElementById("camera-stage");
      this.video = document.getElementById("camera-video");
      const smart = document.getElementById("smart-button");

      if (!this.btnCam || !this.video || !this.stage) return;

      this.btnCam.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.toggleCamera();
      });

      if (this.btnFlip) {
        this.btnFlip.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          if (this.state === States.CAMARA_ACTIVA) this.flipCamera();
        });
      }

      if (smart) {
        smart.addEventListener(
          "click",
          (e) => {
            if (this.state !== States.CAMARA_ACTIVA) return;
            e.preventDefault();
            e.stopImmediatePropagation();
            this.disparar();
          },
          true
        );
      }

      this._emit(States.IDLE);
    },

    isActive() {
      return this.state === States.CAMARA_ACTIVA || this.state === States.DISPARO;
    },

    async toggleCamera() {
      if (this.state === States.IDLE || this.state === States.OFF) {
        await this.openCamera();
      } else {
        await this.closeCamera();
      }
    },

    async openCamera() {
      if (this._switching) return;
      this._switching = true;
      try {
        // UI inmediata (milisegundos)
        requestAnimationFrame(() => {
          if (this.camWrap) this.camWrap.classList.add("is-active");
          if (this.stage) this.stage.classList.add("is-visible");
          this._emit(States.CAMARA_ACTIVA);
        });

        await this._startStream(this.facingMode);
      } catch (err) {
        await this.closeCamera();
        this._notify("No se pudo abrir la cámara. Revisa los permisos.");
      } finally {
        this._switching = false;
      }
    },

    async closeCamera() {
      this._emit(States.OFF);
      requestAnimationFrame(() => {
        if (this.camWrap) this.camWrap.classList.remove("is-active");
        if (this.stage) {
          this.stage.classList.remove("is-visible", "is-flash", "is-mirror");
        }
      });
      this._stopStream();
      this.state = States.IDLE;
      this._emit(States.IDLE);
    },

    async flipCamera() {
      if (this.state !== States.CAMARA_ACTIVA || this._switching) return;
      this._switching = true;
      this.facingMode = this.facingMode === "environment" ? "user" : "environment";
      try {
        await this._startStream(this.facingMode);
      } catch (err) {
        this.facingMode = this.facingMode === "environment" ? "user" : "environment";
        this._notify("No se pudo girar la cámara.");
      } finally {
        this._switching = false;
      }
    },

    disparar() {
      if (this.state !== States.CAMARA_ACTIVA || !this.video) return;
      this._emit(States.DISPARO);

      requestAnimationFrame(() => {
        if (this.stage) {
          this.stage.classList.remove("is-flash");
          // reflow
          void this.stage.offsetWidth;
          this.stage.classList.add("is-flash");
        }

        try {
          const w = this.video.videoWidth || 720;
          const h = this.video.videoHeight || 960;
          const canvas = document.createElement("canvas");
          canvas.width = w;
          canvas.height = h;
          const ctx = canvas.getContext("2d");
          if (this.facingMode === "user") {
            ctx.translate(w, 0);
            ctx.scale(-1, 1);
          }
          ctx.drawImage(this.video, 0, 0, w, h);
          const dataUrl = canvas.toDataURL("image/jpeg", 0.92);
          window.dispatchEvent(
            new CustomEvent("salomon:camera-capture", {
              detail: { dataUrl, facingMode: this.facingMode },
            })
          );
          this._notify("Foto capturada. El stream sigue activo.");
        } catch (_) {
          this._notify("No se pudo capturar el frame.");
        }

        // Volver a CÁMARA_ACTIVA sin cortar stream
        this.state = States.CAMARA_ACTIVA;
        this._emit(States.CAMARA_ACTIVA);
        setTimeout(() => {
          if (this.stage) this.stage.classList.remove("is-flash");
        }, 200);
      });
    },

    async _startStream(facingMode) {
      this._stopStream();
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("getUserMedia no disponible");
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: { ideal: facingMode },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      });

      this.stream = stream;
      await new Promise((resolve, reject) => {
        requestAnimationFrame(() => {
          try {
            this.video.srcObject = stream;
            this.video.muted = true;
            this.video.playsInline = true;
            if (this.stage) {
              this.stage.classList.toggle("is-mirror", facingMode === "user");
            }
            const playPromise = this.video.play();
            if (playPromise && playPromise.then) {
              playPromise.then(resolve).catch(reject);
            } else {
              resolve();
            }
          } catch (err) {
            reject(err);
          }
        });
      });
    },

    _stopStream() {
      if (this.stream) {
        this.stream.getTracks().forEach((t) => t.stop());
        this.stream = null;
      }
      if (this.video) {
        this.video.srcObject = null;
      }
    },

    _emit(state) {
      this.state = state;
      window.dispatchEvent(
        new CustomEvent("salomon:camera-state", {
          detail: { state, facingMode: this.facingMode },
        })
      );
    },

    _notify(msg) {
      const chat = document.getElementById("chat");
      if (!chat) return;
      const el = document.createElement("div");
      el.className = "bubble bot";
      el.textContent = msg;
      chat.appendChild(el);
      chat.scrollTop = chat.scrollHeight;
    },
  };

  function boot() {
    CameraLogic.init();
    window.SalomonCamera = CameraLogic;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
