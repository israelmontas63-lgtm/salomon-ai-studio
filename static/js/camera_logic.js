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
        if (document.body.classList.contains("control-layer-open")) return;
        // request_ui_action: AI_PROCESSING → cámara no recibe encendido
        var gate = window.request_ui_action || (window.SalomonAILock && window.SalomonAILock.request_ui_action);
        if (gate && !gate("camera")) return;
        e.preventDefault();
        e.stopPropagation();
        this.toggleCamera();
      });

      if (this.btnFlip) {
        this.btnFlip.addEventListener("click", (e) => {
          if (document.body.classList.contains("control-layer-open")) return;
          var gateFlip =
            window.request_ui_action ||
            (window.SalomonAILock && window.SalomonAILock.request_ui_action);
          if (gateFlip && !gateFlip("flip")) return;
          e.preventDefault();
          e.stopPropagation();
          if (this.isActive()) this.flipCamera();
        });
      }

      if (smart) {
        smart.addEventListener(
          "click",
          (e) => {
            if (document.body.classList.contains("control-layer-open")) return;
            // IA tiene prioridad: no convertir el centro en gatillo durante lock
            if (window.SalomonAILock && window.SalomonAILock.isActive()) return;
            if (!this.isActive()) return;
            e.preventDefault();
            e.stopImmediatePropagation();
            this.disparar();
          },
          true
        );
      }

      this._emit(States.IDLE);

      // Portero: si la IA toma el control, apagar stream físico al instante
      window.addEventListener("salomon:ai-lock", (ev) => {
        var d = (ev && ev.detail) || {};
        if (d.action === "activate" && this.isActive()) {
          this.closeCamera();
        }
      });
    },

    isActive() {
      return this.state === States.CAMARA_ACTIVA || this.state === States.DISPARO;
    },

    isSelfie() {
      return this.facingMode === "user";
    },

    async toggleCamera() {
      var gate =
        window.request_ui_action ||
        (window.SalomonAILock && window.SalomonAILock.request_ui_action);
      if (gate && !gate("camera")) {
        this._notify("Cámara bloqueada: la IA está en uso.");
        return;
      }
      if (this.state === States.IDLE || this.state === States.OFF) {
        await this.openCamera();
      } else {
        await this.closeCamera();
      }
    },

    async openCamera() {
      var gate =
        window.request_ui_action ||
        (window.SalomonAILock && window.SalomonAILock.request_ui_action);
      if (gate && !gate("camera")) {
        this._notify("Cámara bloqueada: la IA está en uso.");
        return;
      }
      if (this._switching) return;
      this._switching = true;
      this.facingMode = "environment";
      this.focusMode = "continuous";
      try {
        // UI inmediata — stream en paralelo perceptivo
        if (this.camWrap) this.camWrap.classList.add("is-active");
        if (this.stage) this.stage.classList.add("is-visible");
        this._emit(States.CAMARA_ACTIVA);
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

      // Disparo UI inmediato — sin esperar al stream
      if (this.stage) {
        this.stage.classList.toggle("is-mirror", this.facingMode === "user");
        this.stage.classList.toggle("is-selfie", this.facingMode === "user");
      }
      this.state = States.CAMARA_ACTIVA;
      this._emit(States.CAMARA_ACTIVA);

      try {
        await this._startStream(this.facingMode, { fast: true, skipFocus: true });
        this._notify(
          this.facingMode === "user"
            ? "Modo Selfie activo. El gatillo sigue listo."
            : "Cámara trasera activa."
        );
      } catch (err) {
        this.facingMode = prev;
        if (this.stage) {
          this.stage.classList.toggle("is-mirror", prev === "user");
          this.stage.classList.toggle("is-selfie", prev === "user");
        }
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

      // Flash en 2 rAF (sin layout thrashing / offsetWidth)
      requestAnimationFrame(() => {
        if (this.stage) this.stage.classList.remove("is-flash");
        requestAnimationFrame(() => {
          if (this.stage) this.stage.classList.add("is-flash");
          // Encode JPEG fuera del frame crítico (~60 FPS)
          const encode = () => this._encodeCaptureFrame();
          if (window.SalomonMain && window.SalomonMain.deferHeavy) {
            window.SalomonMain.deferHeavy(encode);
          } else {
            setTimeout(encode, 0);
          }
          this.state = States.CAMARA_ACTIVA;
          this._emit(States.CAMARA_ACTIVA);
          setTimeout(() => {
            if (this.stage) this.stage.classList.remove("is-flash");
          }, 120);
        });
      });
    },

    _encodeCaptureFrame() {
      if (!this.video) return;
      var self = this;
      var mirror = this.facingMode === "user";
      var facingMode = this.facingMode;
      var focusMode = this.focusMode;

      function emit(dataUrl) {
        window.dispatchEvent(
          new CustomEvent("salomon:camera-capture", {
            detail: {
              dataUrl: dataUrl,
              facingMode: facingMode,
              focusMode: focusMode,
            },
          })
        );
      }

      function fallbackCanvas() {
        try {
          var w = self.video.videoWidth || 720;
          var h = self.video.videoHeight || 960;
          var canvas = document.createElement("canvas");
          canvas.width = w;
          canvas.height = h;
          var ctx = canvas.getContext("2d", { alpha: false });
          if (!ctx) return;
          if (mirror) {
            ctx.translate(w, 0);
            ctx.scale(-1, 1);
          }
          ctx.drawImage(self.video, 0, 0, w, h);
          emit(canvas.toDataURL("image/jpeg", 0.85));
        } catch (_) {
          self._notify("No se pudo capturar el frame.");
        }
      }

      // Worker + ImageBitmap si el dispositivo lo soporta (sin bloquear UI)
      if (
        typeof Worker !== "undefined" &&
        typeof createImageBitmap === "function" &&
        typeof OffscreenCanvas !== "undefined"
      ) {
        createImageBitmap(this.video)
          .then(function (bitmap) {
            try {
              if (!self._captureWorker) {
                self._captureWorker = new Worker("/static/js/workers/capture_worker.js");
              }
              var worker = self._captureWorker;
              var onMsg = function (ev) {
                worker.removeEventListener("message", onMsg);
                if (ev.data && ev.data.type === "ENCODE_DONE" && ev.data.dataUrl) {
                  emit(ev.data.dataUrl);
                } else {
                  fallbackCanvas();
                }
              };
              worker.addEventListener("message", onMsg);
              worker.postMessage(
                {
                  type: "ENCODE_FRAME",
                  bitmap: bitmap,
                  width: bitmap.width,
                  height: bitmap.height,
                  mirror: mirror,
                },
                [bitmap]
              );
            } catch (_) {
              fallbackCanvas();
            }
          })
          .catch(function () {
            fallbackCanvas();
          });
        return;
      }

      fallbackCanvas();
    },

    async _startStream(facingMode, opts) {
      opts = opts || {};
      // Bloqueo físico: no pedir getUserMedia si la IA manda
      if (window.SalomonAILock && window.SalomonAILock.isActive()) {
        throw new Error("camera_blocked_by_ai_priority");
      }
      this._stopStream();
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("getUserMedia no disponible");
      }

      const constraints = {
        audio: false,
        video: {
          facingMode: { ideal: facingMode },
          width: { ideal: opts.fast ? 960 : 1280 },
          height: { ideal: opts.fast ? 540 : 720 },
        },
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.stream = stream;

      if (!opts.skipFocus) {
        try {
          // Foco en idle — no bloquear el primer frame
          const self = this;
          const mode =
            this.focusMode === "macro" || this.focusMode === "micro"
              ? this.focusMode
              : "continuous";
          if (window.SalomonMain && window.SalomonMain.deferHeavy) {
            window.SalomonMain.deferHeavy(function () {
              self.setFocusMode(mode);
            });
          } else {
            setTimeout(function () {
              self.setFocusMode(mode);
            }, 0);
          }
        } catch (_) {}
      }

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
