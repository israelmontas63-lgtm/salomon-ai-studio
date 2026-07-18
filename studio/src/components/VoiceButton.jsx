import { useCallback, useEffect, useRef, useState } from "react";
import { playBreathSound } from "../utils/helpers";
import { Haptic, pulse } from "../core/haptics";
import { CaptureMode, CoreState } from "../core/states";
import "./VoiceButton.css";

const HOLD_MS = 300;
const DOUBLE_MS = 360;
const TRIPLE_WINDOW_MS = 420;

function createRecognition(lang = "es-ES", { continuous = false } = {}) {
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return null;

  const rec = new SpeechRecognition();
  rec.lang = lang;
  rec.interimResults = true; // Fase 1 — pensar mientras Israel aún habla
  rec.continuous = continuous;
  rec.maxAlternatives = 1;
  return rec;
}

/**
 * Botón núcleo: gestos → orquestador.
 * Hold = dictado | Doble = conversación/manos libres | Triple = forzar media
 * Toque en busy = cancelAll
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
  const holdTimer = useRef(null);
  const clickCount = useRef(0);
  const gestureLock = useRef(null);
  const pressedRef = useRef(false);
  const recognitionRef = useRef(null);
  const [tapPending, setTapPending] = useState(false);
  const [holding, setHolding] = useState(false);
  const [forceMediaNext, setForceMediaNext] = useState(false);

  const captureRef = useRef(captureMode);
  captureRef.current = captureMode;

  const clearTapTimer = () => {
    if (tapTimer.current) {
      window.clearTimeout(tapTimer.current);
      tapTimer.current = null;
    }
  };

  const clearHoldTimer = () => {
    if (holdTimer.current) {
      window.clearTimeout(holdTimer.current);
      holdTimer.current = null;
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
    clearHoldTimer();
    setTapPending(false);
    setHolding(false);
    pressedRef.current = false;
    clickCount.current = 0;
    gestureLock.current = null;
    stopRecognition();
    endCapture();
  }, [endCapture]);

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
      });
    },
    [dispatchIntent, forceMediaNext]
  );

  const startListening = useCallback(
    (mode) => {
      const continuous = mode === CaptureMode.HANDS_FREE;
      const rec = createRecognition("es-ES", { continuous });
      if (!rec) {
        onNotify?.("Tu navegador no soporta reconocimiento de voz.");
        gestureLock.current = null;
        setHolding(false);
        endCapture();
        pulse(Haptic.error);
        return;
      }

      recognitionRef.current = rec;
      setTapPending(false);
      playBreathSound();
      beginCapture(mode);
      onNotify?.(
        mode === CaptureMode.DICTATION
          ? "Dictado — mantén pulsado"
          : mode === CaptureMode.HANDS_FREE
            ? "Manos libres — habla con naturalidad"
            : "Conversación — habla ahora"
      );

      rec.onresult = (event) => {
        const result = event.results?.[event.results.length - 1];
        const text = result?.[0]?.transcript?.trim();
        if (!text) return;

        // Fase 1: interim → feedback en vivo; solo finales disparan el chat
        const isFinal = Boolean(result?.isFinal);
        if (!isFinal) {
          try {
            window.dispatchEvent(
              new CustomEvent("salomon:fase1-escuchando", {
                detail: { texto: text, final: false },
              })
            );
          } catch {
            /* ignore */
          }
          onNotify?.(`Escuchando… ${text.slice(0, 36)}`);
          return;
        }

        const autoSend =
          mode === CaptureMode.CONVERSATION ||
          mode === CaptureMode.HANDS_FREE;
        void handleTranscript(text, { autoSend });

        if (mode === CaptureMode.DICTATION && pressedRef.current) {
          return;
        }
        if (mode !== CaptureMode.HANDS_FREE) {
          stopRecognition();
          endCapture();
          setHolding(false);
          gestureLock.current = null;
        }
      };

      rec.onerror = (event) => {
        if (event.error === "aborted" || event.error === "no-speech") return;
        console.error("[Salomón] Error de voz:", event.error);
        onNotify?.("No se pudo activar el micrófono.");
        pulse(Haptic.error);
        stopCaptureUi();
      };

      rec.onend = () => {
        recognitionRef.current = null;
        if (
          mode === CaptureMode.DICTATION &&
          pressedRef.current &&
          gestureLock.current === "hold"
        ) {
          try {
            const again = createRecognition();
            if (again) {
              recognitionRef.current = again;
              again.onresult = rec.onresult;
              again.onerror = rec.onerror;
              again.onend = rec.onend;
              again.start();
            }
          } catch {
            /* noop */
          }
        }
      };

      try {
        rec.start();
      } catch (err) {
        console.error("[Salomón] No se pudo iniciar escucha:", err);
        onNotify?.("Error al iniciar el micrófono.");
        pulse(Haptic.error);
        stopCaptureUi();
      }
    },
    [
      beginCapture,
      endCapture,
      handleTranscript,
      onNotify,
      stopCaptureUi,
    ]
  );

  useEffect(() => {
    registerHandsFreeResume?.(() => {
      if (!handsFree) return;
      if (coreState !== CoreState.IDLE) return;
      gestureLock.current = "double";
      startListening(CaptureMode.HANDS_FREE);
    });
  }, [registerHandsFreeResume, handsFree, coreState, startListening]);

  /** Cancelación global: aborta mic + UI aunque el fetch ya se cortó. */
  useEffect(() => {
    if (!cancelEpoch) return;
    stopCaptureUi();
  }, [cancelEpoch, stopCaptureUi]);

  const handlePointerDown = (e) => {
    if (disabled) return;
    if (e.button != null && e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();

    pulse(Haptic.tap);

    // Cancelación maestra si hay proceso (no en medio del hold de dictado)
    if (
      (isBusy || captureRef.current) &&
      gestureLock.current !== "hold"
    ) {
      cancelAll("user");
      stopCaptureUi();
      playBreathSound();
      return;
    }

    pressedRef.current = true;
    clearHoldTimer();

    holdTimer.current = window.setTimeout(() => {
      if (!pressedRef.current || gestureLock.current === "double") return;
      if (gestureLock.current === "triple") return;
      gestureLock.current = "hold";
      clearTapTimer();
      clickCount.current = 0;
      setTapPending(false);
      setHolding(true);
      startListening(CaptureMode.DICTATION);
    }, HOLD_MS);
  };

  const handlePointerUp = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (disabled) return;

    const wasHold = gestureLock.current === "hold";
    clearHoldTimer();
    pressedRef.current = false;

    if (wasHold || captureRef.current === CaptureMode.DICTATION) {
      stopCaptureUi();
      playBreathSound();
      return;
    }

    if (
      captureRef.current === CaptureMode.CONVERSATION ||
      captureRef.current === CaptureMode.HANDS_FREE
    ) {
      stopCaptureUi();
      playBreathSound();
      return;
    }

    if (gestureLock.current === "double" || gestureLock.current === "triple") {
      return;
    }

    clickCount.current += 1;
    setTapPending(true);
    clearTapTimer();

    tapTimer.current = window.setTimeout(() => {
      const taps = clickCount.current;
      clickCount.current = 0;
      setTapPending(false);

      if (gestureLock.current === "hold") return;

      if (taps >= 3) {
        // Fase 4: triple toque → forzar próxima captura hacia media
        gestureLock.current = "triple";
        setForceMediaNext(true);
        pulse(Haptic.tripleTap);
        onNotify?.("Modo imagen: di qué generar (o abre el panel)");
        onOpenMedia?.();
        window.setTimeout(() => {
          gestureLock.current = null;
        }, 50);
        return;
      }

      if (taps === 2) {
        gestureLock.current = "double";
        // Hold largo (~1.2s) en settings: toggle manos libres vía 2 taps + flag
        // Doble toque normal = conversación; si handsFree → handsFree mode
        startListening(
          handsFree ? CaptureMode.HANDS_FREE : CaptureMode.CONVERSATION
        );
        return;
      }

      // Un toque: no-op (reserva para cancel ya cubierto en busy)
      gestureLock.current = null;
    }, tapsWindowMs(clickCount.current));
  };

  const handlePointerCancel = () => {
    clearHoldTimer();
    if (
      gestureLock.current === "hold" ||
      captureRef.current === CaptureMode.DICTATION
    ) {
      stopCaptureUi();
    }
    pressedRef.current = false;
    setHolding(false);
  };

  useEffect(
    () => () => {
      clearTapTimer();
      clearHoldTimer();
      stopRecognition();
    },
    []
  );

  const spinning = holding || visual.spinning;
  const shimmering = visual.shimmering;
  const busyPulse = visual.busyPulse;
  const activeRing =
    captureMode || tapPending || holding || busyPulse || visual.error;

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
          captureMode || tapPending || holding ? "control-btn--recording" : "",
          disabled ? "voice-btn--disabled" : "",
          handsFree ? "voice-btn--hands-free" : "",
        ]
          .filter(Boolean)
          .join(" ")}
        aria-label="Núcleo Salomón — mantener dictado, doble conversación, toque cancela"
        aria-pressed={Boolean(captureMode)}
        data-button-state={buttonState || "IDLE"}
        disabled={disabled}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerCancel}
        onPointerCancel={handlePointerCancel}
        onContextMenu={(e) => {
          // Menú contextual / long-press secundario: toggle manos libres
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
    </div>
  );
}

function tapsWindowMs(currentCount) {
  // Primera ventana un poco más larga para permitir triple toque
  return currentCount >= 2 ? TRIPLE_WINDOW_MS : DOUBLE_MS;
}
