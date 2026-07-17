import { useCallback, useState } from "react";
import { useCameraStream } from "./useCameraStream.js";
import LockButton from "./controls/LockButton.jsx";
import CamToggle from "./controls/CamToggle.jsx";
import FlipButton from "./controls/FlipButton.jsx";
import ShutterButton from "./controls/ShutterButton.jsx";
import "./cameraV13.css";

/**
 * Cámara v15 — dual-stream hot-swap + crossfade.
 * No usa SalomonBridge, no dicta, no conversa.
 */
export default function CameraV13({ open, onClose, onCaptured }) {
  const [facing, setFacing] = useState("environment");
  const [locked, setLocked] = useState(true);
  const [shotFx, setShotFx] = useState(false);
  const [crossfading, setCrossfading] = useState(false);
  const { videoEnvRef, videoUserRef, ready, captureBlob, switchCamera } = useCameraStream(
    !!open,
    facing
  );

  const status = open ? (ready ? "STREAMING" : "ACTIVE") : "IDLE";

  const takePicture = useCallback(async () => {
    if (status === "IDLE" || !ready) return;
    const blob = await captureBlob();
    if (!blob) return;
    setShotFx(true);
    setTimeout(() => setShotFx(false), 900);
    onCaptured?.({
      blob,
      facing,
      isolated: true,
      deferChat: true,
      cameraOnly: true,
      source: "camera_v15",
    });
  }, [status, ready, captureBlob, facing, onCaptured]);

  const rotateCamera = useCallback(async () => {
    if (status === "IDLE") return;
    const next = facing === "environment" ? "user" : "environment";
    setCrossfading(true);
    const result = await switchCamera(next);
    setFacing(next);
    setTimeout(() => setCrossfading(false), 180);
    if (result?.ms != null) {
      console.info("[CameraV15] switchCamera", result.ms + "ms", result.hot ? "HOT" : "cold");
    }
  }, [status, facing, switchCamera]);

  const toggleCameraMode = useCallback(() => {
    onClose?.();
  }, [onClose]);

  if (!open) return null;

  return (
    <div
      className={`cam13-root${facing === "user" ? " is-front" : ""}${shotFx ? " is-shot" : ""}${crossfading ? " is-crossfading" : ""}`}
      data-salomon-camera-v13="1"
      data-salomon-camera-v14="1"
      data-salomon-camera-v15="1"
      data-isolated="1"
      data-cam-status={status}
      data-facing={facing}
    >
      <video
        ref={videoEnvRef}
        className={`cam13-video${facing === "environment" ? " is-active" : " is-standby"}`}
        data-facing="environment"
        playsInline
        muted
        autoPlay
      />
      <video
        ref={videoUserRef}
        className={`cam13-video${facing === "user" ? " is-active is-mirror" : " is-standby"}`}
        data-facing="user"
        playsInline
        muted
        autoPlay
      />
      <button
        type="button"
        className="cam13-stage-hit"
        aria-label=" "
        onClick={takePicture}
        onPointerUp={(e) => {
          if (e.pointerType === "touch") return;
          e.stopPropagation();
        }}
      />
      <div className="cam13-flash" aria-hidden="true" />

      <LockButton locked={locked} onToggle={() => setLocked((v) => !v)} />

      <div className="cam13-cluster-right">
        <CamToggle active onToggle={toggleCameraMode} />
        <FlipButton onFlip={rotateCamera} />
      </div>

      <div className="cam13-shutter-wrap">
        <ShutterButton onShoot={takePicture} disabled={!ready} />
      </div>
    </div>
  );
}
