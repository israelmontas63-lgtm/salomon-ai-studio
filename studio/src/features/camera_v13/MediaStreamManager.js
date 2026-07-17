/**
 * MediaStreamManager v20 — motor universal (deviceId + freeze + applyConstraints).
 * Estados: INITIALIZING | READY | SWITCHING | ERROR
 */
const HARDWARE_GAP_MS = 320;
const FADE_MS = 200;

export const ENGINE_STATUS = {
  IDLE: "IDLE",
  INITIALIZING: "INITIALIZING",
  READY: "READY",
  SWITCHING: "SWITCHING",
  ERROR: "ERROR",
};

function logStatus(status, latencyMs, extra) {
  const lat = latencyMs == null ? "-" : `${Math.round(latencyMs)}ms`;
  console.info(
    `[CameraEngine] - Status: ${status} - Latencia: ${lat}${extra ? ` - ${extra}` : ""}`
  );
}

function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function stopTracks(stream) {
  if (!stream) return;
  try {
    stream.getTracks().forEach((t) => {
      try {
        t.stop();
      } catch (_) {}
    });
  } catch (_) {}
}

function waitFrame(video, timeoutMs = 2500) {
  return new Promise((resolve) => {
    if (!video) return resolve(false);
    if (video.readyState >= 2 && video.videoWidth > 0) return resolve(true);
    let done = false;
    const timer = setTimeout(() => {
      if (!done) {
        done = true;
        resolve(video.readyState >= 2 && video.videoWidth > 0);
      }
    }, timeoutMs);
    const ok = () => {
      if (done || !video.videoWidth) return;
      done = true;
      clearTimeout(timer);
      resolve(true);
    };
    video.addEventListener("loadeddata", ok);
    video.addEventListener("playing", ok);
  });
}

export class MediaStreamManager {
  constructor({ videoEl, freezeEl, onStatus } = {}) {
    this.videoEl = videoEl || null;
    this.freezeEl = freezeEl || null;
    this.onStatus = onStatus || null;
    this.status = ENGINE_STATUS.IDLE;
    this.facing = "environment";
    this.stream = null;
    this.track = null;
    this.deviceMap = { environment: null, user: null };
    this.lastLatencyMs = 0;
    this._switchLock = false;
  }

  _setStatus(status, latencyMs, extra) {
    this.status = status;
    if (latencyMs != null) this.lastLatencyMs = latencyMs;
    logStatus(status, latencyMs, extra);
    this.onStatus?.(status, this.lastLatencyMs, this.facing);
  }

  isReady() {
    return this.status === ENGINE_STATUS.READY;
  }

  getFacing() {
    return this.facing;
  }

  getStatus() {
    return this.status;
  }

  _constraints(facing) {
    const id = this.deviceMap[facing];
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
  }

