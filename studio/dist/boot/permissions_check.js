/**
 * boot/permissions_check.js — fuerza solicitud mic/cámara a Israel.
 */
(function (global) {
  "use strict";

  var state = { mic: false, camera: false, asked: false };

  function stop(stream) {
    try {
      stream &&
        stream.getTracks &&
        stream.getTracks().forEach(function (t) {
          t.stop();
        });
    } catch (e) {}
  }

  function emit(detail) {
    global.__SalomonPermissions = detail;
    try {
      global.dispatchEvent(new CustomEvent("salomon:permissions-ready", { detail: detail }));
    } catch (e) {}
    var step = document.getElementById("splash-step");
    if (step) {
      step.textContent = detail.mic
        ? "Micrófono listo — iniciando Salomón…"
        : "Activa el micrófono para voz completa";
    }
  }

  async function askMic() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return false;
    }
    try {
      var s = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });
      stop(s);
      return true;
    } catch (e) {
      console.warn("[permissions] mic denegado", e && e.name);
      return false;
    }
  }

  async function askCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return false;
    }
    try {
      var s = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: "user" },
      });
      stop(s);
      return true;
    } catch (e) {
      console.warn("[permissions] cámara denegada/omitida", e && e.name);
      return false;
    }
  }

  var SalomonPermissions = {
    state: function () {
      return state;
    },
    ensure: function () {
      if (state.asked && state.mic) {
        emit(state);
        return Promise.resolve(state);
      }
      state.asked = true;
      var step = document.getElementById("splash-step");
      if (step) step.textContent = "Israel: permite micrófono y cámara…";
      return askMic()
        .then(function (micOk) {
          state.mic = !!micOk;
          return askCamera();
        })
        .then(function (camOk) {
          state.camera = !!camOk;
          emit(state);
          return state;
        });
    },
  };

  global.SalomonPermissions = SalomonPermissions;
})(typeof window !== "undefined" ? window : globalThis);
