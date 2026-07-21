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
    focusMode: "continuous", // continuous | macro (lejos) | micro (cerca)
    zoomLevel: 1,
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

      // Portero: apagar cámara solo si la IA no pide mantener ojos (visión+voz)
      window.addEventListener("salomon:ai-lock", (ev) => {
        var d = (ev && ev.detail) || {};
        if (d.action !== "activate" || !this.isActive()) return;
        var keep =
          d.hardware === "camera_kept_for_vision" ||
          d.keepCamera === true ||
          d.keep_camera === true;
        if (keep) return;
        this.closeCamera();
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
        var msg = this._permissionErrorMessage(err);
        this._notify(msg);
        try {
          window.dispatchEvent(
            new CustomEvent("salomon:camera-error", {
              detail: {
                error: String((err && err.name) || err || "camera_error"),
                message: msg,
              },
            })
          );
        } catch (_) {}
      } finally {
        this._switching = false;
      }
    },

    _permissionErrorMessage(err) {
      var name = (err && err.name) || "";
      var text = String((err && err.message) || err || "");
      if (
        name === "NotAllowedError" ||
        name === "PermissionDeniedError" ||
        /permission|denied|notallowed/i.test(text)
      ) {
        return (
          "Permiso de cámara bloqueado. Actívalo en el navegador y vuelve a " +
          "tocar Cámara — Salomón sigue disponible por texto."
        );
      }
      if (name === "NotFoundError" || /not found|no device/i.test(text)) {
        return "No encontré una cámara en este dispositivo.";
      }
      if (name === "NotReadableError" || /in use|trackstart/i.test(text)) {
        return "La cámara está en uso por otra app. Ciérrala e inténtalo de nuevo.";
      }
      if (/getUserMedia no disponible/i.test(text)) {
        return "Este navegador no permite cámara. Usa Chrome/Edge o HTTPS.";
      }
      if (/camera_blocked_by_ai_priority/i.test(text)) {
        return "Cámara en espera: la IA está procesando. Reintenta en un momento.";
      }
      return "No se pudo abrir la cámara. Revisa los permisos del navegador.";
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
      this.zoomLevel = 1;
      if (this.video) {
        this.video.style.transform = "";
        this.video.classList.remove("is-zoom-micro", "is-zoom-macro", "is-zoom-reset");
      }
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
     * Zoom digital (+ óptico si el dispositivo expone zoom).
     * factor 1 = normal; >1 acerca el sujeto en el encuadre.
     */
    async setZoom(factor) {
      var f = Number(factor);
      if (!isFinite(f) || f < 1) f = 1;
      if (f > 4) f = 4;
      this.zoomLevel = f;

      if (this.video) {
        this.video.classList.remove("is-zoom-micro", "is-zoom-macro", "is-zoom-reset");
        if (f <= 1.05) {
          this.video.style.transform = "";
          this.video.classList.add("is-zoom-reset");
        } else {
          var mirror = this.facingMode === "user";
          this.video.style.transform =
            (mirror ? "scaleX(-1) " : "") + "scale(" + f.toFixed(2) + ")";
          // Clase según modo de foco (contrato micro/macro), no solo el factor
          if (this.focusMode === "macro") {
            this.video.classList.add("is-zoom-macro");
          } else if (this.focusMode === "micro") {
            this.video.classList.add("is-zoom-micro");
          } else {
            this.video.classList.add(f >= 2 ? "is-zoom-macro" : "is-zoom-micro");
          }
        }
      }

      if (!this.stream) return f > 1;
      var track = this.stream.getVideoTracks()[0];
      if (!track || typeof track.getCapabilities !== "function") return f > 1;
      var caps = track.getCapabilities() || {};
      if (!caps.zoom) return f > 1;
      var zMin = caps.zoom.min != null ? caps.zoom.min : 1;
      var zMax = caps.zoom.max != null ? caps.zoom.max : zMin;
      var target = zMin + (zMax - zMin) * Math.min(1, (f - 1) / 3);
      try {
        await track.applyConstraints({ advanced: [{ zoom: target }] });
        return true;
      } catch (_) {
        try {
          await track.applyConstraints({ zoom: target });
          return true;
        } catch (__) {
          return f > 1;
        }
      }
    },

    /**
     * Ajusta foco + zoom.
     * micro = detalle cercano (letra) | macro = objeto lejano (roca allá)
     */
    async setFocusMode(mode) {
      if (!this.stream && mode !== "continuous") {
        // Permite marcar modo aunque el stream aún arranca
        this.focusMode = mode || "continuous";
      }
      if (!this.stream) return false;
      const track = this.stream.getVideoTracks()[0];
      if (!track) return false;

      const caps = typeof track.getCapabilities === "function" ? track.getCapabilities() : {};
      const advanced = [];

      if (mode === "micro") {
        // Detalle cercano: foco cerca + zoom moderado
        this.focusMode = "micro";
        if (caps.focusMode && caps.focusMode.includes("manual")) {
          advanced.push({ focusMode: "manual" });
        } else if (caps.focusMode && caps.focusMode.includes("continuous")) {
          advanced.push({ focusMode: "continuous" });
        }
        if (caps.focusDistance) {
          const min = caps.focusDistance.min != null ? caps.focusDistance.min : 0;
          const max = caps.focusDistance.max != null ? caps.focusDistance.max : 1;
          const near = min + (max - min) * 0.06;
          advanced.push({ focusDistance: near });
        }
        await this.setZoom(1.85);
      } else if (mode === "macro" || mode === "distant_object_zoom") {
        // Objeto lejano: foco lejos + zoom digital fuerte
        this.focusMode = "macro";
        if (caps.focusMode && caps.focusMode.includes("continuous")) {
          advanced.push({ focusMode: "continuous" });
        } else if (caps.focusMode && caps.focusMode.includes("manual")) {
          advanced.push({ focusMode: "manual" });
        }
        if (caps.focusDistance) {
          const min = caps.focusDistance.min != null ? caps.focusDistance.min : 0;
          const max = caps.focusDistance.max != null ? caps.focusDistance.max : 1;
          const far = min + (max - min) * 0.9;
          advanced.push({ focusDistance: far });
        }
        await this.setZoom(2.45);
      } else {
        this.focusMode = "continuous";
        if (caps.focusMode && caps.focusMode.includes("continuous")) {
          advanced.push({ focusMode: "continuous" });
        }
        await this.setZoom(1);
      }

      window.dispatchEvent(
        new CustomEvent("salomon:focus-mode", {
          detail: { mode: this.focusMode, zoom: this.zoomLevel },
        })
      );

      if (!advanced.length) return this.zoomLevel > 1;

      try {
        await track.applyConstraints({ advanced: advanced });
        return true;
      } catch (_) {
        try {
          const flat = {};
          advanced.forEach(function (obj) {
            Object.keys(obj).forEach(function (k) {
              flat[k] = obj[k];
            });
          });
          await track.applyConstraints(flat);
          return true;
        } catch (__) {
          return this.zoomLevel > 1;
        }
      }
    },

    /**
     * Inferencia verbal → micro/macro/continuous.
     * "esa letra ahí mismo" → micro | "esa roca allá" → macro
     */
    inferFocusFromText(mensaje) {
      var low = (mensaje || "").toLowerCase();
      if (!low) return null;
      var micro =
        /\b(micro|letra|texto|detalle|peque[nñ]o|cerca|aqu[ií]\s+mismo|ah[ií]\s+mismo|zoom\s+cerca)\b/.test(
          low
        );
      var macro =
        /\b(macro|lejos|all[aá]|aquella|aquel|roca|monta[nñ]a|horizonte|objeto\s+lejano|enfoque\s+lejano|zoom\s+lejos|distant)\b/.test(
          low
        );
      if (micro && !macro) return "micro";
      if (macro && !micro) return "macro";
      if (micro && macro) {
        if (/\b(letra|texto|cerca|ah[ií]\s+mismo)\b/.test(low)) return "micro";
        return "macro";
      }
      return null;
    },

    async autoFocusFromText(mensaje) {
      var mode = this.inferFocusFromText(mensaje);
      if (!mode) return { applied: false, mode: null };
      var ok = await this.setFocusMode(mode);
      return { applied: !!ok || this.zoomLevel > 1, mode: mode, zoom: this.zoomLevel };
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
      // Bloqueo físico: no pedir getUserMedia si la IA manda (salvo keepCamera visión+voz)
      var lock = window.SalomonAILock;
      var allowVisionCam =
        lock &&
        typeof lock.allowsCameraDuringAi === "function" &&
        lock.allowsCameraDuringAi();
      if (lock && lock.isActive && lock.isActive() && !allowVisionCam) {
        throw new Error("camera_blocked_by_ai_priority");
      }
      this._stopStream();
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("getUserMedia no disponible");
      }

      const wIdeal = opts.fast ? 1280 : 1920;
      const hIdeal = opts.fast ? 720 : 1080;
      // Autofoco continuo + resolución nítida en el pedido inicial (no solo post-hoc)
      const constraints = {
        audio: false,
        video: {
          facingMode: { ideal: facingMode },
          width: { ideal: wIdeal, min: 640 },
          height: { ideal: hIdeal, min: 480 },
          frameRate: { ideal: 30, max: 30 },
          advanced: [
            { focusMode: "continuous" },
            { facingMode: facingMode },
          ],
        },
      };

      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia(constraints);
      } catch (err1) {
        // Fallback sin advanced (algunos navegadores rechazan focusMode en gUM)
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            audio: false,
            video: {
              facingMode: { ideal: facingMode },
              width: { ideal: wIdeal },
              height: { ideal: hIdeal },
            },
          });
        } catch (err2) {
          throw err2 || err1;
        }
      }
      this.stream = stream;

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

      if (!opts.skipFocus) {
        try {
          const mode =
            this.focusMode === "macro" || this.focusMode === "micro"
              ? this.focusMode
              : "continuous";
          // Aplicar autofoco de inmediato (frame nítido para el modelo)
          await this.setFocusMode(mode);
          await this.ensureSharpFocus();
        } catch (_) {}
      }
    },

    /**
     * Refuerza autofoco continuo + espera breve a que el sensor estabilice.
     * Llamar antes de capturar fotogramas para análisis visual.
     */
    async ensureSharpFocus() {
      if (!this.stream) return false;
      const track = this.stream.getVideoTracks()[0];
      if (!track) return false;
      try {
        const caps =
          typeof track.getCapabilities === "function"
            ? track.getCapabilities()
            : {};
        if (caps.focusMode && caps.focusMode.includes("continuous")) {
          try {
            await track.applyConstraints({
              advanced: [{ focusMode: "continuous" }],
            });
          } catch (_) {
            try {
              await track.applyConstraints({ focusMode: "continuous" });
            } catch (__) {}
          }
        }
        // Pequeña espera para que el AF termine antes del buffer
        await new Promise(function (r) {
          setTimeout(r, 180);
        });
        return true;
      } catch (_) {
        return false;
      }
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
