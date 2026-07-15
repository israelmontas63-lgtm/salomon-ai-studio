import { useEffect } from "react";

/**
 * Drawer Glassmorphism — vacío por defecto (placeholder).
 */
export default function GlassPanel({
  open,
  title,
  items = [],
  onClose,
  side = "left",
  onItemClick,
}) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape") onClose?.();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const empty = !items || items.length === 0;
  const hint =
    side === "left"
      ? "Registro, correo y planes de servicio. Pronto aquí."
      : "Herramientas de Salomón. Pronto aquí.";

  return (
    <>
      <div className="glass-backdrop" onClick={onClose} aria-hidden="true" />
      <aside
        className={`glass-panel glass-panel--${side} drawer-open`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header className="glass-panel__header">
          <h2>{title}</h2>
          <button
            type="button"
            className="glass-panel__close"
            onClick={onClose}
            aria-label="Cerrar"
          >
            ✕
          </button>
        </header>
        <nav className="glass-panel__list">
          {empty ? (
            <div className="drawer-placeholder">
              <strong>{title}</strong>
              {hint}
            </div>
          ) : (
            items.map((item) => (
              <button
                key={item}
                type="button"
                className="glass-panel__item"
                onClick={() => onItemClick?.(item)}
              >
                {item}
              </button>
            ))
          )}
        </nav>
      </aside>
    </>
  );
}
