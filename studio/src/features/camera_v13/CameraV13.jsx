import { useCallback, useState } from "react";
import { useCameraStream } from "./useCameraStream.js";
import LockButton from "./controls/LockButton.jsx";
import CamToggle from "./controls/CamToggle.jsx";
import FlipButton from "./controls/FlipButton.jsx";
import ShutterButton from "./controls/ShutterButton.jsx";
import "./cameraV13.css";

/**
 * Cámara v16 — failsafe Apagar/Esperar/Reanudar (Redmi 13C).
 */
export default function CameraV13({ open, onClose, onCaptured }) {
  const [facing, setFacing] = useState("environment");
  const [locked, setLocked] = useState(true);
  const [shotFx, setShotFx] = useState(false);
  const {
    videoEnvRef,
    videoUserRef,
    freezeRef,
    ready,
    switching,
    captureBlob,
    handleCameraSwitch,
  } = useCameraStream(!!open, facing);

  const status = open ? (switching ? "SWITCHING" : ready ? "STREAMING" : "ACTIVE") : "IDLE";

  const takePicture = useCallback(async () => {
    if (status === "IDLE" || switching || !ready) return;
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
      source: "camera_v16",
    });
  }, [status, switching, ready, captureBlob, facing, onCaptured]);

  const rotateCamera = useCallback(async () => {
    if (status === "IDLE" || switching) return;
    await handleCameraSwitch(setFacing);
  }, [status, switching, handleCameraSwitch]);

  const toggleCameraMode = useCallback(() => {
    if (switching) return;
    onClose?.();
  }, [onClose, switching]);

  if (!open) return null;

  return (
    <div
      className={`cam13-root${facing === "user" ? " is-front" : ""}${shotFx ? " is-shot" : ""}${switching ? " is-switching is-crossfading" : ""}`}
      data-salomon-camera-v13="1"
      data-salomon-camera-v16="1"
      data-isolated="1"
      data-cam-status={status}
      data-facing={facing}
      data-switch-mode="failsafe"
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
      <canvas ref={freezeRef} className="cam13-freeze" aria-hidden="true" />
      <button
        type="button"
        className="cam13-stage-hit"
        aria-label=" "
        onClick={takePicture}
        disabled={switching}
      />
      <div className="cam13-flash" aria-hidden="true" />

      <LockButton locked={locked} onToggle={() => setLocked((v) => !v)} />

      <div className="cam13-cluster-right">
        <CamToggle active onToggle={toggleCameraMode} />
        <FlipButton onFlip={rotateCamera} disabled={switching} />
      </div>

      <div className="cam13-shutter-wrap">
        <ShutterButton onShoot={takePicture} disabled={!ready || switching} />
      </div>
    </div>
  );
}
