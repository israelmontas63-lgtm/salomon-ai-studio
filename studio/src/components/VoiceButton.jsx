import { useCallback, useEffect, useRef, useState } from "react";
import { hapticPulse, playBreathSound } from "../utils/helpers";
import "./VoiceButton.css";

function createRecognition(lang = "es-ES") {
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return null;

  const rec = new SpeechRecognition();
  rec.lang = lang;
  rec.interimResults = false;
  rec.continuous = false;
  rec.maxAlternatives = 1;
  return rec;
}

export default function VoiceButton({
  voiceMode,
  appStatus,
  disabled = false,
  onModeChange,
  onStatusChange,
  onTranscript,
  onNotify,
}) {
  const tapTimer = useRef(null);
  const clickCount = useRef(0);
  const recognitionRef = useRef(null);
  const [tapPending, setTapPending] = useState(false);

  const clearTapTimer = () => {
    if (tapTimer.current) {
      window.clearTimeout(tapTimer.current);
      tapTimer.current = null;
    }
  };

  const stopRecognition = () => {
    try {
      recognitionRef.current?.stop();
    } catch {
      /* noop */
    }
    recognitionRef.current = null;
  };

  const stopMode = useCallback(() => {
    clearTapTimer();
    setTapPending(false);
    clickCount.current = 0;
    stopRecognition();
    onModeChange(null);
    onStatusChange("ready");
  }, [onModeChange, onStatusChange]);

  const startListening = useCallback(
    (mode) => {
      const rec = createRecognition();
      if (!rec) {
        onNotify?.("Tu navegador no soporta reconocimiento de voz.");
        return;
      }

      recognitionRef.current = rec;
      setTapPending(false);
      playBreathSound();
      hapticPulse(mode === "conversation" ? [8, 40, 8] : 10);
      onModeChange(mode);
      onStatusChange("listening");
      onNotify?.(
        mode === "conversation"
          ? "Modo conversación — habla ahora"
          : "Escuchando — dictado activo"
      );

      rec.onresult = (event) => {
        const text = event.results?.[0]?.[0]?.transcript?.trim();
        if (text) {
          onTranscript(text, mode === "conversation");
        }
        stopMode();
      };

      rec.onerror = (event) => {
        console.error("[Salomón] Error de voz:", event.error);
        onNotify?.("No se pudo activar el micrófono. Revisa los permisos.");
        stopMode();
      };

      rec.onend = () => {
        recognitionRef.current = null;
        if (mode === "conversation") {
          onStatusChange("thinking");
        }
      };

      try {
        rec.start();
      } catch (err) {
        console.error("[Salomón] No se pudo iniciar escucha:", err);
        onNotify?.("Error al iniciar el micrófono.");
        stopMode();
      }
    },
    [onModeChange, onNotify, onStatusChange, onTranscript, stopMode]
  );

  const startDictation = useCallback(
    () => startListening("dictation"),
    [startListening]
  );

  const startConversation = useCallback(
    () => startListening("conversation"),
    [startListening]
  );

  const handlePointerUp = (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (disabled) return;

    if (voiceMode) {
      stopMode();
      playBreathSound();
      return;
    }

    setTapPending(true);
    onStatusChange("listening");
    clickCount.current += 1;

    clearTapTimer();
    tapTimer.current = window.setTimeout(() => {
      const taps = clickCount.current;
      clickCount.current = 0;
      setTapPending(false);

      if (taps >= 2) {
        startConversation();
      } else if (taps === 1) {
        startDictation();
      } else {
        onStatusChange("ready");
      }
    }, 320);
  };

  useEffect(
    () => () => {
      clearTapTimer();
      stopRecognition();
    },
    []
  );

  const activeRing = voiceMode || tapPending;

  const ringClass = [
    "voice-ring",
    tapPending && !voiceMode ? "voice-ring--pending" : "",
    voiceMode === "dictation" ? "voice-ring--dictation" : "",
    voiceMode === "conversation" ? "voice-ring--conversation" : "",
    appStatus === "thinking" && voiceMode === "conversation"
      ? "voice-ring--thinking"
      : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="voice-btn-wrap">
      {activeRing && <div className={ringClass} aria-hidden="true" />}
      <button
        type="button"
        className={[
          "control-btn control-btn--main voice-btn",
          voiceMode || tapPending ? "control-btn--recording" : "",
          disabled ? "voice-btn--disabled" : "",
        ].join(" ")}
        aria-label="Voz — toque dictado, doble toque conversación"
        aria-pressed={Boolean(voiceMode)}
        disabled={disabled}
        onPointerUp={handlePointerUp}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
        }}
      >
        🎙
      </button>
    </div>
  );
}
