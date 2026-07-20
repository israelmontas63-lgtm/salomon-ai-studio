/**
 * Salomón AI — Capa 4 Voice Layer (TTS unificado)
 * Reproduce audio_base64 del cerebro sin duplicar lógica.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";
  var current = null;
  var VoiceLayer = {
    playBase64(audioBase64, mime) {
      if (!audioBase64) return false;
      try {
        if (current) {
          try { current.pause(); } catch (_) {}
        }
        var m = mime || "audio/mpeg";
        var audio = new Audio("data:" + m + ";base64," + audioBase64);
        current = audio;
        audio.play().catch(function () {});
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
