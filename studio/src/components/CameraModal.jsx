import { useCallback, useEffect, useRef, useState } from "react";

export default function CameraModal({ open, onClose, onCaptureComment }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [error, setError] = useState("");

  const stop = useCallback(() => {
    streamRef.current?.getTracks?.().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => {
    if (!open) {
      stop();
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
      } catch {
        setError("No se pudo abrir la cámara.");
      }
    })();
    return () => {
      cancelled = true;
      stop();
    };
  }, [open, stop]);

  if (!open) return null;

  return (
    <div className="camera-modal" role="dialog" aria-modal="true">
      <video ref={videoRef} playsInline muted className="camera-modal__video" />
      {error && <p className="camera-modal__error">{error}</p>}
      <div className="camera-modal__bar">
        <button type="button" className="camera-btn" onClick={onClose}>
          Cerrar
        </button>
        <button
          type="button"
          className="camera-btn camera-btn--primary"
          onClick={() => {
            onCaptureComment?.("Foto capturada.");
            onClose?.();
          }}
        >
          Capturar
        </button>
      </div>
    </div>
  );
}
