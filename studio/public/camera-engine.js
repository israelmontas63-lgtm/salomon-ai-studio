/**
 * Salomón CameraEngine v20.1.0 — MediaStreamManager (STABLE_PRODUCTION_READY).
 * Estados: INITIALIZING | READY | SWITCHING | ERROR
 * Filtro: forceReset si no READY en <2000ms.
 */
(function (global) {
  "use strict";

  var VERSION = "20.1.0";
  var STABLE_PRODUCTION_READY = true;
  var HARDWARE_GAP_MS = 320;
  var FADE_MS = 200;
  var READY_TIMEOUT_MS = 2000;

  var STATUS = {
    IDLE: "IDLE",
    INITIALIZING: "INITIALIZING",
    READY: "READY",
    SWITCHING: "SWITCHING",
    ERROR: "ERROR",
  };

  function logStatus(status, latencyMs, extra) {
    var lat = latencyMs == null ? "-" : Math.round(latencyMs) + "ms";
    var msg = "[CameraEngine] - Status: " + status + " - Latencia: " + lat;
    if (extra) msg += " - " + extra;
    try {
      console.info(msg);
    } catch (e) {}
  }

  function delay(ms) {
    return new Promise(function (r) {
      setTimeout(r, ms);
    });
  }

  function stopTracks(stream) {
    if (!stream) return;
    try {
      stream.getTracks().forEach(function (t) {
        try {
          t.stop();
        } catch (e) {}
      });
    } catch (e) {}
  }

  function waitFrame(video, timeoutMs) {
    return new Promise(function (resolve) {
      if (!video) return resolve(false);
      if (video.readyState >= 2 && video.videoWidth > 0) return resolve(true);
      var done = false;
      function cleanup() {
        try {
          video.removeEventListener("loadeddata", ok);
          video.removeEventListener("playing", ok);
        } catch (e) {}
      }
      var timer = setTimeout(function () {
        if (done) return;
        done = true;
        cleanup();
        resolve(video.readyState >= 2 && video.videoWidth > 0);
      }, timeoutMs || 2500);
      function ok() {
        if (done || !video.videoWidth) return;
        done = true;
        clearTimeout(timer);
        cleanup();
        resolve(true);
      }
      video.addEventListener("loadeddata", ok);
      video.addEventListener("playing", ok);
    });
  }

  function MediaStreamManager(options) {
    options = options || {};
    this.videoEl = options.videoEl || null;
    this.freezeEl = options.freezeEl || null;
    this.onStatus = typeof options.onStatus === "function" ? options.onStatus : null;

    this.status = STATUS.IDLE;
    this.facing = "environment";
    this.stream = null;
    this.track = null;
    this.deviceMap = { environment: null, user: null };
    this.devicesMapped = false;
    this.lastLatencyMs = 0;
    this._switchLock = false;
    this._bootSeq = 0;
    this._readyWatchdog = null;
    this._autoRetried = false;
  }

  MediaStreamManager.prototype._setStatus = function (status, latencyMs, extra) {
    this.status = status;
    if (latencyMs != null) this.lastLatencyMs = latencyMs;
    logStatus(status, latencyMs, extra);
    if (this.onStatus) {
      try {
        this.onStatus(status, this.lastLatencyMs, this.facing);
      } catch (e) {}
    }
  };

  MediaStreamManager.prototype.isReady = function () {
    return this.status === STATUS.READY;
  };

  MediaStreamManager.prototype.getFacing = function () {
    return this.facing;
  };

  MediaStreamManager.prototype.getStatus = function () {
    return this.status;
  };

  MediaStreamManager.prototype._clearReadyWatchdog = function () {
    if (this._readyWatchdog) {
      clearTimeout(this._readyWatchdog);
      this._readyWatchdog = null;
    }
  };

  /** Filtro de seguridad: limpia estado corrupto / streams huérfanos. */
  MediaStreamManager.prototype.forceReset = function (reason) {
    this._bootSeq += 1;
    this._clearReadyWatchdog();
    stopTracks(this.stream);
    this.stream = null;
    this.track = null;
    if (this.videoEl) {
      try {
        this.videoEl.srcObject = null;
      } catch (e) {}
    }
    this.hideFreeze();
    this._switchLock = false;
    this._setStatus(STATUS.ERROR, 0, "forceReset: " + (reason || "corrupt"));
    return true;
  };

  MediaStreamManager.prototype._constraints = function (facing) {
    var id = this.deviceMap[facing];
    if (id) {
      return {
        audio: false,
        video: {
          deviceId: { exact: id },
          width: { ideal: 1280 },
          height: { ideal: 720 },
          advanced: [{ deviceId: id }],
        },
      };
    }
    return {
      audio: false,
      video: {
        facingMode: { ideal: facing },
        width: { ideal: 1280 },
        height: { ideal: 720 },
        advanced: [{ facingMode: facing }],
      },
    };
  };

  MediaStreamManager.prototype._acquire = function (facing) {
    var primary = this._constraints(facing);
    return navigator.mediaDevices
      .getUserMedia(primary)
      .catch(function () {
        return navigator.mediaDevices.getUserMedia({
          audio: false,
          video: { facingMode: facing },
        });
      })
      .catch(function () {
        return navigator.mediaDevices.getUserMedia({
          audio: false,
          video: { facingMode: { exact: facing } },
        });
      })
      .catch(function () {
        return navigator.mediaDevices.getUserMedia({ audio: false, video: true });
      });
  };

  MediaStreamManager.prototype.mapDevices = function () {
    var self = this;
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
      return Promise.resolve(false);
    }
    return navigator.mediaDevices.enumerateDevices().then(function (list) {
      var videos = list.filter(function (d) {
        return d.kind === "videoinput" && d.deviceId;
      });
      var envId = null;
      var userId = null;
      videos.forEach(function (d) {
        var label = (d.label || "").toLowerCase();
        if (!userId && /front|user|selfie|facing\s*front|frontal/i.test(label)) userId = d.deviceId;
        if (!envId && /back|rear|environment|facing\s*back|trasera|world/i.test(label)) envId = d.deviceId;
      });
      if (!envId && videos[0]) envId = videos[0].deviceId;
      if (!userId && videos[1]) userId = videos[1].deviceId;
      if (!userId && videos[0] && videos[0].deviceId !== envId) userId = videos[0].deviceId;
      self.deviceMap.environment = envId;
      self.deviceMap.user = userId || envId;
      self.devicesMapped = !!(envId || userId);
      logStatus(self.status, null, "devices env=" + (envId || "?").slice(0, 8) + " user=" + (userId || "?").slice(0, 8));
      return self.devicesMapped;
    });
  };

  MediaStreamManager.prototype._bindStream = function (stream, facing) {
    var video = this.videoEl;
    stopTracks(this.stream);
    this.stream = stream;
    this.track = stream.getVideoTracks()[0] || null;
    this.facing = facing;
    if (!video) return Promise.resolve(false);
    video.srcObject = stream;
    video.classList.toggle("is-mirror", facing === "user");
    return video
      .play()
      .catch(function () {})
      .then(function () {
        return waitFrame(video, 2500);
      });
  };

  MediaStreamManager.prototype.showFreeze = function () {
    var video = this.videoEl;
    var canvas = this.freezeEl;
    if (!canvas) return false;
    try {
      var ctx = canvas.getContext("2d");
      if (video && video.readyState >= 2 && video.videoWidth > 0) {
        var w = video.videoWidth;
        var h = video.videoHeight;
        canvas.width = w;
        canvas.height = h;
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        if (this.facing === "user") {
          ctx.translate(w, 0);
          ctx.scale(-1, 1);
        }
        ctx.drawImage(video, 0, 0, w, h);
      } else {
        canvas.width = 720;
        canvas.height = 1280;
        ctx.fillStyle = "#111";
        ctx.fillRect(0, 0, 720, 1280);
      }
      canvas.classList.add("is-visible");
      return true;
    } catch (e) {
      return false;
    }
  };

  MediaStreamManager.prototype.hideFreeze = function () {
    if (this.freezeEl) this.freezeEl.classList.remove("is-visible");
  };

  MediaStreamManager.prototype._bootOnce = function (facing, seq) {
    var self = this;
    return this._acquire(facing).then(function (stream) {
      if (seq !== self._bootSeq) {
        stopTracks(stream);
        return false;
      }
      return self._bindStream(stream, facing).then(function (ok) {
        if (seq !== self._bootSeq) return false;
        if (!ok) throw new Error("no frame");
        return self.mapDevices().then(function () {
          return seq === self._bootSeq;
        });
      });
    });
  };

  MediaStreamManager.prototype.start = function (facing) {
    var self = this;
    facing = facing || "environment";
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this._setStatus(STATUS.ERROR, 0, "no mediaDevices");
      return Promise.resolve(false);
    }

    var seq = ++this._bootSeq;
    var t0 = performance.now();
    this._setStatus(STATUS.INITIALIZING, 0, "start " + facing);

    this._clearReadyWatchdog();
    this._readyWatchdog = setTimeout(function () {
      if (seq !== self._bootSeq) return;
      if (self.status === STATUS.READY) return;
      var shouldRetry = !self._autoRetried;
      self.forceReset("READY timeout >" + READY_TIMEOUT_MS + "ms");
      if (shouldRetry) {
        self._autoRetried = true;
        logStatus(STATUS.ERROR, READY_TIMEOUT_MS, "auto-retry after forceReset");
        self.start(facing);
      }
    }, READY_TIMEOUT_MS);

    return this._bootOnce(facing, seq)
      .then(function (ok) {
        if (seq !== self._bootSeq) return false;
        self._clearReadyWatchdog();
        if (!ok) {
          self.forceReset("boot failed");
          return false;
        }
        self._autoRetried = false;
        self._setStatus(STATUS.READY, performance.now() - t0, "facing=" + self.facing);
        return true;
      })
      .catch(function (err) {
        if (seq !== self._bootSeq) return false;
        self._clearReadyWatchdog();
        self.forceReset((err && err.name) || "boot error");
        return false;
      });
  };

  MediaStreamManager.prototype.switchFacing = function (toFacing) {
    var self = this;
    toFacing = toFacing || (this.facing === "user" ? "environment" : "user");
    if (this._switchLock || this.status === STATUS.SWITCHING) {
      logStatus(this.status, 0, "switch blocked");
      return Promise.resolve(false);
    }
    if (this.status !== STATUS.READY) {
      logStatus(this.status, 0, "switch requires READY");
      return Promise.resolve(false);
    }
    if (toFacing === this.facing) return Promise.resolve(true);

    var t0 = performance.now();
    var from = this.facing;
    this._switchLock = true;
    this._setStatus(STATUS.SWITCHING, 0, from + "→" + toFacing);
    this.showFreeze();

    var targetId = this.deviceMap[toFacing];

    function finishOk() {
      return delay(40).then(function () {
        self.hideFreeze();
        return delay(FADE_MS).then(function () {
          self._switchLock = false;
          self._setStatus(STATUS.READY, performance.now() - t0, "switch " + from + "→" + self.facing);
          return true;
        });
      });
    }

    function failsafeRestart() {
      logStatus(STATUS.SWITCHING, performance.now() - t0, "failsafe stop/restart");
      stopTracks(self.stream);
      self.stream = null;
      self.track = null;
      if (self.videoEl) {
        try {
          self.videoEl.srcObject = null;
        } catch (e) {}
      }
      return delay(HARDWARE_GAP_MS)
        .then(function () {
          return self._acquire(toFacing);
        })
        .then(function (stream) {
          return self._bindStream(stream, toFacing);
        })
        .then(function (ok) {
          if (!ok) throw new Error("failsafe no frame");
          return finishOk();
        });
    }

    var tryApply = Promise.resolve(false);
    if (this.track && targetId && typeof this.track.applyConstraints === "function") {
      tryApply = this.track
        .applyConstraints({
          deviceId: { exact: targetId },
          advanced: [{ deviceId: targetId }],
        })
        .then(function () {
          self.facing = toFacing;
          if (self.videoEl) self.videoEl.classList.toggle("is-mirror", toFacing === "user");
          logStatus(STATUS.SWITCHING, performance.now() - t0, "applyConstraints OK");
          return waitFrame(self.videoEl, 800).then(function (ok) {
            return !!ok;
          });
        })
        .catch(function () {
          return false;
        });
    }

    return tryApply
      .then(function (applied) {
        if (applied) return finishOk();
        return failsafeRestart();
      })
      .catch(function (err) {
        self._switchLock = false;
        self.hideFreeze();
        self.forceReset(err && (err.message || err.name));
        return self
          ._acquire(from)
          .then(function (s) {
            return self._bindStream(s, from).then(function (ok) {
              if (ok) self._setStatus(STATUS.READY, performance.now() - t0, "recovered " + from);
              return false;
            });
          })
          .catch(function () {
            return false;
          });
      });
  };

  MediaStreamManager.prototype.stop = function () {
    this._bootSeq += 1;
    this._clearReadyWatchdog();
    stopTracks(this.stream);
    this.stream = null;
    this.track = null;
    if (this.videoEl) {
      try {
        this.videoEl.srcObject = null;
      } catch (e) {}
    }
    this.hideFreeze();
    this._switchLock = false;
    this._autoRetried = false;
    this.status = STATUS.IDLE;
    logStatus(STATUS.IDLE, 0, "stopped");
  };

  MediaStreamManager.prototype.captureBlob = function (quality) {
    var video = this.videoEl;
    if (!video || video.readyState < 2) return Promise.resolve(null);
    var canvas = document.createElement("canvas");
    var vw = video.videoWidth || 720;
    var vh = video.videoHeight || 1280;
    canvas.width = vw;
    canvas.height = vh;
    var ctx = canvas.getContext("2d");
    if (this.facing === "user") {
      ctx.translate(vw, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(video, 0, 0, vw, vh);
    return new Promise(function (resolve) {
      canvas.toBlob(function (b) {
        resolve(b);
      }, "image/jpeg", quality == null ? 0.88 : quality);
    });
  };

  global.SalomonMediaStreamManager = MediaStreamManager;
  global.SalomonCameraEngine = {
    version: VERSION,
    STABLE_PRODUCTION_READY: STABLE_PRODUCTION_READY,
    READY_TIMEOUT_MS: READY_TIMEOUT_MS,
    STATUS: STATUS,
    MediaStreamManager: MediaStreamManager,
  };

  logStatus("BOOT", 0, "v" + VERSION + " STABLE_PRODUCTION_READY");
})(typeof window !== "undefined" ? window : this);
