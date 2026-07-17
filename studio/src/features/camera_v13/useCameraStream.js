/**
 * Dual-stream hot-swap — sin Bridge / modoInterfaz.
 * Activo + standby; switchCamera <300ms cuando dual OK.
 */
import { useCallback, useEffect, useRef, useState } from "react";

const OTHER = (f) => (f === "user" ? "environment" : "user");

async function acquire(facing) {
  try {
    return await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { exact: facing }, width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    });
  } catch {
    return navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: facing }, width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    });
  }
}

function waitFrame(video, ms = 1500) {
  return new Promise((resolve) => {
    if (!video) return resolve(false);
    if (video.readyState >= 2 && video.videoWidth > 0) return resolve(true);
    let done = false;
    const t = setTimeout(() => {
      if (!done) {
        done = true;
        resolve(video.readyState >= 2);
      }
    }, ms);
    const ok = () => {
      if (done) return;
      done = true;
      clearTimeout(t);
      resolve(true);
    };
    video.addEventListener("loadeddata", ok, { once: true });
    video.addEventListener("playing", ok, { once: true });
  });
}

function stopStream(stream) {
  if (!stream) return;
  try {
    stream.getTracks().forEach((t) => t.stop());
  } catch (_) {}
}

export function useCameraStream(active, facing) {
  const videoEnvRef = useRef(null);
  const videoUserRef = useRef(null);
  const streamsRef = useRef({ environment: null, user: null });
  const dualOkRef = useRef(true);
  const warmingRef = useRef({ environment: false, user: false });
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [lastSwitchMs, setLastSwitchMs] = useState(0);

  const videoRefFor = useCallback((f) => (f === "user" ? videoUserRef : videoEnvRef), []);

  const attach = useCallback(async (f, stream) => {
    const video = videoRefFor(f).current;
    if (!video) {
      stopStream(stream);
      return false;
    }
    stopStream(streamsRef.current[f]);
    streamsRef.current[f] = stream;
    video.srcObject = stream;
    await video.play().catch(() => {});
    const ok = await waitFrame(video);
    return ok;
  }, [videoRefFor]);

  const stopAll = useCallback(() => {
    stopStream(streamsRef.current.environment);
    stopStream(streamsRef.current.user);
    streamsRef.current = { environment: null, user: null };
    warmingRef.current = { environment: false, user: false };
    if (videoEnvRef.current) videoEnvRef.current.srcObject = null;
    if (videoUserRef.current) videoUserRef.current.srcObject = null;
    setReady(false);
  }, []);

  const warmStandby = useCallback(
    async (f) => {
      if (!active || !dualOkRef.current) return;
      if (streamsRef.current[f] || warmingRef.current[f]) return;
      warmingRef.current[f] = true;
      try {
        const stream = await acquire(f);
        if (!active) {
          stopStream(stream);
          return;
        }
        const ok = await attach(f, stream);
        if (!ok) return;
        const cur = facing;
        const curStream = streamsRef.current[cur];
        const live =
          curStream &&
          curStream.getVideoTracks().some((t) => t.readyState === "live");
        if (!live) {
          dualOkRef.current = false;
          stopStream(streamsRef.current[f]);
          streamsRef.current[f] = null;
          const s2 = await acquire(cur);
          await attach(cur, s2);
          setReady(true);
        }
      } catch {
        dualOkRef.current = false;
      } finally {
        warmingRef.current[f] = false;
      }
    },
    [active, attach, facing]
  );

  useEffect(() => {
    if (!active) {
      stopAll();
      dualOkRef.current = true;
      return;
    }
    let cancelled = false;
    setError("");
    setReady(false);
    (async () => {
      try {
        const stream = await acquire(facing);
        if (cancelled) {
          stopStream(stream);
          return;
        }
        const ok = await attach(facing, stream);
        if (!cancelled && ok) {
          setReady(true);
          setTimeout(() => {
            if (!cancelled) warmStandby(OTHER(facing));
          }, 80);
        }
      } catch {
        if (!cancelled) setError("cam");
      }
    })();
    return () => {
      cancelled = true;
      stopAll();
    };
    // Solo al abrir/cerrar — el flip lo hace switchCamera
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  const switchCamera = useCallback(
    async (nextFacing) => {
      const from = facing;
      const to = nextFacing || OTHER(from);
      if (to === from) return { ok: true, ms: 0 };
      const t0 = performance.now();
      const standbyStream = streamsRef.current[to];

      if (dualOkRef.current && standbyStream) {
        const ms = Math.round(performance.now() - t0);
        setLastSwitchMs(ms);
        setReady(true);
        setTimeout(() => warmStandby(from), 120);
        return { ok: true, ms, hot: true };
      }

      try {
        const stream = await acquire(to);
        const ok = await attach(to, stream);
        if (ok) {
          stopStream(streamsRef.current[from]);
          streamsRef.current[from] = null;
          if (videoRefFor(from).current) videoRefFor(from).current.srcObject = null;
        }
        const ms = Math.round(performance.now() - t0);
        setLastSwitchMs(ms);
        setReady(!!ok);
        setTimeout(() => {
          if (dualOkRef.current) warmStandby(from);
        }, 120);
        return { ok, ms, hot: false };
      } catch {
        setError("cam");
        return { ok: false, ms: Math.round(performance.now() - t0) };
      }
    },
    [facing, attach, warmStandby, videoRefFor]
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
    videoRef: videoRefFor(facing),
    ready,
    error,
    stop: stopAll,
    captureBlob,
    switchCamera,
    lastSwitchMs,
    dualOk: dualOkRef.current,
  };
}
