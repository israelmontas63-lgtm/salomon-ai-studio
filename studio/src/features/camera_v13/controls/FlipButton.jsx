export default function FlipButton({ onFlip }) {
  return (
    <button
      type="button"
      className="cam13-icon"
      aria-label="Giro"
      data-cam-action="rotateCamera"
      onClick={(e) => {
        e.stopPropagation();
        onFlip?.(e);
      }}
      onPointerUp={(e) => e.stopPropagation()}
      onTouchEnd={(e) => {
        e.stopPropagation();
      }}
    >
      <span className="cam13-ico-flip" aria-hidden="true">
        <svg viewBox="0 0 24 24">
          <path d="M4 12a8 8 0 0 1 13.5-5.8M20 12a8 8 0 0 1-13.5 5.8" />
          <polyline points="16 4 17.5 6.2 14.2 6.5" />
          <polyline points="8 20 6.5 17.8 9.8 17.5" />
        </svg>
      </span>
    </button>
  );
}
