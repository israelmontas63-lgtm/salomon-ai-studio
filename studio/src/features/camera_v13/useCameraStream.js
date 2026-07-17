/**
 * Stream de cámara aislado — sin SalomonBridge ni modoInterfaz del shield.
 */
import { useCallback, useEffect, useRef, useState } from "react";

export function useCameraStream(active, facing) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const seqRef = useRef(0);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");

  const stop = useCallback(() => {
    seqRef.current += 1;
    const s = streamRef.current;
    streamRef.current = null;
    if (videoRef.current) {
      try {
        videoRef.current.srcObject = null;
      } catch (_) {}
    }
    if (s) {
      try {
        s.getTracks().forEach((t) => t.stop());
      } catch (_) {}
    }
    setReady(false);
  }, []);

  useEffect(() => {
    if (!active) {
      stop();
      return;
    }
    let cancelled = false;
    const seq = ++seqRef.current;
    setError("");
    setReady(false);

    (async () => {
      try {
        let stream;
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: { exact: facing } },
            audio: false,
          });
        } catch {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: { ideal: facing } },
            audio: false,
          });
        }
        if (cancelled || seq !== seqRef.current) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        const video = videoRef.current;
        if (video) {
          video.srcObject = stream;
          await video.play().catch(() => {});
        }
        setReady(true);
      } catch {
        if (!cancelled) setError("cam");
      }
    })();

    return () => {
      cancelled = true;
      stop();
    };
  }, [active, facing, stop]);

  const captureBlob = useCallback(async () => {
    const video = videoRef.current;
    if (!video || video.readyState < 2) return null;
    const canvas = document.createElement("canvas");
    const vw = video.videoWidth || 720;
    const vh = video.videoHeight || 1280;
    canvas.width = vw;
    canvas.height = vh;
    const ctx = canvas.getContext("2d");
    const mirror = facing === "user";
    if (mirror) {
      ctx.translate(vw, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(video, 0, 0, vw, vh);
    return new Promise((resolve) => {
      canvas.toBlob((b) => resolve(b), "image/jpeg", 0.88);
    });
  }, [facing]);

  return { videoRef, ready, error, stop, captureBlob, streamRef };
}
