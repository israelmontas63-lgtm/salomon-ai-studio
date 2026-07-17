/**
 * Salomón Camera v15.0.0 — hot-swap dual stream + crossfade (<300ms).
 * Independiente del asistente / Bridge / dictado.
 * Controles: Candado · Cámara · Giro · Disparador.
 */
(function () {
  "use strict";

  var VERSION = "15.0.0";
  var CROSSFADE_MS = 180;
  var TARGET_SWITCH_MS = 300;

  var state = {
    open: false,
    status: "IDLE", // IDLE | ACTIVE | STREAMING | SWITCHING
    facing: "environment",
    locked: true,
    root: null,
    freeze: null,
    switching: false,
    dualOk: true,
    lastSwitchMs: 0,
    ready: false,
    slots: {
      environment: { stream: null, video: null, ready: false, warming: false },
      user: { stream: null, video: null, ready: false, warming: false },
    },
  };

  function log() {
    try {
      console.info.apply(console, ["[CameraV15]"].concat([].slice.call(arguments)));
    } catch (e) {}
  }

  function bindTap(el, handler) {
    if (!el || typeof handler !== "function") return;
    var last = 0;
    function run(e) {
      if (!e) return;
      var t = e.type || "";
      if (t === "pointerup" && e.pointerType === "mouse" && e.button != null && e.button !== 0) return;
      if (t === "touchend" || t === "pointerup") {
        if (e.cancelable) e.preventDefault();
      }
      try {
        e.stopPropagation();
        if (e.stopImmediatePropagation) e.stopImmediatePropagation();
      } catch (err) {}
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

  function activeVideo() {
    var slot = state.slots[state.facing];
    return slot && slot.video ? slot.video : null;
  }

  function stopSlot(facing, keepVideo) {
    var slot = state.slots[facing];
    if (!slot) return;
    if (slot.stream) {
      try {
        slot.stream.getTracks().forEach(function (t) {
          t.stop();
        });
      } catch (e) {}
    }
    slot.stream = null;
    slot.ready = false;
    slot.warming = false;
    if (slot.video && !keepVideo) {
      try {
        slot.video.srcObject = null;
      } catch (e) {}
    } else if (slot.video) {
      try {
        slot.video.srcObject = null;
      } catch (e) {}
    }
  }

  function stopAllStreams() {
    stopSlot("environment", true);
    stopSlot("user", true);
    state.status = state.open ? "ACTIVE" : "IDLE";
  }

  function destroyRoot() {
    if (state.root && state.root.parentNode) state.root.parentNode.removeChild(state.root);
    state.root = null;
    state.freeze = null;
    state.slots.environment.video = null;
    state.slots.user.video = null;
    document.documentElement.classList.remove(
      "camera-v13-open",
      "camera-v14-open",
      "camera-v15-open"
    );
    document.documentElement.removeAttribute("data-camera-v13");
    document.documentElement.removeAttribute("data-camera-v14");
    document.documentElement.removeAttribute("data-camera-v15");
  }

  function constraintsFor(facing) {
    return {
      exact: { video: { facingMode: { exact: facing }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false },
      ideal: { video: { facingMode: { ideal: facing }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false },
    };
  }

  function acquireStream(facing) {
    var c = constraintsFor(facing);
    return navigator.mediaDevices
      .getUserMedia(c.exact)
      .catch(function () {
        return navigator.mediaDevices.getUserMedia(c.ideal);
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
        resolve(video.readyState >= 2);
      }, timeoutMs || 1200);
      function ok() {
        if (done) return;
        done = true;
        clearTimeout(timer);
        resolve(true);
      }
      video.addEventListener("loadeddata", ok, { once: true });
      video.addEventListener("playing", ok, { once: true });
    });
  }

  function attachToSlot(facing, stream) {
    var slot = state.slots[facing];
    if (!slot || !slot.video) {
      stream.getTracks().forEach(function (t) {
        t.stop();
      });
      return Promise.resolve(false);
    }
    // Liberar stream previo del slot sin tocar el otro
    if (slot.stream && slot.stream !== stream) {
      try {
        slot.stream.getTracks().forEach(function (t) {
          t.stop();
        });
      } catch (e) {}
    }
    slot.stream = stream;
    slot.video.srcObject = stream;
    slot.warming = false;
    return slot.video
      .play()
      .catch(function () {})
      .then(function () {
        return waitFirstFrame(slot.video, 1500);
      })
      .then(function (ok) {
        slot.ready = !!ok;
        return slot.ready;
      });
  }

  function setActiveLayer(facing) {
    var env = state.slots.environment.video;
    var usr = state.slots.user.video;
    if (env) {
      env.classList.toggle("is-active", facing === "environment");
      env.classList.toggle("is-standby", facing !== "environment");
      env.classList.toggle("is-mirror", false);
    }
    if (usr) {
      usr.classList.toggle("is-active", facing === "user");
      usr.classList.toggle("is-standby", facing !== "user");
      usr.classList.toggle("is-mirror", facing === "user");
    }
    if (state.root) {
      state.root.classList.toggle("is-front", facing === "user");
      state.root.setAttribute("data-facing", facing);
    }
  }

  function showFreezeFrom(video) {
    if (!state.freeze || !video || video.readyState < 2) return false;
    try {
      var ctx = state.freeze.getContext("2d");
      var w = video.videoWidth || 720;
      var h = video.videoHeight || 1280;
      state.freeze.width = w;
      state.freeze.height = h;
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
    if (state.freeze) state.freeze.classList.remove("is-visible");
  }

  function warmStandby(facing) {
    var slot = state.slots[facing];
    if (!state.open || !slot || slot.ready || slot.warming) return;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
    slot.warming = true;
    log("prewarm standby →", facing);
    acquireStream(facing)
      .then(function (stream) {
        if (!state.open) {
          stream.getTracks().forEach(function (t) {
            t.stop();
          });
          return false;
        }
        // Si el dispositivo no admite dual stream, el activo puede morir:
        // detectar y marcar dualOk=false, mantener solo el stream pedido.
        return attachToSlot(facing, stream).then(function (ok) {
          if (!ok) return false;
          // Verificar que el activo sigue vivo
          var active = state.slots[state.facing];
          if (active && active.stream) {
            var live = active.stream.getVideoTracks().some(function (t) {
              return t.readyState === "live";
            });
            if (!live) {
              state.dualOk = false;
              log("dual stream no soportado — standby liberado, freeze-path");
              stopSlot(facing, true);
              // Reabrir activo
              return acquireStream(state.facing).then(function (s2) {
                return attachToSlot(state.facing, s2);
              });
            }
          }
          log("standby READY", facing);
          return true;
        });
      })
      .catch(function (err) {
        slot.warming = false;
        state.dualOk = false;
        log("prewarm fail", facing, err && err.name);
      });
  }

  function markStreaming() {
    var slot = state.slots[state.facing];
    state.ready = !!(slot && slot.ready);
    state.status = state.ready ? "STREAMING" : "ACTIVE";
    if (state.root) state.root.setAttribute("data-cam-status", state.status);
  }

  function openPrimary(facing) {
    state.facing = facing;
    setActiveLayer(facing);
    return acquireStream(facing)
      .then(function (stream) {
        if (!state.open) {
          stream.getTracks().forEach(function (t) {
            t.stop();
          });
          return false;
        }
        return attachToSlot(facing, stream);
      })
      .then(function (ok) {
        markStreaming();
        if (ok) {
          // Precalentar la otra cámara sin bloquear UI
          setTimeout(function () {
            if (state.open && state.dualOk) warmStandby(otherFacing(facing));
          }, 80);
        }
        return ok;
      });
  }

  /**
   * Hot-swap: si standby listo → crossfade instantáneo.
   * Si no → freeze-frame + acquire paralelo (sin pantalla negra).
   */
  function switchCamera() {
    if (!state.open || state.status === "IDLE" || state.switching) {
      log("switch bloqueado");
      return Promise.resolve(false);
    }
    var from = state.facing;
    var to = otherFacing(from);
    var t0 = performance.now();
    state.switching = true;
    state.status = "SWITCHING";
    if (state.root) state.root.setAttribute("data-cam-status", "SWITCHING");

    var standby = state.slots[to];
    var current = state.slots[from];

    function finish(ok) {
      state.facing = to;
      setActiveLayer(to);
      hideFreeze();
      markStreaming();
      state.switching = false;
      state.lastSwitchMs = Math.round(performance.now() - t0);
      log(
        "switchCamera",
        from,
        "→",
        to,
        state.lastSwitchMs + "ms",
        state.lastSwitchMs <= TARGET_SWITCH_MS ? "OK<300" : "SLOW",
        ok ? "hot" : "cold"
      );
      // Re-prewarm la salida en background (no await)
      setTimeout(function () {
        if (!state.open) return;
        if (state.dualOk) warmStandby(from);
      }, 120);
      return true;
    }

    // PATH A — hot swap (doble stream listo)
    if (state.dualOk && standby && standby.ready && standby.video && standby.stream) {
      if (state.root) state.root.classList.add("is-crossfading");
      setActiveLayer(to);
      state.facing = to;
      setTimeout(function () {
        if (state.root) state.root.classList.remove("is-crossfading");
        hideFreeze();
        markStreaming();
        state.switching = false;
        state.lastSwitchMs = Math.round(performance.now() - t0);
        log("switchCamera HOT", from, "→", to, state.lastSwitchMs + "ms");
        setTimeout(function () {
          if (state.open && state.dualOk) warmStandby(from);
        }, 120);
      }, CROSSFADE_MS);
      return Promise.resolve(true);
    }

    // PATH B — freeze + acquire (sin apagar preview hasta tener frame)
    showFreezeFrom(current && current.video);
    return acquireStream(to)
      .then(function (stream) {
        if (!state.open) {
          stream.getTracks().forEach(function (t) {
            t.stop();
          });
          return false;
        }
        return attachToSlot(to, stream);
      })
      .then(function (ok) {
        if (!ok) {
          hideFreeze();
          state.switching = false;
          markStreaming();
          log("switch fail", to);
          return false;
        }
        if (state.root) state.root.classList.add("is-crossfading");
        // Liberar stream saliente DESPUÉS de tener entrante
        stopSlot(from, true);
        finish(false);
        setTimeout(function () {
          if (state.root) state.root.classList.remove("is-crossfading");
        }, CROSSFADE_MS);
        return true;
      })
      .catch(function (err) {
        hideFreeze();
        state.switching = false;
        markStreaming();
        log("switch error", err && err.name);
        return false;
      });
  }

  function close() {
    stopAllStreams();
    destroyRoot();
    state.open = false;
    state.status = "IDLE";
    state.facing = "environment";
    state.locked = true;
    state.switching = false;
    state.dualOk = true;
    state.ready = false;
    window.dispatchEvent(new CustomEvent("salomon:camera-v13-close"));
    window.dispatchEvent(new CustomEvent("salomon:camera-v14-close"));
    window.dispatchEvent(new CustomEvent("salomon:camera-v15-close"));
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
    state.dualOk = true;
    document.documentElement.classList.add("camera-v13-open", "camera-v14-open", "camera-v15-open");
    document.documentElement.setAttribute("data-camera-v13", "1");
    document.documentElement.setAttribute("data-camera-v14", "1");
    document.documentElement.setAttribute("data-camera-v15", "1");
    mount();
    openPrimary("environment");
    window.dispatchEvent(new CustomEvent("salomon:camera-v13-open"));
    window.dispatchEvent(new CustomEvent("salomon:camera-v14-open"));
    window.dispatchEvent(new CustomEvent("salomon:camera-v15-open"));
    log("abierta trasera + prewarm selfie");
  }

  function toggle() {
    if (state.open) close();
    else open();
  }

  function toggleCameraMode() {
    if (!state.open) open();
    else close();
  }

  function rotateCamera() {
    switchCamera();
  }

  function flip() {
    switchCamera();
  }

  function takePicture() {
    shoot();
  }

  function shoot() {
    if (!state.open || state.status === "IDLE") return;
    var video = activeVideo();
    var slot = state.slots[state.facing];
    if (!slot || !slot.ready || !video || video.readyState < 2) {
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
            source: "camera_v15",
          };
          window.dispatchEvent(new CustomEvent("salomon:camera-v13-photo", { detail: detail }));
          window.dispatchEvent(new CustomEvent("salomon:ui-photo", { detail: detail }));
          log("foto OK");
        },
        "image/jpeg",
        0.88
      );
    } catch (e) {
      log("capture fail", e && e.message);
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
    root.setAttribute("data-isolated", "1");
    root.setAttribute("data-cam-status", "ACTIVE");
    root.setAttribute("data-facing", "environment");

    var videoEnv = makeVideo("environment");
    var videoUser = makeVideo("user");
    state.slots.environment.video = videoEnv;
    state.slots.user.video = videoUser;

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
      if (state.status === "IDLE") return;
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
      toggleCameraMode();
    });

    var flipBtn = document.createElement("button");
    flipBtn.type = "button";
    flipBtn.className = "cam13-icon";
    flipBtn.setAttribute("aria-label", "Giro");
    flipBtn.setAttribute("data-cam-action", "switchCamera");
    flipBtn.innerHTML =
      '<span class="cam13-ico-flip" aria-hidden="true"><svg viewBox="0 0 24 24">' +
      '<path d="M4 12a8 8 0 0 1 13.5-5.8M20 12a8 8 0 0 1-13.5 5.8"/>' +
      '<polyline points="16 4 17.5 6.2 14.2 6.5"/>' +
      '<polyline points="8 20 6.5 17.8 9.8 17.5"/>' +
      "</svg></span>";
    bindTap(flipBtn, function () {
      switchCamera();
    });

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
    toggleCameraMode: toggleCameraMode,
    takePicture: takePicture,
    isOpen: function () {
      return !!state.open;
    },
    getStatus: function () {
      return state.status;
    },
    isReady: function () {
      return !!(state.slots[state.facing] && state.slots[state.facing].ready);
    },
    getLastSwitchMs: function () {
      return state.lastSwitchMs;
    },
    isDualOk: function () {
      return !!state.dualOk;
    },
  };

  window.SalomonCameraV13 = api;
  window.SalomonCameraV14 = api;
  window.SalomonCameraV15 = api;

  log("listo", VERSION, "dual-stream hot-swap");
})();
