/**
 * Salomón Camera v14.0.0 — runtime aislado (Live).
 * Independiente del asistente / Bridge / dictado / estado del shield.
 * Controles: Candado · Cámara · Giro · Disparador — 100% táctiles al primer toque.
 */
(function () {
  "use strict";

  var VERSION = "14.0.0";
  var state = {
    open: false,
    status: "IDLE", // IDLE | ACTIVE | STREAMING
    facing: "environment",
    locked: true,
    stream: null,
    video: null,
    root: null,
    seq: 0,
    ready: false,
  };

  function log() {
    try {
      console.info.apply(console, ["[CameraV14]"].concat([].slice.call(arguments)));
    } catch (e) {}
  }

  /** Un solo disparo por gesto (evita touchend + click doble). */
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
      if (now - last < 320) return;
      last = now;
      handler(e);
    }
    el.addEventListener("click", run, false);
    el.addEventListener("pointerup", run, false);
    el.addEventListener("touchend", run, { passive: false, capture: false });
  }

  function stopStream() {
    state.seq += 1;
    // Conservar el <video> del DOM — solo cortar tracks/srcObject
    if (state.video) {
      try {
        state.video.srcObject = null;
      } catch (e) {}
    }
    if (state.stream) {
      try {
        state.stream.getTracks().forEach(function (t) {
          t.stop();
        });
      } catch (e) {}
    }
    state.stream = null;
    state.ready = false;
    if (state.open) state.status = "ACTIVE";
    else state.status = "IDLE";
  }

  function destroyRoot() {
    if (state.root && state.root.parentNode) state.root.parentNode.removeChild(state.root);
    state.root = null;
    document.documentElement.classList.remove("camera-v13-open", "camera-v14-open");
    document.documentElement.removeAttribute("data-camera-v13");
    document.documentElement.removeAttribute("data-camera-v14");
  }

  function close() {
    stopStream();
    state.video = null;
    destroyRoot();
    state.open = false;
    state.status = "IDLE";
    state.facing = "environment";
    state.locked = true;
    window.dispatchEvent(new CustomEvent("salomon:camera-v13-close"));
    window.dispatchEvent(new CustomEvent("salomon:camera-v14-close"));
    log("cerrada (aislada)");
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
    document.documentElement.classList.add("camera-v13-open", "camera-v14-open");
    document.documentElement.setAttribute("data-camera-v13", "1");
    document.documentElement.setAttribute("data-camera-v14", "1");
    mount();
    startStream("environment");
    window.dispatchEvent(new CustomEvent("salomon:camera-v13-open"));
    window.dispatchEvent(new CustomEvent("salomon:camera-v14-open"));
    log("abierta trasera ACTIVE");
  }

  function toggle() {
    if (state.open) close();
    else open();
  }

  /** Alias prompt: toggleCameraMode → cerrar/abrir unidad (botón Cámara). */
  function toggleCameraMode() {
    if (!state.open) {
      open();
      return;
    }
    close();
  }

  /** Alias prompt: rotateCamera → Giro. */
  function rotateCamera() {
    flip();
  }

  function flip() {
    if (!state.open || state.status === "IDLE") {
      log("flip bloqueado — no ACTIVE");
      return;
    }
    state.facing = state.facing === "environment" ? "user" : "environment";
    if (state.root) state.root.classList.toggle("is-front", state.facing === "user");
    startStream(state.facing);
    log("giro →", state.facing);
  }

  function startStream(facing) {
    stopStream();
    if (!state.open) return;
    state.status = "ACTIVE";
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      log("sin mediaDevices");
      return;
    }
    var seq = ++state.seq;
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: { exact: facing } }, audio: false })
      .catch(function () {
        return navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: facing } },
          audio: false,
        });
      })
      .then(function (stream) {
        if (seq !== state.seq || !state.open) {
          stream.getTracks().forEach(function (t) {
            t.stop();
          });
          return;
        }
        state.stream = stream;
        if (state.video) {
          state.video.srcObject = stream;
          state.video.play().catch(function () {});
          var markReady = function () {
            if (seq !== state.seq || !state.open) return;
            state.ready = true;
            state.status = "STREAMING";
            if (state.root) state.root.setAttribute("data-cam-status", "STREAMING");
            log("stream READY / STREAMING");
          };
          if (state.video.readyState >= 2) markReady();
          else {
            state.video.addEventListener("loadeddata", markReady, { once: true });
            state.video.addEventListener("playing", markReady, { once: true });
          }
        } else {
          state.ready = true;
          state.status = "STREAMING";
        }
      })
      .catch(function (err) {
        log("error stream", err && err.name);
        state.ready = false;
        state.status = "ACTIVE";
      });
  }

  /** Alias prompt: takePicture → Disparador. */
  function takePicture() {
    shoot();
  }

  function shoot() {
    if (!state.open || state.status === "IDLE") {
      log("shoot bloqueado — no ACTIVE");
      return;
    }
    if (!state.ready || !state.video) {
      log("shoot espera stream (aún no READY)");
      return;
    }
    var video = state.video;
    if (video.readyState < 2) {
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
          window.dispatchEvent(
            new CustomEvent("salomon:camera-v13-photo", {
              detail: {
                blob: blob,
                facing: state.facing,
                isolated: true,
                deferChat: true,
                cameraOnly: true,
                source: "camera_v14",
              },
            })
          );
          window.dispatchEvent(
            new CustomEvent("salomon:ui-photo", {
              detail: {
                blob: blob,
                facing: state.facing,
                deferChat: true,
                cameraOnly: true,
                source: "camera_v14",
              },
            })
          );
          log("foto OK (aislada)");
        },
        "image/jpeg",
        0.88
      );
    } catch (e) {
      log("capture fail", e && e.message);
    }
  }

  function mount() {
    destroyRoot();
    var root = document.createElement("div");
    root.className = "cam13-root";
    root.setAttribute("data-salomon-camera-v13", "1");
    root.setAttribute("data-salomon-camera-v14", "1");
    root.setAttribute("data-isolated", "1");
    root.setAttribute("data-cam-status", "ACTIVE");

    var video = document.createElement("video");
    video.className = "cam13-video";
    video.setAttribute("playsinline", "true");
    video.setAttribute("webkit-playsinline", "true");
    video.muted = true;
    video.autoplay = true;
    video.playsInline = true;
    state.video = video;

    var flash = document.createElement("div");
    flash.className = "cam13-flash";
    flash.setAttribute("aria-hidden", "true");

    // Preview hit: SIN capa full-screen encima de botones (evita click-through muerto)
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
      log("candado", state.locked ? "ON" : "OFF");
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
      log("Cámara → toggleCameraMode");
      toggleCameraMode();
    });

    var flipBtn = document.createElement("button");
    flipBtn.type = "button";
    flipBtn.className = "cam13-icon";
    flipBtn.setAttribute("aria-label", "Giro");
    flipBtn.setAttribute("data-cam-action", "rotateCamera");
    flipBtn.innerHTML =
      '<span class="cam13-ico-flip" aria-hidden="true"><svg viewBox="0 0 24 24">' +
      '<path d="M4 12a8 8 0 0 1 13.5-5.8M20 12a8 8 0 0 1-13.5 5.8"/>' +
      '<polyline points="16 4 17.5 6.2 14.2 6.5"/>' +
      '<polyline points="8 20 6.5 17.8 9.8 17.5"/>' +
      "</svg></span>";
    bindTap(flipBtn, function () {
      log("Giro → rotateCamera");
      rotateCamera();
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
      log("Disparador → takePicture");
      takePicture();
    });
    shutterWrap.appendChild(shutter);

    // Orden: video → preview → flash → controles (controles siempre encima)
    root.appendChild(video);
    root.appendChild(preview);
    root.appendChild(flash);
    root.appendChild(lock);
    root.appendChild(cluster);
    root.appendChild(shutterWrap);
    document.body.appendChild(root);
    state.root = root;
  }

  window.SalomonCameraV13 = {
    version: VERSION,
    open: open,
    close: close,
    toggle: toggle,
    flip: flip,
    shoot: shoot,
    rotateCamera: rotateCamera,
    toggleCameraMode: toggleCameraMode,
    takePicture: takePicture,
    isOpen: function () {
      return !!state.open;
    },
    getStatus: function () {
      return state.status;
    },
    isReady: function () {
      return !!state.ready;
    },
  };

  // Alias estable v14
  window.SalomonCameraV14 = window.SalomonCameraV13;

  log("listo", VERSION, "eventos reconectados");
})();
