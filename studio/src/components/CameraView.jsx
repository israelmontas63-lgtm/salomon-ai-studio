import { useCallback, useEffect, useRef, useState } from "react";
import "./CameraView.css";

/**
 * Vista de cámara a pantalla completa.
 * Cuando está montada, el Chat NO existe en el DOM (render condicional en App).
 */
export default function CameraView({ onClose, onCaptured }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [facing, setFacing] = useState("user");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);

  const stopStream = useCallback(() => {
    try {
      streamRef.current?.getTracks?.().forEach((t) => t.stop());
    } catch {
      /* noop */
    }
    streamRef.current = null;
  }, []);

  const startStream = useCallback(
    async (mode) => {
      setError("");
      setReady(false);
      stopStream();
      if (!navigator.mediaDevices?.getUserMedia) {
        setError("Cámara no disponible en este dispositivo.");
        return;
      }
      try {
        let stream;
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: { exact: mode } },
            audio: false,
          });
        } catch {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: { ideal: mode } },
            audio: false,
          });
        }
        streamRef.current = stream;
        const video = videoRef.current;
        if (video) {
          video.srcObject = stream;
          await video.play().catch(() => {});
        }
        setReady(true);
      } catch {
        setError("No se pudo abrir la cámara selfie.");
      }
    },
    [stopStream]
  );

  useEffect(() => {
    void startStream(facing);
    return () => {
      stopStream();
    };
  }, [facing, startStream, stopStream]);

  const capturePhoto = useCallback(() => {
    if (busy || !ready) return;
    const video = videoRef.current;
    if (!video || video.readyState < 2) return;
    setBusy(true);
    try {
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth || 720;
      canvas.height = video.videoHeight || 1280;
      canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/jpeg", 0.88);
      const bin = atob(dataUrl.split(",")[1] || "");
      const arr = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i += 1) arr[i] = bin.charCodeAt(i);
      const blob = new Blob([arr], { type: "image/jpeg" });
      const detail = {
        blob,
        dataUrl,
        facing,
        mode: "photo",
        width: canvas.width,
        height: canvas.height,
      };
      window.dispatchEvent(new CustomEvent("salomon:ui-photo", { detail }));
      onCaptured?.(detail);
      onClose?.();
    } catch {
      setError("No se pudo capturar la foto.");
    } finally {
      setBusy(false);
    }
  }, [busy, ready, facing, onCaptured, onClose]);

  const flip = useCallback(() => {
    setFacing((f) => (f === "user" ? "environment" : "user"));
  }, []);

  return (
    <div className="camera-view" role="dialog" aria-modal="true" aria-label="Cámara Salomón">
      <video ref={videoRef} className="camera-view__video" playsInline muted autoPlay />

      <div className="camera-view__badge" aria-live="polite">
        {facing === "user" ? "CÁMARA ACTIVA — SELFIE" : "CÁMARA ACTIVA — TRASERA"}
      </div>

      {error && <p className="camera-view__error">{error}</p>}

      <button
        type="button"
        className="camera-view__close"
        aria-label="Cerrar cámara"
        onClick={() => onClose?.()}
      >
        ×
      </button>

      <p className="camera-view__hint">Solo el botón central dispara · voltear con el nodo</p>

      <button
        type="button"
        className="camera-view__flip"
        aria-label="Voltear cámara"
        onClick={flip}
        disabled={busy}
      >
        Voltear
      </button>

      <button
        type="button"
        className="camera-view__shutter"
        aria-label="Disparar foto"
        disabled={busy || !ready || Boolean(error)}
        onClick={capturePhoto}
      >
        <span className="camera-view__shutter-ring" aria-hidden="true" />
        <span className="camera-view__shutter-core" aria-hidden="true" />
      </button>
    </div>
  );
}
