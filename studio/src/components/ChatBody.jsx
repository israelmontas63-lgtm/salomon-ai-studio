import { useEffect, useRef } from "react";

export default function ChatBody({
  messages = [],
  onToggleSaved,
  accessibilityMode = false,
  onRepeatLast,
  canRepeat = false,
  onTypingDone,
}) {
  const scrollRef = useRef(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  return (
    <section className="chat-body" aria-label="Conversación">
      <div className="chat-scroll" ref={scrollRef}>
        {messages.map((m) => (
          <div
            key={m.id}
            className={[
              "bubble",
              m.role === "user" ? "bubble--user" : "bubble--ai",
              m.typing ? "is-typing" : "",
              accessibilityMode ? "bubble--a11y" : "",
            ].join(" ")}
          >
            <div className="bubble__text">{m.text}</div>
            {m.imageSrc ? (
              <img
                className="bubble__image"
                src={m.imageSrc}
                alt="Imagen generada por Salomón"
                loading="lazy"
              />
            ) : null}
            {m.role === "ai" && (
              <button
                type="button"
                className="bubble__save"
                onClick={() => onToggleSaved?.(m.id)}
                aria-label={m.saved ? "Quitar guardado" : "Guardar"}
              >
                {m.saved ? "★" : "☆"}
              </button>
            )}
          </div>
        ))}
      </div>
      {canRepeat && (
        <div className="chat-toolbar">
          <button type="button" className="chat-toolbar-btn" onClick={onRepeatLast}>
            ↺ Repetir última respuesta
          </button>
        </div>
      )}
    </section>
  );
}
