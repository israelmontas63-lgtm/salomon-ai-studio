export default function CamToggle({ active, onToggle }) {
  return (
    <button
      type="button"
      className={`cam13-icon${active ? " is-on" : ""}`}
      aria-label="Cámara"
      data-cam-action="toggleCameraMode"
      onClick={(e) => {
        e.stopPropagation();
        onToggle?.(e);
      }}
      onPointerUp={(e) => e.stopPropagation()}
      onTouchEnd={(e) => {
        e.stopPropagation();
      }}
    >
      <span className="cam13-ico-cam" aria-hidden="true" />
    </button>
  );
}
