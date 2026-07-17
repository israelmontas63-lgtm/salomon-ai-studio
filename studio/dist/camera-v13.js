/**
 * Salomón Camera UI v20.0.0 — shell sobre CameraEngine / MediaStreamManager.
 * API estable: window.SalomonCameraV13 (compat shield).
 */
(function () {
  "use strict";

  var VERSION = "20.0.0";
  var Manager = window.SalomonMediaStreamManager;
  if (!Manager) {
    console.error("[CameraEngine] MediaStreamManager no cargado — incluye camera-engine.js antes");
    return;
  }

  var ui = {
    open: false,
    locked: true,
    root: null,
    video: null,
    freeze: null,
    flash: null,
    manager: null,
  };

  function log() {
    try {
      console.info.apply(console, ["[CameraUI20]"].concat([].slice.call(arguments)));
    } catch (e) {}
  }

  function bindTap(el, handler) {
    if (!el || typeof handler !== "function") return;
    var last = 0;
    function run(e) {
      if (!e) return;
      if (e.cancelable) e.preventDefault();
      try {
        e.stopPropagation();
        if (e.stopImmediatePropagation) e.stopImmediatePropagation();
      } catch (err) {}
      if (e.type === "pointerup" && e.pointerType === "mouse" && e.button != null && e.button !== 0) return;
      var now = Date.now();
      if (now - last < 280) return;
      last = now;
      handler(e);
    }
    el.addEventListener("click", run, false);
    el.addEventListener("pointerup", run, false);
    el.addEventListener("touchend", run, { passive: false });
  }

  function syncEngineStatus(status) {
    if (!ui.root) return;
    ui.root.setAttribute("data-engine-status", status);
    ui.root.classList.toggle("is-engine-ready", status === "READY");
    ui.root.classList.toggle("is-switching", status === "SWITCHING");
    ui.root.classList.toggle("is-engine-error", status === "ERROR");
    var facing = ui.manager ? ui.manager.getFacing() : "environment";
    ui.root.classList.toggle("is-front", facing === "user");
    ui.root.setAttribute("data-facing", facing);
    if (ui.video) ui.video.classList.toggle("is-mirror", facing === "user");
  }

  function destroyRoot() {
    if (ui.manager) {
      ui.manager.stop();
      ui.manager = null;
    }
    if (ui.root && ui.root.parentNode) ui.root.parentNode.removeChild(ui.root);
    ui.root = null;
    ui.video = null;
    ui.freeze = null;
    ui.flash = null;
    document.documentElement.classList.remove(
      "camera-v13-open",
      "camera-v14-open",
      "camera-v15-open",
      "camera-v16-open",
      "camera-v20-open"
    );
    document.documentElement.removeAttribute("data-camera-v13");
    document.documentElement.removeAttribute("data-camera-v20");
  }

  function close() {
    destroyRoot();
    ui.open = false;
    ui.locked = true;
    window.dispatchEvent(new CustomEvent("salomon:camera-v13-close"));
    window.dispatchEvent(new CustomEvent("salomon:camera-v20-close"));
    log("cerrada");
  }

  function takePicture() {
    if (!ui.manager || !ui.manager.isReady()) return;
    ui.manager.captureBlob(0.88).then(function (blob) {
      if (!blob) return;
      if (ui.root) {
        ui.root.classList.remove("is-shot");
        void ui.root.offsetWidth;
        ui.root.classList.add("is-shot");
        setTimeout(function () {
          if (ui.root) ui.root.classList.remove("is-shot");
        }, 900);
      }
      var detail = {
        blob: blob,
        facing: ui.manager.getFacing(),
        isolated: true,
        deferChat: true,
        cameraOnly: true,
        source: "camera_v20",
      };
      window.dispatchEvent(new CustomEvent("salomon:camera-v13-photo", { detail: detail }));
      window.dispatchEvent(new CustomEvent("salomon:ui-photo", { detail: detail }));
      log("foto OK");
    });
  }

  function rotateCamera() {
    if (!ui.manager || !ui.manager.isReady()) return;
    var next = ui.manager.getFacing() === "user" ? "environment" : "user";
    ui.manager.switchFacing(next).then(function () {
      syncEngineStatus(ui.manager.getStatus());
    });
  }

  function mount() {
    destroyRoot();
    var root = document.createElement("div");
    root.className = "cam13-root";
    root.setAttribute("data-salomon-camera-v13", "1");
    root.setAttribute("data-salomon-camera-v20", "1");
    root.setAttribute("data-isolated", "1");
    root.setAttribute("data-engine-status", "INITIALIZING");
    root.setAttribute("data-switch-mode", "engine-v20");

    var video = document.createElement("video");
    video.className = "cam13-video is-active";
    video.setAttribute("playsinline", "true");
    video.setAttribute("webkit-playsinline", "true");
    video.muted = true;
    video.autoplay = true;
    video.playsInline = true;

    var freeze = document.createElement("canvas");
    freeze.className = "cam13-freeze";
    freeze.setAttribute("aria-hidden", "true");

    var flash = document.createElement("div");
    flash.className = "cam13-flash";
    flash.setAttribute("aria-hidden", "true");

    var preview = document.createElement("div");
    preview.className = "cam13-stage-hit";
    bindTap(preview, function () {
      takePicture();
    });

    var lock = document.createElement("button");
    lock.type = "button";
    lock.className = "cam13-lock is-locked cam13-ctrl";
    lock.setAttribute("aria-label", "Candado");
    lock.setAttribute("data-cam-action", "lock");
    lock.innerHTML =
      '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/>' +
      '<path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>';
    bindTap(lock, function () {
      if (!ui.manager || !ui.manager.isReady()) return;
      ui.locked = !ui.locked;
      lock.classList.toggle("is-locked", ui.locked);
      var path = lock.querySelector("path");
      if (path) {
        path.setAttribute("d", ui.locked ? "M8 11V8a4 4 0 0 1 8 0v3" : "M8 11V8a4 4 0 0 1 8 0");
      }
    });

    var cluster = document.createElement("div");
    cluster.className = "cam13-cluster-right";

    var camBtn = document.createElement("button");
    camBtn.type = "button";
    camBtn.className = "cam13-icon is-on cam13-ctrl";
    camBtn.setAttribute("aria-label", "Cámara");
    camBtn.setAttribute("data-cam-action", "toggleCameraMode");
    camBtn.innerHTML = '<span class="cam13-ico-cam" aria-hidden="true"></span>';
    bindTap(camBtn, function () {
      if (!ui.manager || ui.manager.getStatus() === "SWITCHING") return;
      close();
    });

    var flipBtn = document.createElement("button");
    flipBtn.type = "button";
    flipBtn.className = "cam13-icon cam13-ctrl";
    flipBtn.setAttribute("aria-label", "Giro");
    flipBtn.setAttribute("data-cam-action", "rotateCamera");
    flipBtn.innerHTML =
      '<span class="cam13-ico-flip" aria-hidden="true"><svg viewBox="0 0 24 24">' +
      '<path d="M4 12a8 8 0 0 1 13.5-5.8M20 12a8 8 0 0 1-13.5 5.8"/>' +
      '<polyline points="16 4 17.5 6.2 14.2 6.5"/>' +
      '<polyline points="8 20 6.5 17.8 9.8 17.5"/>' +
      "</svg></span>";
    bindTap(flipBtn, function () {
      rotateCamera();
    });

    cluster.appendChild(camBtn);
    cluster.appendChild(flipBtn);

    var shutterWrap = document.createElement("div");
    shutterWrap.className = "cam13-shutter-wrap";
    var shutter = document.createElement("button");
    shutter.type = "button";
    shutter.className = "cam13-shutter cam13-ctrl";
    shutter.setAttribute("aria-label", "Disparador");
    shutter.setAttribute("data-cam-action", "takePicture");
    shutter.innerHTML =
      '<span class="cam13-ring-plata" aria-hidden="true"></span>' +
      '<span class="cam13-ico-cam-dark" aria-hidden="true"></span>';
    bindTap(shutter, function () {
      takePicture();
    });
    shutterWrap.appendChild(shutter);

    root.appendChild(video);
    root.appendChild(freeze);
    root.appendChild(preview);
    root.appendChild(flash);
    root.appendChild(lock);
    root.appendChild(cluster);
    root.appendChild(shutterWrap);
    document.body.appendChild(root);

    ui.root = root;
    ui.video = video;
    ui.freeze = freeze;
    ui.flash = flash;

    ui.manager = new Manager({
      videoEl: video,
      freezeEl: freeze,
      onStatus: function (status) {
        syncEngineStatus(status);
      },
    });
  }

  function open() {
    if (ui.open) return;
    try {
      var old = document.getElementById("ui-camera-overlay");
      if (old) old.remove();
      document.documentElement.classList.remove("salomon-cam-mode", "salomon-cam-selfie");
    } catch (e) {}

    ui.open = true;
    document.documentElement.classList.add(
      "camera-v13-open",
      "camera-v14-open",
      "camera-v15-open",
      "camera-v16-open",
      "camera-v20-open"
    );
    document.documentElement.setAttribute("data-camera-v13", "1");
    document.documentElement.setAttribute("data-camera-v20", "1");
    mount();
    ui.manager.start("environment").then(function (ok) {
      log(ok ? "engine READY" : "engine ERROR");
    });
    window.dispatchEvent(new CustomEvent("salomon:camera-v13-open"));
    window.dispatchEvent(new CustomEvent("salomon:camera-v20-open"));
  }

  function toggle() {
    if (ui.open) close();
    else open();
  }

  var api = {
    version: VERSION,
    open: open,
    close: close,
    toggle: toggle,
    flip: rotateCamera,
    rotateCamera: rotateCamera,
    switchFacing: function (f) {
      if (!ui.manager) return Promise.resolve(false);
      return ui.manager.switchFacing(f);
    },
    shoot: takePicture,
    takePicture: takePicture,
    toggleCameraMode: function () {
      if (ui.open) close();
      else open();
    },
    isOpen: function () {
      return !!ui.open;
    },
    getStatus: function () {
      return ui.manager ? ui.manager.getStatus() : "IDLE";
    },
    getFacing: function () {
      return ui.manager ? ui.manager.getFacing() : "environment";
    },
    isReady: function () {
      return !!(ui.manager && ui.manager.isReady());
    },
    engine: function () {
      return ui.manager;
    },
  };

  window.SalomonCameraV13 = api;
  window.SalomonCameraV14 = api;
  window.SalomonCameraV15 = api;
  window.SalomonCameraV16 = api;
  window.SalomonCameraV20 = api;

  log("UI listo", VERSION, "sobre MediaStreamManager");
})();
