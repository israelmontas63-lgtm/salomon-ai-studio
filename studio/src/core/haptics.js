/** Patrones hápticos del núcleo (ms o arrays). */
export const Haptic = Object.freeze({
  tap: 8,
  holdStart: 12,
  doubleTap: [10, 40, 10],
  tripleTap: [8, 30, 8, 30, 8],
  success: [15, 40, 15],
  error: [40, 60, 40],
  cancel: 25,
  speakingDone: 10,
  mediaDone: [12, 35, 12, 35, 20],
});

export function pulse(pattern) {
  try {
    if (typeof navigator !== "undefined" && navigator.vibrate) {
      navigator.vibrate(pattern);
    }
  } catch {
    /* noop */
  }
}
