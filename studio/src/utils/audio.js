/** Reproducción de audio TTS (base64). Devuelve función stop(). */
export function playSalomonAudio(audioBase64, audioMime = "audio/wav", hooks = {}) {
  if (!audioBase64) return () => {};
  let audio = null;
  let url = null;
  try {
    const binary = atob(audioBase64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], { type: audioMime || "audio/wav" });
    url = URL.createObjectURL(blob);
    audio = new Audio(url);
    audio.onplay = () => hooks.onStart?.();
    audio.onended = () => {
      if (url) URL.revokeObjectURL(url);
      url = null;
      hooks.onEnd?.();
    };
    audio.onerror = () => {
      if (url) URL.revokeObjectURL(url);
      url = null;
      hooks.onError?.();
    };
    audio.play().catch(() => hooks.onError?.());
  } catch {
    hooks.onError?.();
  }
  return () => {
    try {
      audio?.pause();
      if (url) URL.revokeObjectURL(url);
    } catch {
      /* noop */
    }
  };
}
