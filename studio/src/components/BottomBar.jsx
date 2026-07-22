import { useCallback, useEffect, useRef, useState } from "react";
import VoiceButton from "./VoiceButton";
import "./bottomBarUx.css";

/**
 * Barra inferior: elevación sincronizada + modos aislados (WhatsApp-like).
 * No muta lógica de backend / 8 capas.
 */
export default function BottomBar({
  orchestrator,
  keyboardVisible,
  cameraOpen = false,
  inputValue,
  sending = false,
  onInputChange,
  onSend,
  onOpenCamera,
  onToggleKeyboard,
  onNotify,
  onOpenMedia,
  onToggleHandsFree,
}) {
  const handsFree = orchestrator?.handsFree;
  const voiceActive = Boolean(
    orchestrator?.captureMode ||
      orchestrator?.isBusy ||
      orchestrator?.buttonState === "listening" ||
      orchestrator?.buttonState === "recording"
  );

  const barRef = useRef(null);
  const [elevated, setElevated] = useState(false);
  const [interacting, setInteracting] = useState(false);

  const uiMode = cameraOpen
    ? "camera"
    : voiceActive
      ? "voice"
      : keyboardVisible
        ? "text"
        : "idle";

  const shouldElevate =
    interacting || cameraOpen || keyboardVisible || voiceActive;

  useEffect(() => {
    setElevated(shouldElevate);
  }, [shouldElevate]);

  useEffect(() => {
    const root = document.documentElement;
    const modes = ["camera", "text", "voice"];
    modes.forEach((m) => root.classList.remove(`salomon-ui-mode-${m}`));
    if (uiMode !== "idle") {
      root.classList.add(`salomon-ui-mode-${uiMode}`);
    }
    root.classList.toggle("salomon-controls-elevated", elevated);
    return () => {
      modes.forEach((m) => root.classList.remove(`salomon-ui-mode-${m}`));
      root.classList.remove("salomon-controls-elevated");
    };
  }, [uiMode, elevated]);

  const lift = useCallback(() => {
    setInteracting(true);
  }, []);

  const maybeLower = useCallback(() => {
    setInteracting(false);
  }, []);

  useEffect(() => {
    const onPointerDown = (e) => {
      const bar = barRef.current;
      if (!bar) return;
      if (bar.contains(e.target)) return;
      // Fuera de la barra → reposo (si no hay modo que sostenga elevación)
      setInteracting(false);
    };
    document.addEventListener("pointerdown", onPointerDown, true);
    return () => document.removeEventListener("pointerdown", onPointerDown, true);
  }, []);

  const openCamera = () => {
    lift();
    onOpenCamera?.();
  };

  const toggleKeyboard = () => {
    lift();
    onToggleKeyboard?.();
  };

  return (
    <div
      ref={barRef}
      className={[
        "bottom-bar",
        elevated ? "is-controls-elevated" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      data-ui-mode={uiMode}
      data-muta-fuentes="false"
    >
      <div
        className="controls-row"
        onPointerDown={lift}
        onFocusCapture={lift}
        onBlurCapture={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget)) {
            maybeLower();
          }
        }}
      >
        <button
          type="button"
          className={[
            "control-btn",
            "ui-smart-cam-btn",
            cameraOpen ? "is-cam-active" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          aria-label="Cámara"
          aria-pressed={cameraOpen}
          onClick={openCamera}
        >
          📷
        </button>

        <VoiceButton
          orchestrator={orchestrator}
          disabled={sending}
          onNotify={onNotify}
          onOpenMedia={onOpenMedia}
        />

        <button
          type="button"
          className={[
            "control-btn",
            "ui-write-btn",
            keyboardVisible ? "is-write-active" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          aria-label={keyboardVisible ? "Ocultar teclado" : "Mostrar teclado"}
          aria-pressed={keyboardVisible}
          onClick={toggleKeyboard}
        >
          ⌨️
        </button>
      </div>

      {uiMode !== "camera" && uiMode !== "voice" && (
        <div className="bottom-bar__meta">
          <button
            type="button"
            className={["hands-free-toggle", handsFree ? "is-on" : ""].join(" ")}
            onClick={onToggleHandsFree}
            aria-pressed={Boolean(handsFree)}
          >
            Manos libres {handsFree ? "ON" : "OFF"}
          </button>
        </div>
      )}

      {keyboardVisible && uiMode === "text" && (
        <form
          className="chat-input"
          onSubmit={(e) => {
            e.preventDefault();
            onSend?.();
          }}
        >
          <input
            type="text"
            value={inputValue}
            onChange={(e) => onInputChange?.(e.target.value)}
            placeholder="Escribe a Salomón…"
            aria-label="Mensaje"
            autoComplete="off"
            autoFocus
          />
          <button
            type="submit"
            className="send-btn"
            disabled={sending || !inputValue?.trim()}
          >
            Enviar
          </button>
        </form>
      )}
    </div>
  );
}
