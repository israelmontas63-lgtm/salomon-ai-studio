/**
 * Salomón AI — Cámara Inteligente + modos Selfie / Foco
 * IDLE → CÁMARA_ACTIVA (trasera) → flip → Selfie | OFF → IDLE
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
    facingMode: "environment",
    focusMode: "continuous", // continuous | macro | micro
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
          if (this.isActive()) this.flipCamera();
        });
      }

      if (smart) {
        smart.addEventListener(
          "click",
          (e) => {
            if (!this.isActive()) return;
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

    isSelfie() {
      return this.facingMode === "user";
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
      this.facingMode = "environment"; // trasera por defecto
      this.focusMode = "continuous";
      try {
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
          this.stage.classList.remove("is-visible", "is-flash", "is-mirror", "is-selfie");
        }
      });
      this._stopStream();
      this.facingMode = "environment";
      this.focusMode = "continuous";
      this.state = States.IDLE;
      this._emit(States.IDLE);
    },

    async flipCamera() {
      if (!this.isActive() || this._switching) return;
      this._switching = true;
      const prev = this.facingMode;
      this.facingMode = this.facingMode === "environment" ? "user" : "environment";
      try {
        await this._startStream(this.facingMode);
        // Mantener gatillo (CÁMARA_ACTIVA) en selfie
        this.state = States.CAMARA_ACTIVA;
        this._emit(States.CAMARA_ACTIVA);
        this._notify(
          this.facingMode === "user"
            ? "Modo Selfie activo. El gatillo sigue listo."
            : "Cámara trasera activa."
        );
      } catch (err) {
        this.facingMode = prev;
        this._notify("No se pudo girar la cámara.");
      } finally {
        this._switching = false;
      }
    },

    /**
     * Ajusta foco vía constraints getUserMedia / applyConstraints.
     * macro = cerca | micro = lejos / continuous
     */
    async setFocusMode(mode) {
      if (!this.stream) return false;
      const track = this.stream.getVideoTracks()[0];
      if (!track) return false;

      const caps = typeof track.getCapabilities === "function" ? track.getCapabilities() : {};
      const advanced = [];

      if (mode === "macro") {
        this.focusMode = "macro";
        if (caps.focusMode && caps.focusMode.includes("manual")) {
          advanced.push({ focusMode: "manual" });
        } else if (caps.focusMode && caps.focusMode.includes("continuous")) {
          advanced.push({ focusMode: "continuous" });
        }
        if (caps.focusDistance) {
          const min = caps.focusDistance.min != null ? caps.focusDistance.min : 0;
          const max = caps.focusDistance.max != null ? caps.focusDistance.max : 1;
          // Cerca del mínimo = macro
          const near = min + (max - min) * 0.08;
          advanced.push({ focusDistance: near });
        }
      } else if (mode === "micro") {
        this.focusMode = "micro";
        if (caps.focusMode && caps.focusMode.includes("continuous")) {
          advanced.push({ focusMode: "continuous" });
        } else if (caps.focusMode && caps.focusMode.includes("manual")) {
          advanced.push({ focusMode: "manual" });
        }
        if (caps.focusDistance) {
          const min = caps.focusDistance.min != null ? caps.focusDistance.min : 0;
          const max = caps.focusDistance.max != null ? caps.focusDistance.max : 1;
          const far = min + (max - min) * 0.85;
          advanced.push({ focusDistance: far });
        }
      } else {
        this.focusMode = "continuous";
        if (caps.focusMode && caps.focusMode.includes("continuous")) {
          advanced.push({ focusMode: "continuous" });
        }
      }

      if (!advanced.length) return false;

      try {
        await track.applyConstraints({ advanced: advanced });
        return true;
      } catch (_) {
        try {
          // Fallback sin advanced
          const flat = {};
          advanced.forEach(function (obj) {
            Object.keys(obj).forEach(function (k) {
              flat[k] = obj[k];
            });
          });
          await track.applyConstraints(flat);
          return true;
        } catch (__) {
          return false;
        }
      }
    },

    disparar() {
      if (this.state !== States.CAMARA_ACTIVA || !this.video) return;
      this._emit(States.DISPARO);

      requestAnimationFrame(() => {
        if (this.stage) {
          this.stage.classList.remove("is-flash");
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
              detail: {
                dataUrl: dataUrl,
                facingMode: this.facingMode,
                focusMode: this.focusMode,
              },
            })
          );
        } catch (_) {
          this._notify("No se pudo capturar el frame.");
        }

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

      const constraints = {
        audio: false,
        video: {
          facingMode: { ideal: facingMode },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.stream = stream;

      // Intentar foco continuo al abrir
      try {
        await this.setFocusMode(this.focusMode === "macro" || this.focusMode === "micro" ? this.focusMode : "continuous");
      } catch (_) {}

      await new Promise((resolve, reject) => {
        requestAnimationFrame(() => {
          try {
            this.video.srcObject = stream;
            this.video.muted = true;
            this.video.playsInline = true;
            if (this.stage) {
              this.stage.classList.toggle("is-mirror", facingMode === "user");
              this.stage.classList.toggle("is-selfie", facingMode === "user");
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
          detail: {
            state: state,
            facingMode: this.facingMode,
            focusMode: this.focusMode,
            selfie: this.facingMode === "user",
          },
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
