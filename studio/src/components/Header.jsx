/**
 * Header Salomón — Correo (izq) / Herramientas (der)
 */
export default function Header({
  appStatus = "ready",
  onOpenTools,
  onOpenAccount,
  showWelcomeFlash = false,
  isListeningOrSpeaking = false,
}) {
  const statusClass = `status-dot status-dot--${appStatus}`;

  return (
    <header className="studio-header">
      <button
        type="button"
        className="header-menu-btn"
        aria-label="Correo"
        title="Correo"
        onClick={onOpenAccount}
      >
        <span className="lines-icon" aria-hidden="true">
          <i />
          <i />
        </span>
        <span className="menu-label">Correo</span>
      </button>

      <div className="header-brand">
        <div
          className={["logo-wrap", showWelcomeFlash ? "logo-wrap--flash" : ""]
            .filter(Boolean)
            .join(" ")}
        >
          <span className={statusClass} aria-label={appStatus} />
          <a
            className={[
              "vinyl-card",
              isListeningOrSpeaking ? "vinyl-card--active" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            href="/"
            aria-label="Salomón"
          >
            <span className="vinyl-card__disc">
              <span className="vinyl-card__groove" />
              <span className="vinyl-card__label">
                <span className="vinyl-card__ss">SS</span>
              </span>
              <span className="vinyl-card__shine" />
            </span>
          </a>
        </div>
        <p className="logo-subtitle">Salomón AI</p>
      </div>

      <button
        type="button"
        className="header-menu-btn"
        aria-label="Herramientas"
        title="Herramientas"
        onClick={onOpenTools}
      >
        <span className="dots-icon" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        <span className="menu-label">Herramientas</span>
      </button>
    </header>
  );
}
