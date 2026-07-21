/**
 * Salomón AI — Capa 4 Voice Layer (TTS unificado / Adam)
 * Desbloqueo de autoplay + reproducción obligatoria + fallback /api/tts.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";
  var current = null;
  var pending = null;
  var unlocked = false;
  var audioCtx = null;

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
    /**
     * Llamar en el gesto del usuario (toque de dictado) para desbloquear speakers.
     */
    unlock: function () {
      unlocked = true;
      try {
        var AC = window.AudioContext || window.webkitAudioContext;
        if (AC) {
          if (!audioCtx) audioCtx = new AC();
          if (audioCtx.state === "suspended") {
            audioCtx.resume().catch(function () {});
          }
          // Buffer silencioso: marca el origen de audio como "activado por gesto"
          var buf = audioCtx.createBuffer(1, 1, 22050);
          var src = audioCtx.createBufferSource();
          src.buffer = buf;
          src.connect(audioCtx.destination);
          src.start(0);
        }
      } catch (_) {}
      try {
        var silent = new Audio(
          "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA="
        );
        silent.volume = 0.01;
        silent.play().catch(function () {});
      } catch (_) {}
      unlockReplay();
      return true;
    },

    playBase64: function (audioBase64, mime) {
      if (!audioBase64) return false;
      try {
        if (current) {
          try {
            current.pause();
          } catch (_) {}
        }
        var m = mime || "audio/mpeg";
        var audio = new Audio("data:" + m + ";base64," + audioBase64);
        audio.setAttribute("playsinline", "true");
        audio.preload = "auto";
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
            // Reintento inmediato tras unlock previo
            if (unlocked) {
              setTimeout(function () {
                try {
                  audio.play().catch(function () {});
                } catch (_) {}
              }, 40);
            }
          });
        }
        return true;
      } catch (_) {
        return false;
      }
    },

    playFromResponse: function (data) {
      if (!data) return false;
      return this.playBase64(data.audio_base64, data.audio_mime);
    },

    /**
     * Síntesis Adam vía /api/tts y reproducción inmediata.
     */
    speakViaApi: async function (texto) {
      var t = (texto || "").trim();
      if (!t) return false;
      try {
        var res = await fetch("/api/tts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ texto: t }),
          credentials: "same-origin",
        });
        var pack = await res.json().catch(function () {
          return {};
        });
        if (pack && pack.audio_base64) {
          return this.playBase64(pack.audio_base64, pack.audio_mime || "audio/mpeg");
        }
      } catch (_) {}
      return false;
    },

    /**
     * Obligatorio en dictado: usa audio del cerebro o cae a /api/tts.
     */
    ensureSpeak: async function (data) {
      if (!data) return false;
      if (data.audio_base64) {
        return this.playFromResponse(data);
      }
      var texto = (data.texto || data.detail || "").trim();
      if (!texto) return false;
      return await this.speakViaApi(texto);
    },
  };
  window.SalomonVoiceLayer = VoiceLayer;
})();
