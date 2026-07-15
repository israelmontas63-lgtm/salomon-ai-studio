import VoiceButton from "./VoiceButton";

export default function BottomBar({
  orchestrator,
  keyboardVisible,
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

  return (
    <div className="bottom-bar">
      <div className="controls-row">
        <button
          type="button"
          className="control-btn"
          aria-label="Cámara"
          onClick={onOpenCamera}
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
          className="control-btn"
          aria-label={keyboardVisible ? "Ocultar teclado" : "Mostrar teclado"}
          onClick={onToggleKeyboard}
        >
          ⌨️
        </button>
      </div>

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

      {keyboardVisible && (
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
          />
          <button type="submit" className="send-btn" disabled={sending || !inputValue?.trim()}>
            Enviar
          </button>
        </form>
      )}
    </div>
  );
}
