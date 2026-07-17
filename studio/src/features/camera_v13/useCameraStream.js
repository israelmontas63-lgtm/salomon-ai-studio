/**
 * Failsafe single-stream switch — Apagar → Esperar 350ms → Reanudar.
 * Sin dual-stream (compatible Redmi 13C / HW bloqueado).
 */
import { useCallback, useEffect, useRef, useState } from "react";

const OTHER = (f) => (f === "user" ? "environment" : "user");
const HARDWARE_RELEASE_MS = 350;
const FADE_MS = 220;

async function acquire(facing) {
  try {
    return await navigator.mediaDevices.getUserMedia({
      video: { facingMode: facing },
      audio: false,
    });
  } catch {
    try {
      return await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: facing } },
        audio: false,
      });
    } catch {
      return navigator.mediaDevices.getUserMedia({
        video: { facingMode: { exact: facing } },
        audio: false,
      });
    }
  }
}

function waitFrame(video, ms = 2500) {
  return new Promise((resolve) => {
    if (!video) return resolve(false);
    if (video.readyState >= 2 && video.videoWidth > 0) return resolve(true);
    let done = false;
    const t = setTimeout(() => {
      if (!done) {
        done = true;
        resolve(video.readyState >= 2 && video.videoWidth > 0);
      }
    }, ms);
    const ok = () => {
      if (done || video.videoWidth < 1) return;
      done = true;
      clearTimeout(t);
      resolve(true);
    };
    video.addEventListener("loadeddata", ok);
    video.addEventListener("playing", ok);
  });
}

function stopStream(stream) {
  if (!stream) return;
  try {
    stream.getTracks().forEach((t) => {
      try {
        t.stop();
      } catch (_) {}
    });
  } catch (_) {}
}

function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

export function useCameraStream(active, facing) {
  const videoEnvRef = useRef(null);
  const videoUserRef = useRef(null);
  const freezeRef = useRef(null);
  const streamRef = useRef(null);
  const facingRef = useRef(facing);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [switching, setSwitching] = useState(false);
  const [lastSwitchMs, setLastSwitchMs] = useState(0);

  facingRef.current = facing;

  const videoRefFor = useCallback((f) => (f === "user" ? videoUserRef : videoEnvRef), []);

  const showFreeze = useCallback((video, mirror) => {
    const canvas = freezeRef.current;
    if (!canvas) return;
    try {
      const ctx = canvas.getContext("2d");
      if (video && video.readyState >= 2 && video.videoWidth > 0) {
        const w = video.videoWidth;
        const h = video.videoHeight;
        canvas.width = w;
        canvas.height = h;
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        if (mirror) {
          ctx.translate(w, 0);
          ctx.scale(-1, 1);
        }
        ctx.drawImage(video, 0, 0, w, h);
      } else {
        canvas.width = 720;
        canvas.height = 1280;
        ctx.fillStyle = "#111";
        ctx.fillRect(0, 0, 720, 1280);
      }
      canvas.classList.add("is-visible");
    } catch (_) {}
  }, []);

  const hideFreeze = useCallback(() => {
    freezeRef.current?.classList.remove("is-visible");
  }, []);

  const attach = useCallback(async (f, stream) => {
    const video = videoRefFor(f).current;
    if (!video) {
      stopStream(stream);
      return false;
    }
    streamRef.current = stream;
    video.srcObject = stream;
    await video.play().catch(() => {});
    return waitFrame(video);
  }, [videoRefFor]);

  const stopAll = useCallback(() => {
    stopStream(streamRef.current);
    streamRef.current = null;
    if (videoEnvRef.current) videoEnvRef.current.srcObject = null;
    if (videoUserRef.current) videoUserRef.current.srcObject = null;
    setReady(false);
  }, []);

  useEffect(() => {
    if (!active) {
      stopAll();
      setSwitching(false);
      return;
    }
    let cancelled = false;
    setError("");
    setReady(false);
    (async () => {
      try {
        const stream = await acquire(facingRef.current);
        if (cancelled) {
          stopStream(stream);
          return;
        }
        const ok = await attach(facingRef.current, stream);
        if (!cancelled) setReady(!!ok);
      } catch {
        if (!cancelled) setError("cam");
      }
    })();
    return () => {
      cancelled = true;
      stopAll();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  /**
   * Failsafe: freeze → stop tracks → wait 350ms → getUserMedia → commit facing → fade.
   * commitFacing(to) debe correr ANTES del hideFreeze (Paso 6).
   */
  const handleCameraSwitch = useCallback(
    async (commitFacing) => {
      if (!active || switching) return { ok: false, ms: 0 };
      const from = facingRef.current;
      const to = OTHER(from);
      const t0 = performance.now();
      setSwitching(true);

      const currentVideo = videoRefFor(from).current;
      showFreeze(currentVideo, from === "user");
      stopAll();

      await delay(HARDWARE_RELEASE_MS);

      try {
        const stream = await acquire(to);
        const ok = await attach(to, stream);
        if (!ok) {
          const s2 = await acquire(from);
          await attach(from, s2);
          hideFreeze();
          setReady(true);
          setSwitching(false);
          setLastSwitchMs(Math.round(performance.now() - t0));
          return { ok: false, ms: Math.round(performance.now() - t0), facing: from };
        }
        setReady(true);
        // Paso 6a — estado "user"/destino ANTES de quitar freeze
        if (typeof commitFacing === "function") commitFacing(to);
        facingRef.current = to;
        await delay(40);
        hideFreeze();
        await delay(FADE_MS);
        const ms = Math.round(performance.now() - t0);
        setLastSwitchMs(ms);
        setSwitching(false);
        console.info("[CameraV16] failsafe", from, "→", to, ms + "ms");
        return { ok: true, ms, facing: to };
      } catch (err) {
        hideFreeze();
        setError("cam");
        setSwitching(false);
        setLastSwitchMs(Math.round(performance.now() - t0));
        return { ok: false, ms: Math.round(performance.now() - t0), facing: from };
      }
    },
    [active, switching, videoRefFor, showFreeze, hideFreeze, stopAll, attach]
  );

  const captureBlob = useCallback(async () => {
    const video = videoRefFor(facing).current;
    if (!video || video.readyState < 2) return null;
    const canvas = document.createElement("canvas");
    const vw = video.videoWidth || 720;
    const vh = video.videoHeight || 1280;
    canvas.width = vw;
    canvas.height = vh;
    const ctx = canvas.getContext("2d");
    if (facing === "user") {
      ctx.translate(vw, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(video, 0, 0, vw, vh);
    return new Promise((resolve) => {
      canvas.toBlob((b) => resolve(b), "image/jpeg", 0.88);
    });
  }, [facing, videoRefFor]);

  return {
    videoEnvRef,
    videoUserRef,
    freezeRef,
    videoRef: videoRefFor(facing),
    ready,
    error,
    switching,
    stop: stopAll,
    captureBlob,
    handleCameraSwitch,
    switchCamera: handleCameraSwitch,
    lastSwitchMs,
  };
}
