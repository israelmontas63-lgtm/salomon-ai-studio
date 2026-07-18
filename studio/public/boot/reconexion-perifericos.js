/**
 * Nucleo v105 — Controladores PWA Mic/Camara (auditoria cruzada + reparacion forzosa).
 * No modifica CameraEngine (Golden State). Solicita permisos al inicio / primer gesto.
 * Created by Israel Monta - Salomon AI Studio
 */
(function (global) {
  "use strict";
  if (global.__SalomonReconexionPerifericos && global.__SalomonReconexionPerifericos.version === "105.0.0") {
    return;
  }
  global.__SalomonNucleoReparacion105 = true;
  global.__SalomonReconexionPerifericos = { version: "105.0.0" };

  var PERM_KEY = "salomon_media_perm_v105";
  var state = {
    ok: false,
    mic: false,
    cam: false,
    mediaDevices: false,
    lastError: null,
    primed: false,
  };

  function log() {
    try {
      console.info.apply(console, ["[Nucleo105]"].concat([].slice.call(arguments)));
    } catch (_) {}
  }

  function hasMedia() {
    return !!(
      global.navigator &&
      navigator.mediaDevices &&
      typeof navigator.mediaDevices.getUserMedia === "function"
    );
  }

  function stopTracks(stream) {
    try {
      if (!stream) return;
      stream.getTracks().forEach(function (t) {
        try {
          t.stop();
        } catch (_) {}
      });
    } catch (_) {}
  }

  /** Solicita mic + cam, libera tracks al instante (solo priming de permisos). */
  function solicitarPermisos(opts) {
    opts = opts || {};
    if (!hasMedia()) {
      state.ok = false;
      state.lastError = "NO_MEDIA_DEVICES";
      publish();
      return Promise.resolve(state);
    }
    var wantMic = opts.mic !== false;
    var wantCam = opts.cam !== false;
    var chain = Promise.resolve(null);

    if (wantMic) {
      chain = chain
        .then(function () {
          return navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        })
        .then(function (stream) {
          stopTracks(stream);
          state.mic = true;
          log("mic OK");
        })
        .catch(function (err) {
          state.mic = false;
          state.lastError = (err && err.name) || "MIC_FAIL";
          log("mic FAIL", state.lastError);
        });
    }

    if (wantCam) {
      chain = chain
        .then(function () {
          return navigator.mediaDevices.getUserMedia({
            audio: false,
            video: { facingMode: { ideal: "user" } },
          });
        })
        .catch(function () {
          return navigator.mediaDevices.getUserMedia({ audio: false, video: true });
        })
        .then(function (stream) {
          if (!stream) return;
          stopTracks(stream);
          state.cam = true;
          log("cam OK");
          // Señalar al motor visual (sin tocar Golden internals)
          try {
            global.dispatchEvent(
              new CustomEvent("salomon:vision-ready", { detail: { cam: true, version: "105.0.0" } })
            );
          } catch (_) {}
        })
        .catch(function (err) {
          state.cam = false;
          state.lastError = (err && err.name) || "CAM_FAIL";
          log("cam FAIL", state.lastError);
        });
    }

    return chain.then(function () {
      state.mediaDevices = true;
      state.ok = !!(state.mic || state.cam);
      state.primed = true;
      try {
        localStorage.setItem(
          PERM_KEY,
          JSON.stringify({ mic: state.mic, cam: state.cam, at: Date.now() })
        );
      } catch (_) {}
      publish();
      return state;
    });
  }

  function installBridge() {
    if (!hasMedia()) {
      state.lastError = "NO_MEDIA_DEVICES";
      publish();
      return;
    }
    if (navigator.mediaDevices.__salomonReconexion105) return;
    var native = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = function (constraints) {
      var c = constraints || {};
      return native(c).catch(function (err) {
        var msg = (err && (err.message || err.name)) || "";
        if (/INMORTAL_BLOCKED|NotReadableError|AbortError/i.test(msg)) {
          return new Promise(function (resolve, reject) {
            setTimeout(function () {
              native(c).then(resolve).catch(reject);
            }, 400);
          });
        }
        return Promise.reject(err);
      });
    };
    navigator.mediaDevices.__salomonReconexion105 = true;
    state.mediaDevices = true;
  }

  function ecoDevices() {
    if (!hasMedia() || !navigator.mediaDevices.enumerateDevices) return Promise.resolve(state);
    return navigator.mediaDevices.enumerateDevices().then(function (list) {
      var audio = 0;
      var video = 0;
      list.forEach(function (d) {
        if (d.kind === "audioinput") audio++;
        if (d.kind === "videoinput") video++;
      });
      state.audioInputs = audio;
      state.videoInputs = video;
      // labels no vacíos ⇒ permiso ya concedido
      var labeled = list.some(function (d) {
        return (d.kind === "audioinput" || d.kind === "videoinput") && d.label;
      });
      if (labeled) {
        state.mic = state.mic || audio > 0;
        state.cam = state.cam || video > 0;
        state.ok = true;
      }
      publish();
      return state;
    });
  }

  function publish() {
    global.__SalomonPerifericos = Object.assign({}, state, {
      version: "105.0.0",
      camera_engine: true,
      dictado: !!state.mic,
      vision: !!state.cam,
      solicitarPermisos: solicitarPermisos,
    });
    try {
      global.dispatchEvent(
        new CustomEvent("salomon:reconexion-perifericos", { detail: global.__SalomonPerifericos })
      );
    } catch (_) {}
  }

  function bindFirstGesture() {
    var once = function () {
      document.removeEventListener("pointerdown", once, true);
      document.removeEventListener("touchstart", once, true);
      document.removeEventListener("keydown", once, true);
      solicitarPermisos({ mic: true, cam: true });
    };
    document.addEventListener("pointerdown", once, true);
    document.addEventListener("touchstart", once, true);
    document.addEventListener("keydown", once, true);
  }

  function purgeOldCaches() {
    if (!("caches" in global)) return;
    caches.keys().then(function (keys) {
      keys.forEach(function (k) {
        if (/salomon-pwa-v(9|10[0-4])/.test(k) || k === "salomon-pwa-v97") {
          caches.delete(k).then(function () {
            log("cache purged", k);
          });
        }
      });
    });
  }

  function boot() {
    installBridge();
    purgeOldCaches();
    ecoDevices().then(function () {
      // Si aún no hay permisos, pedir en primer gesto (política de navegadores)
      if (!state.mic || !state.cam) {
        bindFirstGesture();
        // Intento temprano (algunos standalone PWA lo permiten)
        try {
          if (global.matchMedia && global.matchMedia("(display-mode: standalone)").matches) {
            setTimeout(function () {
              if (!state.primed) solicitarPermisos({ mic: true, cam: true });
            }, 800);
          }
        } catch (_) {}
      }
      publish();
    });
    // Ventana de reparación: 45s sin rate-limit agresivo del kernel
    setTimeout(function () {
      global.__SalomonNucleoReparacion105 = false;
    }, 45000);
  }

  global.SalomonPerifericos = {
    solicitarPermisos: solicitarPermisos,
    estado: function () {
      return global.__SalomonPerifericos;
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(window);
