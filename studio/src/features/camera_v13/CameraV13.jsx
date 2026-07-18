import { useCallback, useEffect, useRef, useState } from "react";
import { MediaStreamManager, ENGINE_STATUS } from "./MediaStreamManager.js";
import LockButton from "./controls/LockButton.jsx";
import CamToggle from "./controls/CamToggle.jsx";
import FlipButton from "./controls/FlipButton.jsx";
import ShutterButton from "./controls/ShutterButton.jsx";
import "./cameraV13.css";

const ZOOM_MIN = 1;
const ZOOM_MAX = 4;

function clampZoom(z) {
  return Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, z));
}

/**
 * Cámara v20 — UI sobre MediaStreamManager (engine nativo).
 * Captura: SOLO botón disparo. Pinch-to-zoom fluido en viewport.
 */
export default function CameraV13({ open, onClose, onCaptured }) {
  const videoRef = useRef(null);
  const freezeRef = useRef(null);
  const rootRef = useRef(null);
  const managerRef = useRef(null);
  const zoomRef = useRef({
    zoom: 1,
    target: 1,
    display: 1,
    raf: 0,
    pinch: { active: false, startDist: 0, startZoom: 1, moved: false },
  });
  const [facing, setFacing] = useState("environment");
  const [locked, setLocked] = useState(true);
  const [shotFx, setShotFx] = useState(false);
  const [engineStatus, setEngineStatus] = useState(ENGINE_STATUS.IDLE);

  const ready = engineStatus === ENGINE_STATUS.READY;
  const switching = engineStatus === ENGINE_STATUS.SWITCHING;

  const paintZoom = useCallback((z) => {
    const zoom = clampZoom(z);
    zoomRef.current.zoom = zoom;
    const video = videoRef.current;
    if (!video) return;
    video.style.transformOrigin = "center center";
    video.style.willChange = "transform";
    const mirror = managerRef.current?.getFacing?.() === "user" || facing === "user";
    video.style.transform = `${mirror ? "scaleX(-1) " : ""}scale(${zoom})`;
    if (rootRef.current) rootRef.current.dataset.zoom = zoom.toFixed(2);
  }, [facing]);

  const setZoomTarget = useCallback(
    (z) => {
      const state = zoomRef.current;
      state.target = clampZoom(z);
      if (state.raf) return;
      const tick = () => {
        state.raf = 0;
        const next = state.display + (state.target - state.display) * 0.32;
        state.display = Math.abs(state.target - next) < 0.002 ? state.target : next;
        paintZoom(state.display);
        if (state.display !== state.target) {
          state.raf = requestAnimationFrame(tick);
        }
      };
      state.raf = requestAnimationFrame(tick);
    },
    [paintZoom],
  );

  useEffect(() => {
    if (!open) {
      managerRef.current?.stop();
      managerRef.current = null;
      setEngineStatus(ENGINE_STATUS.IDLE);
      setFacing("environment");
      const z = zoomRef.current;
      if (z.raf) cancelAnimationFrame(z.raf);
      z.raf = 0;
      z.zoom = 1;
      z.target = 1;
      z.display = 1;
      return;
    }
    const mgr = new MediaStreamManager({
      videoEl: videoRef.current,
      freezeEl: freezeRef.current,
      onStatus: (status, _ms, fac) => {
        setEngineStatus(status);
        if (fac) setFacing(fac);
      },
    });
    managerRef.current = mgr;
    mgr.videoEl = videoRef.current;
    mgr.freezeEl = freezeRef.current;
    mgr.start("environment");
    return () => {
      mgr.stop();
      if (managerRef.current === mgr) managerRef.current = null;
    };
  }, [open]);

  // Pinch-to-zoom + orientation visual-only
  useEffect(() => {
    if (!open) return;
    const root = rootRef.current;
    if (!root) return;
    const state = zoomRef.current;
    const opts = { capture: true, passive: false };

    const dist = (t0, t1) => {
      const dx = t0.clientX - t1.clientX;
      const dy = t0.clientY - t1.clientY;
      return Math.hypot(dx, dy);
    };

    const onStart = (e) => {
      if (!e.touches || e.touches.length < 2) return;
      state.pinch.active = true;
      state.pinch.moved = false;
      state.pinch.startDist = dist(e.touches[0], e.touches[1]);
      state.pinch.startZoom = state.target || state.display || 1;
      if (e.cancelable) e.preventDefault();
      e.stopPropagation();
    };
    const onMove = (e) => {
      if (!state.pinch.active || !e.touches || e.touches.length < 2) return;
      if (e.cancelable) e.preventDefault();
      e.stopPropagation();
      if (!state.pinch.startDist) return;
      const ratio = dist(e.touches[0], e.touches[1]) / state.pinch.startDist;
      if (Math.abs(ratio - 1) > 0.03) state.pinch.moved = true;
      setZoomTarget(state.pinch.startZoom * ratio);
    };
    const onEnd = (e) => {
      if (!state.pinch.active) return;
      if (e.touches && e.touches.length >= 2) return;
      state.pinch.active = false;
      if (state.pinch.moved) {
        setTimeout(() => {
          state.pinch.moved = false;
        }, 320);
      }
    };

    root.addEventListener("touchstart", onStart, opts);
    root.addEventListener("touchmove", onMove, opts);
    root.addEventListener("touchend", onEnd, opts);
    root.addEventListener("touchcancel", onEnd, opts);

    const onOrient = () => {
      window.SalomonCameraActions?.onOrientationVisualOnly?.({
        log: (...a) => console.info("[CameraV13]", ...a),
      });
    };
    window.addEventListener("orientationchange", onOrient);
    try {
      screen.orientation?.addEventListener?.("change", onOrient);
    } catch {
      /* ignore */
    }

    return () => {
      root.removeEventListener("touchstart", onStart, opts);
      root.removeEventListener("touchmove", onMove, opts);
      root.removeEventListener("touchend", onEnd, opts);
      root.removeEventListener("touchcancel", onEnd, opts);
      window.removeEventListener("orientationchange", onOrient);
    };
  }, [open, setZoomTarget]);

  const takePicture = useCallback(async () => {
    if (!ready || !managerRef.current) return;
    const blob = await managerRef.current.captureBlob();
    if (!blob) return;
    setShotFx(true);
    setTimeout(() => setShotFx(false), 900);
    onCaptured?.({
      blob,
      facing: managerRef.current.getFacing?.() || facing,
      isolated: true,
      deferChat: true,
      cameraOnly: true,
      source: "camera_v20",
      zoom: zoomRef.current.zoom,
    });
  }, [ready, facing, onCaptured]);

  const rotateCamera = useCallback(async () => {
    // Solo facing — nunca captura
    if (!ready || !managerRef.current) return;
    const next = facing === "user" ? "environment" : "user";
    await managerRef.current.switchFacing(next);
    setFacing(managerRef.current.facing);
    paintZoom(zoomRef.current.display || 1);
  }, [ready, facing, paintZoom]);

  if (!open) return null;

  return (
    <div
      ref={rootRef}
      className={`cam13-root${facing === "user" ? " is-front" : ""}${shotFx ? " is-shot" : ""}${switching ? " is-switching" : ""}`}
      data-salomon-camera-v13="1"
      data-salomon-camera-v20="1"
      data-isolated="1"
      data-engine-status={engineStatus}
      data-facing={facing}
      data-switch-mode="engine-v20"
    >
      <video
        ref={videoRef}
        className={`cam13-video is-active${facing === "user" ? " is-mirror" : ""}`}
        playsInline
        muted
        autoPlay
      />
      <canvas ref={freezeRef} className="cam13-freeze" aria-hidden="true" />
      {/* Stage hit: sin captura — encapsulado en tools/camera_actions */}
      <div className="cam13-stage-hit" aria-hidden="true" style={{ pointerEvents: "none" }} />
      <div className="cam13-flash" aria-hidden="true" />

      <LockButton locked={locked} onToggle={() => setLocked((v) => !v)} />

      <div className="cam13-cluster-right">
        <CamToggle active onToggle={() => !switching && onClose?.()} />
        <FlipButton onFlip={rotateCamera} disabled={!ready || switching} />
      </div>

      <div className="cam13-shutter-wrap">
        <ShutterButton onShoot={takePicture} disabled={!ready} />
      </div>
    </div>
  );
}
