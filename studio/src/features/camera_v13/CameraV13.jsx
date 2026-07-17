import { useCallback, useEffect, useRef, useState } from "react";
import { MediaStreamManager, ENGINE_STATUS } from "./MediaStreamManager.js";
import LockButton from "./controls/LockButton.jsx";
import CamToggle from "./controls/CamToggle.jsx";
import FlipButton from "./controls/FlipButton.jsx";
import ShutterButton from "./controls/ShutterButton.jsx";
import "./cameraV13.css";

/**
 * Cámara v20 — UI sobre MediaStreamManager (engine nativo).
 */
export default function CameraV13({ open, onClose, onCaptured }) {
  const videoRef = useRef(null);
  const freezeRef = useRef(null);
  const managerRef = useRef(null);
  const [facing, setFacing] = useState("environment");
  const [locked, setLocked] = useState(true);
  const [shotFx, setShotFx] = useState(false);
  const [engineStatus, setEngineStatus] = useState(ENGINE_STATUS.IDLE);

  const ready = engineStatus === ENGINE_STATUS.READY;
  const switching = engineStatus === ENGINE_STATUS.SWITCHING;

  useEffect(() => {
    if (!open) {
      managerRef.current?.stop();
      managerRef.current = null;
      setEngineStatus(ENGINE_STATUS.IDLE);
      setFacing("environment");
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
    // Re-bind elements after mount
    mgr.videoEl = videoRef.current;
    mgr.freezeEl = freezeRef.current;
    mgr.start("environment");
    return () => {
      mgr.stop();
      if (managerRef.current === mgr) managerRef.current = null;
    };
  }, [open]);

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
    });
  }, [ready, facing, onCaptured]);

  const rotateCamera = useCallback(async () => {
    if (!ready || !managerRef.current) return;
    const next = facing === "user" ? "environment" : "user";
    await managerRef.current.switchFacing(next);
    setFacing(managerRef.current.facing);
  }, [ready, facing]);

  if (!open) return null;

  return (
    <div
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
      <button
        type="button"
        className="cam13-stage-hit cam13-ctrl"
        aria-label=" "
        onClick={takePicture}
      />
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
