/**
 * Salomón Camera v13.0.0 — runtime aislado (Live).
 * Independiente del asistente / Bridge / dictado / estado del shield.
 * Controles: Candado · Cámara · Giro · Disparador.
 */
(function () {
  "use strict";

  var VERSION = "13.0.0";
  var state = {
    open: false,
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
      console.info.apply(console, ["[CameraV13]"].concat([].slice.call(arguments)));
    } catch (e) {}
  }

  function stopStream() {
    state.seq += 1;
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
    state.video = null;
    state.ready = false;
  }

  function destroyRoot() {
    if (state.root && state.root.parentNode) state.root.parentNode.removeChild(state.root);
    state.root = null;
    document.documentElement.classList.remove("camera-v13-open");
    document.documentElement.removeAttribute("data-camera-v13");
  }

  function close() {
    stopStream();
    destroyRoot();
    state.open = false;
    state.facing = "environment";
    state.locked = true;
    window.dispatchEvent(new CustomEvent("salomon:camera-v13-close"));
    log("cerrada (aislada)");
  }

  function open() {
    if (state.open) return;
    // Apagar overlay neuronal viejo si existe — sin llamar al agente
    try {
      var old = document.getElementById("ui-camera-overlay");
      if (old) old.remove();
      document.documentElement.classList.remove("salomon-cam-mode", "salomon-cam-selfie");
    } catch (e) {}

    state.open = true;
    state.facing = "environment";
    document.documentElement.classList.add("camera-v13-open");
    document.documentElement.setAttribute("data-camera-v13", "1");
    mount();
    startStream("environment");
    window.dispatchEvent(new CustomEvent("salomon:camera-v13-open"));
    log("abierta trasera (aislada)");
  }

  function toggle() {
    if (state.open) close();
    else open();
  }

  function flip() {
    if (!state.open) return;
    state.facing = state.facing === "environment" ? "user" : "environment";
    if (state.root) state.root.classList.toggle("is-front", state.facing === "user");
    startStream(state.facing);
    log("giro →", state.facing);
  }

  function startStream(facing) {
    stopStream();
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
        }
        state.ready = true;
      })
      .catch(function (err) {
        log("error stream", err && err.name);
        state.ready = false;
      });
  }

  function shoot() {
    if (!state.open || !state.ready || !state.video) return;
    var video = state.video;
    if (video.readyState < 2) return;
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
          // Evento propio — no dispara Bridge/dictado
          window.dispatchEvent(
            new CustomEvent("salomon:camera-v13-photo", {
              detail: {
                blob: blob,
                facing: state.facing,
                isolated: true,
                deferChat: true,
                cameraOnly: true,
                source: "camera_v13",
              },
            })
          );
          // Compat visión (cola) sin ligar al asistente en vivo
          window.dispatchEvent(
            new CustomEvent("salomon:ui-photo", {
              detail: {
                blob: blob,
                facing: state.facing,
                deferChat: true,
                cameraOnly: true,
                source: "camera_v13",
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
    root.setAttribute("data-isolated", "1");

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

    var stage = document.createElement("button");
    stage.type = "button";
    stage.className = "cam13-stage-hit";
    stage.setAttribute("aria-label", " ");
    stage.addEventListener("click", function (e) {
      e.preventDefault();
      shoot();
    });

    var lock = document.createElement("button");
    lock.type = "button";
    lock.className = "cam13-lock is-locked";
    lock.setAttribute("aria-label", " ");
    lock.innerHTML =
      '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/>' +
      '<path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>';
    lock.addEventListener("click", function (e) {
      e.stopPropagation();
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
    camBtn.setAttribute("aria-label", " ");
    camBtn.innerHTML = '<span class="cam13-ico-cam" aria-hidden="true"></span>';
    camBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      close();
    });

    var flipBtn = document.createElement("button");
    flipBtn.type = "button";
    flipBtn.className = "cam13-icon";
    flipBtn.setAttribute("aria-label", " ");
    flipBtn.innerHTML =
      '<span class="cam13-ico-flip" aria-hidden="true"><svg viewBox="0 0 24 24">' +
      '<path d="M4 12a8 8 0 0 1 13.5-5.8M20 12a8 8 0 0 1-13.5 5.8"/>' +
      '<polyline points="16 4 17.5 6.2 14.2 6.5"/>' +
      '<polyline points="8 20 6.5 17.8 9.8 17.5"/>' +
      "</svg></span>";
    flipBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      flip();
    });

    cluster.appendChild(camBtn);
    cluster.appendChild(flipBtn);

    var shutterWrap = document.createElement("div");
    shutterWrap.className = "cam13-shutter-wrap";
    var shutter = document.createElement("button");
    shutter.type = "button";
    shutter.className = "cam13-shutter";
    shutter.setAttribute("aria-label", " ");
    shutter.innerHTML =
      '<span class="cam13-ring-plata" aria-hidden="true"></span>' +
      '<span class="cam13-ico-cam-dark" aria-hidden="true"></span>';
    shutter.addEventListener("click", function (e) {
      e.stopPropagation();
      shoot();
    });
    shutterWrap.appendChild(shutter);

    root.appendChild(video);
    root.appendChild(flash);
    root.appendChild(stage);
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
    isOpen: function () {
      return !!state.open;
    },
  };

  log("listo", VERSION, "aislado");
})();
