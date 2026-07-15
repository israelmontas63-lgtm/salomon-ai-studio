import { useCallback, useEffect, useRef, useState } from "react";
import { enviarMensaje } from "../api/salomon";
import { generarImagen } from "../api/media";
import { getCachedGeo } from "../utils/geo";
import { playSalomonAudio } from "../utils/audio";
import { classifyIntent } from "../core/intent";
import { Haptic, pulse } from "../core/haptics";
import {
  ButtonState,
  CaptureMode,
  CoreState,
  buttonToAppStatus,
  deriveButtonState,
  visualFlagsForButton,
} from "../core/states";

const HANDS_FREE_KEY = "salomon_hands_free";

/**
 * Cerebro del botón central: estados, cancelación, enrutado chat/media,
 * manos libres. Las animaciones las decide VoiceButton vía visualFlags.
 */
export function useSalomonOrchestrator({
  sessionId,
  onSession,
  onUserText,
  onAiText,
  onNotify,
} = {}) {
  const [coreState, setCoreState] = useState(CoreState.IDLE);
  const [captureMode, setCaptureMode] = useState(CaptureMode.NONE);
  const [handsFree, setHandsFreeState] = useState(() => {
    try {
      return localStorage.getItem(HANDS_FREE_KEY) === "1";
    } catch {
      return false;
    }
  });

  const abortRef = useRef(null);
  const audioStopRef = useRef(null);
  const handsFreeRef = useRef(handsFree);
  const resumeHandsFreeRef = useRef(null);
  const coreRef = useRef(coreState);
  const captureRef = useRef(captureMode);

  handsFreeRef.current = handsFree;
  coreRef.current = coreState;
  captureRef.current = captureMode;

  const setHandsFree = useCallback((value) => {
    const next = Boolean(value);
    setHandsFreeState(next);
    try {
      localStorage.setItem(HANDS_FREE_KEY, next ? "1" : "0");
    } catch {
      /* noop */
    }
    onNotify?.(
      next
        ? "Manos libres activado — doble toque inicia conversación continua"
        : "Manos libres desactivado"
    );
    pulse(Haptic.success);
  }, [onNotify]);

  const toggleHandsFree = useCallback(() => {
    setHandsFree(!handsFreeRef.current);
  }, [setHandsFree]);

  const [cancelEpoch, setCancelEpoch] = useState(0);

  const cancelAll = useCallback(
    (reason = "user") => {
      try {
        abortRef.current?.abort?.();
      } catch {
        /* noop */
      }
      abortRef.current = null;
      try {
        audioStopRef.current?.();
      } catch {
        /* noop */
      }
      audioStopRef.current = null;
      setCaptureMode(CaptureMode.NONE);
      setCoreState(CoreState.IDLE);
      setCancelEpoch((n) => n + 1);
      pulse(Haptic.cancel);
      console.info("[Salomón Orquestador] cancelAll → IDLE", { reason });
      if (reason === "user") {
        onNotify?.("Cancelado");
      }
    },
    [onNotify]
  );

  const runChat = useCallback(
    async (text, { signal, meta = {} } = {}) => {
      setCoreState(CoreState.THINKING);
      const geo = getCachedGeo() || {};
      const data = await enviarMensaje(
        text,
        sessionId,
        { ...geo, ...meta },
        { signal }
      );
      if (data?.session_id) onSession?.(data.session_id);
      const reply = data?.texto || data?.respuesta || "";
      onAiText?.(reply, data);
      return data;
    },
    [sessionId, onSession, onAiText]
  );

  const runImage = useCallback(
    async (prompt, { signal } = {}) => {
      setCoreState(CoreState.BUSY_MEDIA);
      onNotify?.("Generando imagen…");
      const data = await generarImagen(
        { prompt, session_id: sessionId || null },
        { signal }
      );
      const msg =
        data?.respuesta ||
        data?.resultado?.mensaje ||
        (data?.resultado?.imagen_base64
          ? "Imagen generada."
          : "Listo (media).");
      onAiText?.(msg, data);
      pulse(Haptic.mediaDone);
      return data;
    },
    [sessionId, onNotify, onAiText]
  );

  const dispatchIntent = useCallback(
    async (rawText, { fromVoice = false, autoSend = true, meta = {} } = {}) => {
      const text = (rawText || "").trim();
      if (!text) return;

      onUserText?.(text, { autoSend });

      if (!autoSend) {
        setCoreState(CoreState.IDLE);
        setCaptureMode(CaptureMode.NONE);
        return { kind: "dictation_fill", text };
      }

      const intent = classifyIntent(text);
      const ac = new AbortController();
      abortRef.current = ac;

      try {
        if (intent.kind === "image" && !meta.imagen_base64) {
          await runImage(intent.prompt || text, { signal: ac.signal });
        } else if (intent.kind === "video" && !meta.imagen_base64) {
          onNotify?.(
            "Para vídeo necesito un archivo. Abre el panel media o describe el clip en el chat."
          );
          await runChat(`[Solicitud de vídeo] ${text}`, {
            signal: ac.signal,
            meta,
          });
        } else {
          await runChat(intent.prompt || text, { signal: ac.signal, meta });
        }

        if (ac.signal.aborted) return { kind: "aborted" };

        setCoreState(CoreState.IDLE);
        setCaptureMode(CaptureMode.NONE);
        pulse(Haptic.success);

        if (
          fromVoice &&
          handsFreeRef.current &&
          typeof resumeHandsFreeRef.current === "function"
        ) {
          window.setTimeout(() => resumeHandsFreeRef.current?.(), 400);
        }

        return intent;
      } catch (err) {
        if (err?.name === "AbortError" || ac.signal.aborted) {
          setCoreState(CoreState.IDLE);
          return { kind: "aborted" };
        }
        console.error("[Orquestador]", err);
        setCoreState(CoreState.ERROR);
        pulse(Haptic.error);
        onNotify?.("No pude completar la petición. Reintenta.");
        window.setTimeout(() => {
          if (coreRef.current === CoreState.ERROR) {
            setCoreState(CoreState.IDLE);
          }
        }, 1600);
        return { kind: "error", error: err };
      } finally {
        if (abortRef.current === ac) abortRef.current = null;
      }
    },
    [onUserText, runChat, runImage, onNotify]
  );

  const playAudio = useCallback((base64, mime) => {
    if (!base64) return;
    setCoreState(CoreState.SPEAKING);
    const stop = playSalomonAudio(base64, mime, {
      onStart: () => {
        setCoreState(CoreState.SPEAKING);
        pulse(Haptic.tap);
      },
      onEnd: () => {
        audioStopRef.current = null;
        setCoreState(CoreState.IDLE);
        pulse(Haptic.speakingDone);
        if (
          handsFreeRef.current &&
          typeof resumeHandsFreeRef.current === "function"
        ) {
          window.setTimeout(() => resumeHandsFreeRef.current?.(), 350);
        }
      },
      onError: () => {
        audioStopRef.current = null;
        setCoreState(CoreState.IDLE);
      },
    });
    audioStopRef.current = stop;
    return stop;
  }, []);

  const beginCapture = useCallback((mode) => {
    setCaptureMode(mode);
    setCoreState(CoreState.CAPTURING);
    const next =
      mode === CaptureMode.DICTATION
        ? ButtonState.DICTATING
        : ButtonState.CONVERSATION;
    console.info("[Salomón Orquestador] captura →", next, { mode });
    if (mode === CaptureMode.DICTATION) pulse(Haptic.holdStart);
    else pulse(Haptic.doubleTap);
  }, []);

  const endCapture = useCallback(() => {
    setCaptureMode(CaptureMode.NONE);
    if (
      coreRef.current === CoreState.CAPTURING ||
      coreRef.current === CoreState.IDLE
    ) {
      setCoreState(CoreState.IDLE);
    }
    console.info("[Salomón Orquestador] fin captura");
  }, []);

  /** Registro para que VoiceButton pueda rearmar manos libres. */
  const registerHandsFreeResume = useCallback((fn) => {
    resumeHandsFreeRef.current = fn;
  }, []);

  const buttonState = deriveButtonState(coreState, captureMode);
  const visual = visualFlagsForButton(buttonState);
  const appStatus = buttonToAppStatus(buttonState);

  const isBusy =
    buttonState === ButtonState.PROCESSING ||
    buttonState === ButtonState.DICTATING ||
    buttonState === ButtonState.CONVERSATION;

  useEffect(() => {
    console.info("[Salomón Orquestador] estado=", buttonState, {
      coreState,
      captureMode,
    });
  }, [buttonState, coreState, captureMode]);

  useEffect(
    () => () => {
      try {
        abortRef.current?.abort?.();
      } catch {
        /* noop */
      }
    },
    []
  );

  return {
    buttonState,
    ButtonState,
    coreState,
    captureMode,
    handsFree,
    setHandsFree,
    toggleHandsFree,
    isBusy,
    visual,
    appStatus,
    beginCapture,
    endCapture,
    dispatchIntent,
    cancelAll,
    cancelEpoch,
    playAudio,
    registerHandsFreeResume,
    /** Compat: voiceMode string para UI antigua */
    voiceMode: captureMode,
  };
}
