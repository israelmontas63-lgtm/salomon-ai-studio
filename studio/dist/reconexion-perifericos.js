/**
 * Reconexión de Emergencia v104 — MediaDevices (micrófono + cámara).
 * No modifica CameraEngine (Golden State). Se monta por encima.
 * Created by Israel Monta - Salomon AI Studio
 */
(function (global) {
  "use strict";
  if (global.__SalomonReconexionPerifericos) return;
  global.__SalomonReconexionPerifericos = { version: "104.0.0" };

  function log() {
    try {
      if (localStorage.getItem("salomon_pwa_debug") === "1") {
        console.log.apply(console, ["[Reconexion104]"].concat([].slice.call(arguments)));
      }
    } catch (_) {}
  }

  function hasMedia() {
    return !!(
      global.navigator &&
      navigator.mediaDevices &&
      typeof navigator.mediaDevices.getUserMedia === "function"
    );
  }

  /**
   * Prioriza audio (dictado): si el kernel bloquea por rate-limit,
   * reintenta una vez tras breve espera.
   */
  function installDictadoBridge() {
    if (!hasMedia()) {
      log("MediaDevices no disponible");
      global.__SalomonPerifericos = { ok: false, reason: "NO_MEDIA_DEVICES" };
      return;
    }
    if (navigator.mediaDevices.__salomonReconexion104) return;

    var native = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = function (constraints) {
      var c = constraints || {};
      var audioOnly = !!(c.audio && !c.video);
      return native(c).catch(function (err) {
        var msg = (err && err.message) || "";
        // Reintento emergencia solo para dictado (audio)
        if (audioOnly && /INMORTAL_BLOCKED|NotAllowedError|NotReadableError/i.test(msg)) {
          log("reintento dictado", msg);
          return new Promise(function (resolve, reject) {
            setTimeout(function () {
              native({ audio: true, video: false }).then(resolve).catch(reject);
            }, 350);
          });
        }
        return Promise.reject(err);
      });
    };
    navigator.mediaDevices.__salomonReconexion104 = true;
    global.__SalomonPerifericos = {
      ok: true,
      mediaDevices: true,
      dictado: true,
      camera_engine: true,
      version: "104.0.0",
    };
    log("periféricos reenlazados");
  }

  /** Eco ligero: enumera devices si el permiso ya fue concedido. */
  function ecoDevices() {
    if (!hasMedia() || !navigator.mediaDevices.enumerateDevices) return;
    navigator.mediaDevices
      .enumerateDevices()
      .then(function (list) {
        var audio = list.filter(function (d) {
          return d.kind === "audioinput";
        }).length;
        var video = list.filter(function (d) {
          return d.kind === "videoinput";
        }).length;
        global.__SalomonPerifericos = Object.assign({}, global.__SalomonPerifericos || {}, {
          audioInputs: audio,
          videoInputs: video,
        });
        log("devices", audio, "mic", video, "cam");
      })
      .catch(function () {});
  }

  function boot() {
    installDictadoBridge();
    ecoDevices();
    try {
      global.dispatchEvent(new CustomEvent("salomon:reconexion-perifericos", { detail: global.__SalomonPerifericos }));
    } catch (_) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(window);
