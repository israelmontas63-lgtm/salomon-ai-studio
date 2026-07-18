import { useCallback, useEffect, useRef, useState } from "react";
import { playBreathSound } from "../utils/helpers";
import { Haptic, pulse } from "../core/haptics";
import { CaptureMode, CoreState } from "../core/states";
import "./VoiceButton.css";

const DOUBLE_MS = 320;
const TRIPLE_WINDOW_MS = 420;

function createRecognition(lang = "es-ES", { continuous = false } = {}) {
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return null;

  const rec = new SpeechRecognition();
  rec.lang = lang;
  rec.interimResults = true;
  rec.continuous = continuous;
  rec.maxAlternatives = 1;
  return rec;
}

/**
 * Núcleo de audio — arquitectura limpia:
 * 1 toque  → Modo Dictado (STT → input, sin chat / sin web)
 * 2 toques → Modo Conversacional (STT → IA bidireccional)
 * 3 toques → armar media
 * Toque en busy → cancelAll
 */
export default function VoiceButton({
  orchestrator,
  disabled = false,
  onNotify,
  onOpenMedia,
}) {
  const {
    coreState,
    captureMode,
    handsFree,
    visual,
    beginCapture,
    endCapture,
    dispatchIntent,
    cancelAll,
    registerHandsFreeResume,
    toggleHandsFree,
    isBusy,
    cancelEpoch,
    buttonState,
  } = orchestrator;

  const tapTimer = useRef(null);
  const clickCount = useRef(0);
  const lastPointerUp = useRef(0);
  const recognitionRef = useRef(null);
  const [tapPending, setTapPending] = useState(false);
  const [forceMediaNext, setForceMediaNext] = useState(false);
  const [modeLabel, setModeLabel] = useState("");

  const captureRef = useRef(captureMode);
  captureRef.current = captureMode;

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

  const stopCaptureUi = useCallback(() => {
    clearTapTimer();
    setTapPending(false);
    clickCount.current = 0;
    stopRecognition();
    endCapture();
    setModeLabel("");
  }, [endCapture]);

  const ensureMicHardware = useCallback(async () => {
    // Re-mapear puerto de audio si el kernel no tiene stream
    if (!navigator.mediaDevices?.getUserMedia) {
      onNotify?.("Sin acceso a micrófono en este dispositivo.");
      return false;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: false,
      });
      // Liberar tras abrir el puerto (SpeechRecognition toma el device)
      stream.getTracks().forEach((t) => t.stop());
      return true;
    } catch {
      onNotify?.("Activa el micrófono del sistema para Salomón.");
      return false;
    }
  }, [onNotify]);

  const handleTranscript = useCallback(
    async (text, { autoSend, forceMedia = false } = {}) => {
      let payload = text;
      if (forceMedia || forceMediaNext) {
        payload = `genera una imagen de ${text}`;
        setForceMediaNext(false);
      }
      await dispatchIntent(payload, {
        fromVoice: true,
        autoSend,
        // Memory Cortex: conversación sin Fase1/auto-research
        meta: { fase1: false },
      });
    },
    [dispatchIntent, forceMediaNext]
  );

  const startListening = useCallback(
    async (mode) => {
      const continuous = mode === CaptureMode.HANDS_FREE;
      const rec = createRecognition("es-ES", { continuous });
      if (!rec) {
        const ok = await ensureMicHardware();
        onNotify?.(
          ok
            ? "Tu navegador no soporta dictado por voz. Usa Chrome/Edge."
            : "No pude abrir el puerto de audio."
        );
        return;
      }

      const hw = await ensureMicHardware();
      if (!hw) return;

      const isDictation = mode === CaptureMode.DICTATION;
      setModeLabel(isDictation ? "Dictado" : "IA");
      beginCapture(mode);
      pulse(isDictation ? Haptic.tap : Haptic.doubleTap);

      // Sincronizar overlay visual (shield / bridge)
      try {
        const btn = document.querySelector(".voice-btn.control-btn--main");
        if (btn) {
          btn.dataset.uiMode = isDictation ? "dictation" : "conversation";
        }
        window.SalomonBridge?.setState?.(
          isDictation ? "DICTATING" : "CONVERSATION"
        );
      } catch {
        /* noop */
      }

      recognitionRef.current = rec;
      let finalText = "";

      rec.onresult = (ev) => {
        let interim = "";
        for (let i = ev.resultIndex; i < ev.results.length; i++) {
          const piece = ev.results[i][0]?.transcript || "";
          if (ev.results[i].isFinal) finalText += piece;
          else interim += piece;
        }
        if (interim && isDictation) {
          // Dictado: canal directo al input (sin búsquedas)
          dispatchIntent(interim, {
            fromVoice: true,
            autoSend: false,
            meta: { fase1: false },
          });
        }
      };

      rec.onerror = (ev) => {
        if (ev.error === "not-allowed" || ev.error === "service-not-allowed") {
          onNotify?.("Permiso de micrófono denegado.");
        } else if (ev.error !== "aborted" && ev.error !== "no-speech") {
          onNotify?.("Error de audio — reintenta el toque.");
        }
        stopCaptureUi();
      };

      rec.onend = () => {
        const text = (finalText || "").trim();
        recognitionRef.current = null;
        if (!text) {
          stopCaptureUi();
          return;
        }
        const autoSend = mode !== CaptureMode.DICTATION;
        handleTranscript(text, { autoSend }).finally(() => {
          stopCaptureUi();
          playBreathSound();
        });
      };

      try {
        rec.start();
      } catch {
        onNotify?.("No pude iniciar el micrófono. Reintenta.");
        stopCaptureUi();
      }
    },
    [
      beginCapture,
      dispatchIntent,
      ensureMicHardware,
      handleTranscript,
      onNotify,
      stopCaptureUi,
    ]
  );

  useEffect(() => {
    registerHandsFreeResume?.(() => {
      if (!handsFree) return;
      if (coreState !== CoreState.IDLE) return;
      startListening(CaptureMode.HANDS_FREE);
    });
  }, [registerHandsFreeResume, handsFree, coreState, startListening]);

  useEffect(() => {
    if (!cancelEpoch) return;
    stopCaptureUi();
  }, [cancelEpoch, stopCaptureUi]);

  const handlePointerUp = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (disabled) return;

    const now = Date.now();
    if (now - lastPointerUp.current < 80) return;
    lastPointerUp.current = now;
    pulse(Haptic.tap);

    // Busy / escuchando → cancelar
    if (isBusy || captureRef.current) {
      cancelAll("user");
      stopCaptureUi();
      playBreathSound();
      return;
    }

    clickCount.current += 1;
    setTapPending(true);
    clearTapTimer();

    const windowMs =
      clickCount.current >= 3 ? TRIPLE_WINDOW_MS : DOUBLE_MS;

    tapTimer.current = window.setTimeout(() => {
      const taps = clickCount.current;
      clickCount.current = 0;
      setTapPending(false);

      if (taps >= 3) {
        setForceMediaNext(true);
        pulse(Haptic.tripleTap);
        onNotify?.("Modo imagen: di qué generar");
        onOpenMedia?.();
        return;
      }

      if (taps >= 2) {
        startListening(
          handsFree ? CaptureMode.HANDS_FREE : CaptureMode.CONVERSATION
        );
        onNotify?.("Modo IA — conversación activa");
        return;
      }

      // 1 toque → Dictado inmediato
      startListening(CaptureMode.DICTATION);
      onNotify?.("Modo Dictado");
    }, windowMs);
  };

  useEffect(
    () => () => {
      clearTapTimer();
      stopRecognition();
    },
    []
  );

  const spinning = visual.spinning || captureMode === CaptureMode.DICTATION;
  const shimmering =
    visual.shimmering ||
    captureMode === CaptureMode.CONVERSATION ||
    captureMode === CaptureMode.HANDS_FREE;
  const busyPulse = visual.busyPulse;
  const activeRing =
    captureMode || tapPending || busyPulse || visual.error;

  const ringClass = [
    "voice-ring",
    tapPending && !captureMode ? "voice-ring--pending" : "",
    spinning ? "voice-ring--dictation" : "",
    shimmering ? "voice-ring--conversation" : "",
    busyPulse ? "voice-ring--thinking" : "",
    visual.error ? "voice-ring--error" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const label =
    modeLabel ||
    (captureMode === CaptureMode.DICTATION
      ? "Dictado"
      : captureMode === CaptureMode.CONVERSATION ||
          captureMode === CaptureMode.HANDS_FREE
        ? "IA"
        : "");

  return (
    <div className="voice-btn-wrap">
      {activeRing && <div className={ringClass} aria-hidden="true" />}
      <button
        type="button"
        className={[
          "control-btn control-btn--main voice-btn",
          spinning ? "voice-btn--spinning" : "",
          shimmering ? "voice-btn--shimmer" : "",
          busyPulse ? "voice-btn--busy" : "",
          visual.error ? "voice-btn--error" : "",
          forceMediaNext ? "voice-btn--media-armed" : "",
          captureMode || tapPending ? "control-btn--recording" : "",
          disabled ? "voice-btn--disabled" : "",
          handsFree ? "voice-btn--hands-free" : "",
        ]
          .filter(Boolean)
          .join(" ")}
        aria-label="Voz — 1 toque Dictado, 2 toques IA"
        aria-pressed={Boolean(captureMode)}
        data-button-state={buttonState || "IDLE"}
        data-ui-mode={
          captureMode === CaptureMode.DICTATION
            ? "dictation"
            : captureMode === CaptureMode.CONVERSATION ||
                captureMode === CaptureMode.HANDS_FREE
              ? "conversation"
              : ""
        }
        disabled={disabled}
        onPointerUp={handlePointerUp}
        onPointerDown={(e) => {
          e.preventDefault();
          e.stopPropagation();
        }}
        onContextMenu={(e) => {
          e.preventDefault();
          toggleHandsFree?.();
        }}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
        }}
      >
        <span className="voice-btn__clip">
          <span className="voice-btn__fx" aria-hidden="true" />
          <span className="voice-btn__glyph">🎙</span>
        </span>
      </button>
      {label ? (
        <span className="voice-mode-badge" data-mode={label === "IA" ? "ia" : "dictado"}>
          {label}
        </span>
      ) : null}
    </div>
  );
}
