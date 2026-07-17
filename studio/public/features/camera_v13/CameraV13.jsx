import { useCallback, useState } from "react";
import { useCameraStream } from "./useCameraStream.js";
import LockButton from "./controls/LockButton.jsx";
import CamToggle from "./controls/CamToggle.jsx";
import FlipButton from "./controls/FlipButton.jsx";
import ShutterButton from "./controls/ShutterButton.jsx";
import "./cameraV13.css";

/**
 * Cámara v13 — UI individual.
 * No usa SalomonBridge, no dicta, no conversa.
 * Solo: candado · cámara · giro · disparador.
 */
export default function CameraV13({ open, onClose, onCaptured }) {
  const [facing, setFacing] = useState("environment");
  const [locked, setLocked] = useState(true);
  const [shotFx, setShotFx] = useState(false);
  const { videoRef, ready, captureBlob } = useCameraStream(!!open, facing);

  const shoot = useCallback(async () => {
    if (!ready || locked === false && false) {
      /* locked no bloquea disparo; solo UI de candado */
    }
    if (!ready) return;
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
      source: "camera_v13",
    });
  }, [ready, captureBlob, facing, locked, onCaptured]);

  if (!open) return null;

  return (
    <div
      className={`cam13-root${facing === "user" ? " is-front" : ""}${shotFx ? " is-shot" : ""}`}
      data-salomon-camera-v13="1"
      data-isolated="1"
    >
      <video ref={videoRef} className="cam13-video" playsInline muted autoPlay />
      <div className="cam13-flash" aria-hidden="true" />

      <LockButton locked={locked} onToggle={() => setLocked((v) => !v)} />

      <div className="cam13-cluster-right">
        <CamToggle active onToggle={onClose} />
        <FlipButton
          onFlip={() => setFacing((f) => (f === "environment" ? "user" : "environment"))}
        />
      </div>

      <div className="cam13-shutter-wrap">
        <ShutterButton onShoot={shoot} disabled={!ready} />
      </div>

      {/* Toque en preview = disparo (individual) */}
      <button type="button" className="cam13-stage-hit" aria-label=" " onClick={shoot} />
    </div>
  );
}
