import { useCallback, useState } from "react";
import { useCameraStream } from "./useCameraStream.js";
import LockButton from "./controls/LockButton.jsx";
import CamToggle from "./controls/CamToggle.jsx";
import FlipButton from "./controls/FlipButton.jsx";
import ShutterButton from "./controls/ShutterButton.jsx";
import "./cameraV13.css";

/**
 * Cámara v14 — UI individual (eventos reconectados).
 * No usa SalomonBridge, no dicta, no conversa.
 * Solo: candado · cámara · giro · disparador.
 */
export default function CameraV13({ open, onClose, onCaptured }) {
  const [facing, setFacing] = useState("environment");
  const [locked, setLocked] = useState(true);
  const [shotFx, setShotFx] = useState(false);
  const { videoRef, ready, captureBlob } = useCameraStream(!!open, facing);

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
      source: "camera_v14",
    });
  }, [status, ready, captureBlob, facing, onCaptured]);

  const rotateCamera = useCallback(() => {
    if (status === "IDLE") return;
    setFacing((f) => (f === "environment" ? "user" : "environment"));
  }, [status]);

  const toggleCameraMode = useCallback(() => {
    onClose?.();
  }, [onClose]);

  if (!open) return null;

  return (
    <div
      className={`cam13-root${facing === "user" ? " is-front" : ""}${shotFx ? " is-shot" : ""}`}
      data-salomon-camera-v13="1"
      data-salomon-camera-v14="1"
      data-isolated="1"
      data-cam-status={status}
    >
      <video ref={videoRef} className="cam13-video" playsInline muted autoPlay />
      {/* Preview debajo de controles — no tapa botones */}
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
