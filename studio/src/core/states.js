/**
 * Estados unificados del botón-núcleo (vocabulario funcional).
 * Un solo estado público evita solapes entre “modo voz” y “proceso IA”.
 */
export const ButtonState = Object.freeze({
  IDLE: "IDLE",
  DICTATING: "DICTATING",
  CONVERSATION: "CONVERSATION",
  PROCESSING: "PROCESSING",
});

/** Capas internas (implementación). */
export const CoreState = Object.freeze({
  IDLE: "idle",
  CAPTURING: "capturing",
  THINKING: "thinking",
  SPEAKING: "speaking",
  BUSY_MEDIA: "busyMedia",
  ERROR: "error",
});

export const CaptureMode = Object.freeze({
  NONE: null,
  DICTATION: "dictation",
  CONVERSATION: "conversation",
  HANDS_FREE: "handsFree",
});

/**
 * Deriva el estado público del botón sin ambigüedad:
 * captura de voz gana sobre idle; procesamiento gana cuando no hay captura.
 */
export function deriveButtonState(coreState, captureMode) {
  if (captureMode === CaptureMode.DICTATION) return ButtonState.DICTATING;
  if (
    captureMode === CaptureMode.CONVERSATION ||
    captureMode === CaptureMode.HANDS_FREE
  ) {
    return ButtonState.CONVERSATION;
  }
  if (
    coreState === CoreState.THINKING ||
    coreState === CoreState.SPEAKING ||
    coreState === CoreState.BUSY_MEDIA
  ) {
    return ButtonState.PROCESSING;
  }
  return ButtonState.IDLE;
}

/**
 * Animaciones metálicas existentes, disparadas solo por estado lógico.
 * - DICTATING → giro (voice-btn--spinning)
 * - CONVERSATION → destellos (voice-btn--shimmer)
 * - PROCESSING → pulso busy (voice-btn--busy)
 */
export function visualFlagsForButton(buttonState) {
  return {
    spinning: buttonState === ButtonState.DICTATING,
    shimmering: buttonState === ButtonState.CONVERSATION,
    busyPulse: buttonState === ButtonState.PROCESSING,
    error: false,
  };
}

/** Compat Header / vinyl (appStatus legacy). */
export function buttonToAppStatus(buttonState) {
  switch (buttonState) {
    case ButtonState.DICTATING:
    case ButtonState.CONVERSATION:
      return "listening";
    case ButtonState.PROCESSING:
      return "thinking";
    default:
      return "ready";
  }
}

/** @deprecated usar visualFlagsForButton(deriveButtonState(...)) */
export function visualFlagsForCore(coreState, captureMode) {
  return visualFlagsForButton(deriveButtonState(coreState, captureMode));
}

/** @deprecated */
export function coreToAppStatus(coreState, captureMode) {
  return buttonToAppStatus(deriveButtonState(coreState, captureMode));
}
