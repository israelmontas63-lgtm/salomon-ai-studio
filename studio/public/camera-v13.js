/**
 * Salomón Camera v16.0.0 — Failsafe switch (Apagar → Esperar 350ms → Reanudar).
 * Prioriza estabilidad en hardware que bloquea dual-stream (p.ej. Redmi 13C).
 * Independiente del asistente / Bridge / dictado.
 */
(function () {
  "use strict";

  var VERSION = "16.0.0";
  var HARDWARE_RELEASE_MS = 350;
  var FADE_MS = 220;

  var state = {
    open: false,
    status: "IDLE", // IDLE | ACTIVE | STREAMING | SWITCHING
    facing: "environment",
    locked: true,
    root: null,
    freeze: null,
    flipBtn: null,
    switching: false,
    lastSwitchMs: 0,
    ready: false,
    stream: null,
    video: null, // video activo visible
    videos: { environment: null, user: null },
  };

  function log() {
    try {
      console.info.apply(console, ["[CameraV16]"].concat([].slice.call(arguments)));
    } catch (e) {}
  }

  function delay(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

  function bindTap(el, handler) {
    if (!el || typeof handler !== "function") return;
    var last = 0;
    function run(e) {
      if (!e) return;
      // Paso 1 — cancelar gesto nativo / hot-swap directo
      if (e.cancelable) e.preventDefault();
      try {
        e.stopPropagation();
        if (e.stopImmediatePropagation) e.stopImmediatePropagation();
      } catch (err) {}
      var t = e.type || "";
      if (t === "pointerup" && e.pointerType === "mouse" && e.button != null && e.button !== 0) return;
      var now = Date.now();
      if (now - last < 280) return;
      last = now;
      handler(e);
    }
    el.addEventListener("click", run, false);
    el.addEventListener("pointerup", run, false);
    el.addEventListener("touchend", run, { passive: false, capture: false });
  }

  function otherFacing(facing) {
    return facing === "user" ? "environment" : "user";
  }

  function setFlipEnabled(on) {
    if (!state.flipBtn) return;
    if (on) {
      state.flipBtn.removeAttribute("disabled");
      state.flipBtn.classList.remove("is-disabled");
      state.flipBtn.setAttribute("aria-disabled", "false");
    } else {
      state.flipBtn.setAttribute("disabled", "true");
      state.flipBtn.classList.add("is-disabled");
      state.flipBtn.setAttribute("aria-disabled", "true");
    }
  }

  function stopAllTracks() {
    // Paso 3 — liberar hardware explícitamente
    if (state.stream) {
      try {
        state.stream.getTracks().forEach(function (track) {
          try {
            track.stop();
          } catch (e) {}
        });
      } catch (e) {}
    }
    state.stream = null;
    state.ready = false;
    ["environment", "user"].forEach(function (f) {
      var v = state.videos[f];
      if (v) {
        try {
          v.srcObject = null;
        } catch (e) {}
      }
    });
  }

  function destroyRoot() {
    if (state.root && state.root.parentNode) state.root.parentNode.removeChild(state.root);
    state.root = null;
    state.freeze = null;
    state.flipBtn = null;
    state.video = null;
    state.videos.environment = null;
    state.videos.user = null;
    document.documentElement.classList.remove(
      "camera-v13-open",
      "camera-v14-open",
      "camera-v15-open",
      "camera-v16-open"
    );
    document.documentElement.removeAttribute("data-camera-v13");
    document.documentElement.removeAttribute("data-camera-v14");
    document.documentElement.removeAttribute("data-camera-v15");
    document.documentElement.removeAttribute("data-camera-v16");
  }

  function acquireStream(facing) {
    // facingMode string simple — mejor compat Android
    return navigator.mediaDevices
      .getUserMedia({ video: { facingMode: facing }, audio: false })
      .catch(function () {
        return navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: facing } },
          audio: false,
        });
      })
      .catch(function () {
        return navigator.mediaDevices.getUserMedia({
          video: { facingMode: { exact: facing } },
          audio: false,
        });
      });
  }

  function waitFirstFrame(video, timeoutMs) {
    return new Promise(function (resolve) {
      if (!video) {
        resolve(false);
        return;
      }
      if (video.readyState >= 2 && video.videoWidth > 0) {
        resolve(true);
        return;
      }
      var done = false;
      var timer = setTimeout(function () {
        if (done) return;
        done = true;
        resolve(video.readyState >= 2 && video.videoWidth > 0);
      }, timeoutMs || 2500);
      function ok() {
        if (done) return;
        if (video.videoWidth < 1) return;
        done = true;
        clearTimeout(timer);
        resolve(true);
      }
      video.addEventListener("loadeddata", ok);
      video.addEventListener("playing", ok);
      video.addEventListener("resize", ok);
    });
  }

  function setActiveLayer(facing) {
    var env = state.videos.environment;
    var usr = state.videos.user;
    if (env) {
      env.classList.toggle("is-active", facing === "environment");
      env.classList.toggle("is-standby", facing !== "environment");
    }
    if (usr) {
      usr.classList.toggle("is-active", facing === "user");
      usr.classList.toggle("is-standby", facing !== "user");
      usr.classList.toggle("is-mirror", facing === "user");
    }
    state.video = state.videos[facing] || null;
    if (state.root) {
      state.root.classList.toggle("is-front", facing === "user");
      state.root.setAttribute("data-facing", facing);
    }
  }

  function showFreezeFrom(video) {
    if (!state.freeze || !video || video.readyState < 2 || video.videoWidth < 1) {
      // Fallback: canvas negro suave evita flash vacío
      if (state.freeze) {
        state.freeze.width = 720;
        state.freeze.height = 1280;
        var c0 = state.freeze.getContext("2d");
        c0.fillStyle = "#111";
        c0.fillRect(0, 0, 720, 1280);
        state.freeze.classList.add("is-visible");
      }
      return false;
    }
    try {
      var ctx = state.freeze.getContext("2d");
      var w = video.videoWidth || 720;
      var h = video.videoHeight || 1280;
      state.freeze.width = w;
      state.freeze.height = h;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      if (state.facing === "user") {
        ctx.translate(w, 0);
        ctx.scale(-1, 1);
      }
      ctx.drawImage(video, 0, 0, w, h);
      state.freeze.classList.add("is-visible");
      return true;
    } catch (e) {
      return false;
    }
  }

  function hideFreeze() {
    if (!state.freeze) return;
    state.freeze.classList.remove("is-visible");
  }

  function markStreaming() {
    state.status = state.ready ? "STREAMING" : "ACTIVE";
    if (state.root) state.root.setAttribute("data-cam-status", state.status);
  }

  function attachFacing(facing, stream) {
    var video = state.videos[facing];
    if (!video) {
      stream.getTracks().forEach(function (t) {
        t.stop();
      });
      return Promise.resolve(false);
    }
    state.stream = stream;
    video.srcObject = stream;
    return video
      .play()
      .catch(function () {})
      .then(function () {
        return waitFirstFrame(video, 2500);
      })
      .then(function (ok) {
        state.ready = !!ok;
        return ok;
      });
  }

  function openPrimary(facing) {
    state.facing = facing;
    setActiveLayer(facing);
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      log("sin mediaDevices");
      return Promise.resolve(false);
    }
    return acquireStream(facing)
      .then(function (stream) {
        if (!state.open) {
          stream.getTracks().forEach(function (t) {
            t.stop();
          });
          return false;
        }
        return attachFacing(facing, stream);
      })
      .then(function (ok) {
        markStreaming();
        return ok;
      })
      .catch(function (err) {
        log("open error", err && err.name);
        state.ready = false;
        markStreaming();
        return false;
      });
  }

  /**
   * Protocolo Failsafe — Apagar, Esperar, Reanudar (Redmi 13C / single-cam HW).
   * facingMode se actualiza SOLO al completar el fade (Paso 6).
   */
  function handleCameraSwitch(e) {
    if (e && e.cancelable) e.preventDefault();
    if (!state.open || state.status === "IDLE" || state.switching) {
      log("switch bloqueado (switching o idle)");
      return Promise.resolve(false);
    }

    var from = state.facing;
    var to = otherFacing(from);
    var t0 = performance.now();
    var currentVideo = state.videos[from];

    state.switching = true;
    state.status = "SWITCHING";
    setFlipEnabled(false);
    if (state.root) {
      state.root.classList.add("is-switching");
      state.root.setAttribute("data-cam-status", "SWITCHING");
    }

    log("failsafe START", from, "→", to);

    // Paso 2 — Freeze visual del último frame
    showFreezeFrom(currentVideo);

    // Paso 3 — Cierre seguro del hardware
    stopAllTracks();

    // Paso 4 — Timeout de seguridad (Android libera el sensor)
    return delay(HARDWARE_RELEASE_MS)
      .then(function () {
        if (!state.open) return null;
        // Paso 5 — Abrir selfie / trasera destino
        log("failsafe acquire", to);
        return acquireStream(to);
      })
      .then(function (stream) {
        if (!stream) return false;
        if (!state.open) {
          stream.getTracks().forEach(function (t) {
            t.stop();
          });
          return false;
        }
        return attachFacing(to, stream);
      })
      .then(function (ok) {
        if (!ok) {
          log("failsafe FAIL acquire", to);
          // Intentar recuperar la cámara de origen
          return acquireStream(from)
            .then(function (s2) {
              return attachFacing(from, s2).then(function (ok2) {
                setActiveLayer(from);
                hideFreeze();
                return ok2;
              });
            })
            .catch(function () {
              hideFreeze();
              return false;
            });
        }

        // Paso 6 — Render + fade: activar capa destino ANTES de quitar freeze
        if (state.root) state.root.classList.add("is-crossfading");
        setActiveLayer(to);
        // Estado facing SOLO ahora (tras stream activo)
        state.facing = to;
        if (state.root) state.root.setAttribute("data-facing", to);

        return delay(40).then(function () {
          hideFreeze();
          return delay(FADE_MS).then(function () {
            if (state.root) state.root.classList.remove("is-crossfading");
            state.ready = true;
            markStreaming();
            return true;
          });
        });
      })
      .then(function (ok) {
        state.switching = false;
        setFlipEnabled(true);
        if (state.root) state.root.classList.remove("is-switching");
        state.lastSwitchMs = Math.round(performance.now() - t0);
        markStreaming();
        log(
          "failsafe DONE",
          from,
          "→",
          state.facing,
          state.lastSwitchMs + "ms",
          ok ? "OK" : "RECOVER/FAIL"
        );
        return !!ok;
      })
      .catch(function (err) {
        log("failsafe ERROR", err && err.name);
        state.switching = false;
        setFlipEnabled(true);
        if (state.root) state.root.classList.remove("is-switching", "is-crossfading");
        hideFreeze();
        markStreaming();
        return false;
      });
  }

  function switchCamera(e) {
    return handleCameraSwitch(e);
  }

  function close() {
    stopAllTracks();
    destroyRoot();
    state.open = false;
    state.status = "IDLE";
    state.facing = "environment";
    state.locked = true;
    state.switching = false;
    state.ready = false;
    window.dispatchEvent(new CustomEvent("salomon:camera-v13-close"));
    window.dispatchEvent(new CustomEvent("salomon:camera-v14-close"));
    window.dispatchEvent(new CustomEvent("salomon:camera-v15-close"));
    window.dispatchEvent(new CustomEvent("salomon:camera-v16-close"));
    log("cerrada");
  }

  function open() {
    if (state.open) return;
    try {
      var old = document.getElementById("ui-camera-overlay");
      if (old) old.remove();
      document.documentElement.classList.remove("salomon-cam-mode", "salomon-cam-selfie");
    } catch (e) {}

    state.open = true;
    state.status = "ACTIVE";
    state.facing = "environment";
    document.documentElement.classList.add(
      "camera-v13-open",
      "camera-v14-open",
      "camera-v15-open",
      "camera-v16-open"
    );
    document.documentElement.setAttribute("data-camera-v13", "1");
    document.documentElement.setAttribute("data-camera-v14", "1");
    document.documentElement.setAttribute("data-camera-v15", "1");
    document.documentElement.setAttribute("data-camera-v16", "1");
    mount();
    openPrimary("environment");
    window.dispatchEvent(new CustomEvent("salomon:camera-v13-open"));
    window.dispatchEvent(new CustomEvent("salomon:camera-v14-open"));
    window.dispatchEvent(new CustomEvent("salomon:camera-v15-open"));
    window.dispatchEvent(new CustomEvent("salomon:camera-v16-open"));
    log("abierta trasera (failsafe mode)");
  }

  function toggle() {
    if (state.open) close();
    else open();
  }

  function toggleCameraMode() {
    if (!state.open) open();
    else close();
  }

  function rotateCamera(e) {
    return handleCameraSwitch(e);
  }

  function flip(e) {
    return handleCameraSwitch(e);
  }

  function takePicture() {
    shoot();
  }

  function shoot() {
    if (!state.open || state.status === "IDLE" || state.switching) return;
    var video = state.videos[state.facing];
    if (!state.ready || !video || video.readyState < 2) {
      log("shoot espera frame");
      return;
    }
    if (state.root) {
      state.root.classList.remove("is-shot");
      void state.root.offsetWidth;
      state.root.classList.add("is-shot");
      setTimeout(function () {
        if (state.root) state.root.classList.remove("is-shot");
      }, 900);
    }
    try {
      var canvas = document.createElement("canvas");
      var vw = video.videoWidth || 720;
      var vh = video.videoHeight || 1280;
      canvas.width = vw;
      canvas.height = vh;
      var ctx = canvas.getContext("2d");
      if (state.facing === "user") {
        ctx.translate(vw, 0);
        ctx.scale(-1, 1);
      }
      ctx.drawImage(video, 0, 0, vw, vh);
      canvas.toBlob(
        function (blob) {
          if (!blob) return;
          var detail = {
            blob: blob,
            facing: state.facing,
            isolated: true,
            deferChat: true,
            cameraOnly: true,
            source: "camera_v16",
          };
          window.dispatchEvent(new CustomEvent("salomon:camera-v13-photo", { detail: detail }));
          window.dispatchEvent(new CustomEvent("salomon:ui-photo", { detail: detail }));
          log("foto OK");
        },
        "image/jpeg",
        0.88
      );
    } catch (err) {
      log("capture fail", err && err.message);
    }
  }

  function makeVideo(facing) {
    var video = document.createElement("video");
    video.className =
      "cam13-video" + (facing === "environment" ? " is-active" : " is-standby");
    video.setAttribute("playsinline", "true");
    video.setAttribute("webkit-playsinline", "true");
    video.setAttribute("data-facing", facing);
    video.muted = true;
    video.autoplay = true;
    video.playsInline = true;
    return video;
  }

  function mount() {
    destroyRoot();
    var root = document.createElement("div");
    root.className = "cam13-root";
    root.setAttribute("data-salomon-camera-v13", "1");
    root.setAttribute("data-salomon-camera-v14", "1");
    root.setAttribute("data-salomon-camera-v15", "1");
    root.setAttribute("data-salomon-camera-v16", "1");
    root.setAttribute("data-isolated", "1");
    root.setAttribute("data-cam-status", "ACTIVE");
    root.setAttribute("data-facing", "environment");
    root.setAttribute("data-switch-mode", "failsafe");

    var videoEnv = makeVideo("environment");
    var videoUser = makeVideo("user");
    state.videos.environment = videoEnv;
    state.videos.user = videoUser;
    state.video = videoEnv;

    var freeze = document.createElement("canvas");
    freeze.className = "cam13-freeze";
    freeze.setAttribute("aria-hidden", "true");
    state.freeze = freeze;

    var flash = document.createElement("div");
    flash.className = "cam13-flash";
    flash.setAttribute("aria-hidden", "true");

    var preview = document.createElement("div");
    preview.className = "cam13-stage-hit";
    preview.setAttribute("aria-hidden", "true");
    bindTap(preview, function () {
      if (state.status === "IDLE" || state.switching) return;
      takePicture();
    });

    var lock = document.createElement("button");
    lock.type = "button";
    lock.className = "cam13-lock is-locked";
    lock.setAttribute("aria-label", "Candado");
    lock.setAttribute("data-cam-action", "lock");
    lock.innerHTML =
      '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/>' +
      '<path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>';
    bindTap(lock, function () {
      if (state.switching) return;
      state.locked = !state.locked;
      lock.classList.toggle("is-locked", state.locked);
      var path = lock.querySelector("path");
      if (path) {
        path.setAttribute("d", state.locked ? "M8 11V8a4 4 0 0 1 8 0v3" : "M8 11V8a4 4 0 0 1 8 0");
      }
    });

    var cluster = document.createElement("div");
    cluster.className = "cam13-cluster-right";

    var camBtn = document.createElement("button");
    camBtn.type = "button";
    camBtn.className = "cam13-icon is-on";
    camBtn.setAttribute("aria-label", "Cámara");
    camBtn.setAttribute("data-cam-action", "toggleCameraMode");
    camBtn.innerHTML = '<span class="cam13-ico-cam" aria-hidden="true"></span>';
    bindTap(camBtn, function () {
      if (state.switching) return;
      toggleCameraMode();
    });

    var flipBtn = document.createElement("button");
    flipBtn.type = "button";
    flipBtn.className = "cam13-icon";
    flipBtn.setAttribute("aria-label", "Giro");
    flipBtn.setAttribute("data-cam-action", "handleCameraSwitch");
    flipBtn.innerHTML =
      '<span class="cam13-ico-flip" aria-hidden="true"><svg viewBox="0 0 24 24">' +
      '<path d="M4 12a8 8 0 0 1 13.5-5.8M20 12a8 8 0 0 1-13.5 5.8"/>' +
      '<polyline points="16 4 17.5 6.2 14.2 6.5"/>' +
      '<polyline points="8 20 6.5 17.8 9.8 17.5"/>' +
      "</svg></span>";
    // Paso 1 + anti doble-tap: bindTap preventDefault; disabled mientras SWITCHING
    bindTap(flipBtn, function (ev) {
      handleCameraSwitch(ev);
    });
    state.flipBtn = flipBtn;

    cluster.appendChild(camBtn);
    cluster.appendChild(flipBtn);

    var shutterWrap = document.createElement("div");
    shutterWrap.className = "cam13-shutter-wrap";
    var shutter = document.createElement("button");
    shutter.type = "button";
    shutter.className = "cam13-shutter";
    shutter.setAttribute("aria-label", "Disparador");
    shutter.setAttribute("data-cam-action", "takePicture");
    shutter.innerHTML =
      '<span class="cam13-ring-plata" aria-hidden="true"></span>' +
      '<span class="cam13-ico-cam-dark" aria-hidden="true"></span>';
    bindTap(shutter, function () {
      if (state.switching) return;
      takePicture();
    });
    shutterWrap.appendChild(shutter);

    root.appendChild(videoEnv);
    root.appendChild(videoUser);
    root.appendChild(freeze);
    root.appendChild(preview);
    root.appendChild(flash);
    root.appendChild(lock);
    root.appendChild(cluster);
    root.appendChild(shutterWrap);
    document.body.appendChild(root);
    state.root = root;
  }

  var api = {
    version: VERSION,
    open: open,
    close: close,
    toggle: toggle,
    flip: flip,
    shoot: shoot,
    rotateCamera: rotateCamera,
    switchCamera: switchCamera,
    handleCameraSwitch: handleCameraSwitch,
    toggleCameraMode: toggleCameraMode,
    takePicture: takePicture,
    isOpen: function () {
      return !!state.open;
    },
    getStatus: function () {
      return state.status;
    },
    getFacing: function () {
      return state.facing;
    },
    isReady: function () {
      return !!state.ready;
    },
    isSwitching: function () {
      return !!state.switching;
    },
    getLastSwitchMs: function () {
      return state.lastSwitchMs;
    },
  };

  window.SalomonCameraV13 = api;
  window.SalomonCameraV14 = api;
  window.SalomonCameraV15 = api;
  window.SalomonCameraV16 = api;

  log("listo", VERSION, "failsafe Apagar-Esperar-Reanudar");
})();
