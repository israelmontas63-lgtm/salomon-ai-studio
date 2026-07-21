/**
 * Salomón AI — Capa 4 Voice Layer (TTS unificado)
 * Reproduce audio_base64 del cerebro; reintenta si autoplay está bloqueado.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";
  var current = null;
  var pending = null;

  function unlockReplay() {
    if (!pending) return;
    var p = pending;
    pending = null;
    try {
      p.play().catch(function () {});
    } catch (_) {}
  }

  // Desbloqueo: el siguiente gesto del usuario reintenta audio pendiente
  try {
    document.addEventListener("pointerdown", unlockReplay, { passive: true });
    document.addEventListener("keydown", unlockReplay, { passive: true });
  } catch (_) {}

  var VoiceLayer = {
    playBase64(audioBase64, mime) {
      if (!audioBase64) return false;
      try {
        if (current) {
          try {
            current.pause();
          } catch (_) {}
        }
        var m = mime || "audio/mpeg";
        var audio = new Audio("data:" + m + ";base64," + audioBase64);
        current = audio;
        var playPromise = audio.play();
        if (playPromise && typeof playPromise.catch === "function") {
          playPromise.catch(function (err) {
            pending = audio;
            try {
              console.warn(
                "[SalomonVoiceLayer] autoplay bloqueado; se reintenta al tocar:",
                err && err.name ? err.name : err
              );
            } catch (_) {}
          });
        }
        return true;
      } catch (_) {
        return false;
      }
    },
    playFromResponse(data) {
      if (!data) return false;
      return this.playBase64(data.audio_base64, data.audio_mime);
    },
  };
  window.SalomonVoiceLayer = VoiceLayer;
})();