  async _acquire(facing) {
    try {
      return await navigator.mediaDevices.getUserMedia(this._constraints(facing));
    } catch {
      try {
        return await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: { facingMode: facing },
        });
      } catch {
        try {
          return await navigator.mediaDevices.getUserMedia({
            audio: false,
            video: { facingMode: { exact: facing } },
          });
        } catch {
          return navigator.mediaDevices.getUserMedia({ audio: false, video: true });
        }
      }
    }
  }

  async mapDevices() {
    if (!navigator.mediaDevices?.enumerateDevices) return false;
    const list = await navigator.mediaDevices.enumerateDevices();
    const videos = list.filter((d) => d.kind === "videoinput" && d.deviceId);
    let envId = null;
    let userId = null;
    videos.forEach((d) => {
      const label = (d.label || "").toLowerCase();
      if (!userId && /front|user|selfie|facing\s*front|frontal/i.test(label)) userId = d.deviceId;
      if (!envId && /back|rear|environment|facing\s*back|trasera|world/i.test(label)) envId = d.deviceId;
    });
    if (!envId && videos[0]) envId = videos[0].deviceId;
    if (!userId && videos[1]) userId = videos[1].deviceId;
    this.deviceMap.environment = envId;
    this.deviceMap.user = userId || envId;
    return !!(envId || userId);
  }

  async _bindStream(stream, facing) {
    stopTracks(this.stream);
    this.stream = stream;
    this.track = stream.getVideoTracks()[0] || null;
    this.facing = facing;
    const video = this.videoEl;
    if (!video) return false;
    video.srcObject = stream;
    video.classList.toggle("is-mirror", facing === "user");
    await video.play().catch(() => {});
    return waitFrame(video);
  }

  showFreeze() {
    const video = this.videoEl;
    const canvas = this.freezeEl;
    if (!canvas) return false;
    try {
      const ctx = canvas.getContext("2d");
      if (video && video.readyState >= 2 && video.videoWidth > 0) {
        const w = video.videoWidth;
        const h = video.videoHeight;
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
    } catch {
      return false;
    }
  }

  hideFreeze() {
    this.freezeEl?.classList.remove("is-visible");
  }

  async start(facing = "environment") {
    if (!navigator.mediaDevices?.getUserMedia) {
      this._setStatus(ENGINE_STATUS.ERROR, 0, "no mediaDevices");
      return false;
    }
    const t0 = performance.now();
    this._setStatus(ENGINE_STATUS.INITIALIZING, 0, `start ${facing}`);
    try {
      const stream = await this._acquire(facing);
      const ok = await this._bindStream(stream, facing);
      if (!ok) throw new Error("no frame");
      await this.mapDevices();
      this._setStatus(ENGINE_STATUS.READY, performance.now() - t0, `facing=${this.facing}`);
      return true;
    } catch (err) {
      this._setStatus(ENGINE_STATUS.ERROR, performance.now() - t0, err?.name);
      return false;
    }
  }

  async switchFacing(toFacing) {
    const to = toFacing || (this.facing === "user" ? "environment" : "user");
    if (this._switchLock || this.status === ENGINE_STATUS.SWITCHING) return false;
    if (this.status !== ENGINE_STATUS.READY && this.status !== ENGINE_STATUS.ERROR) return false;
    if (to === this.facing) return true;

    const t0 = performance.now();
    const from = this.facing;
    this._switchLock = true;
    this._setStatus(ENGINE_STATUS.SWITCHING, 0, `${from}→${to}`);
    this.showFreeze();

    const finishOk = async () => {
      await delay(40);
      this.hideFreeze();
      await delay(FADE_MS);
      this._switchLock = false;
      this._setStatus(ENGINE_STATUS.READY, performance.now() - t0, `switch ${from}→${this.facing}`);
      return true;
    };

    const failsafeRestart = async () => {
      logStatus(ENGINE_STATUS.SWITCHING, performance.now() - t0, "failsafe stop/restart");
      stopTracks(this.stream);
      this.stream = null;
      this.track = null;
      if (this.videoEl) this.videoEl.srcObject = null;
      await delay(HARDWARE_GAP_MS);
      const stream = await this._acquire(to);
      const ok = await this._bindStream(stream, to);
      if (!ok) throw new Error("failsafe no frame");
      return finishOk();
    };

    try {
      const targetId = this.deviceMap[to];
      if (this.track?.applyConstraints && targetId) {
        try {
          await this.track.applyConstraints({
            deviceId: { exact: targetId },
            advanced: [{ deviceId: targetId }],
          });
          this.facing = to;
          this.videoEl?.classList.toggle("is-mirror", to === "user");
          const framed = await waitFrame(this.videoEl, 800);
          if (framed) return finishOk();
        } catch {
          /* fallback */
        }
      }
      return await failsafeRestart();
    } catch (err) {
      this._switchLock = false;
      this.hideFreeze();
      this._setStatus(ENGINE_STATUS.ERROR, performance.now() - t0, err?.message || err?.name);
      try {
        const s = await this._acquire(from);
        if (await this._bindStream(s, from)) {
          this._setStatus(ENGINE_STATUS.READY, performance.now() - t0, `recovered ${from}`);
        }
      } catch (_) {}
      return false;
    }
  }

  stop() {
    stopTracks(this.stream);
    this.stream = null;
    this.track = null;
    if (this.videoEl) this.videoEl.srcObject = null;
    this.hideFreeze();
    this._switchLock = false;
    this.status = ENGINE_STATUS.IDLE;
    logStatus(ENGINE_STATUS.IDLE, 0, "stopped");
  }

  captureBlob(quality = 0.88) {
    const video = this.videoEl;
    if (!video || video.readyState < 2) return Promise.resolve(null);
    const canvas = document.createElement("canvas");
    const vw = video.videoWidth || 720;
    const vh = video.videoHeight || 1280;
    canvas.width = vw;
    canvas.height = vh;
    const ctx = canvas.getContext("2d");
    if (this.facing === "user") {
      ctx.translate(vw, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(video, 0, 0, vw, vh);
    return new Promise((resolve) => canvas.toBlob((b) => resolve(b), "image/jpeg", quality));
  }
}
