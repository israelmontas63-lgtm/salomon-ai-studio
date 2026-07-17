export default function ShutterButton({ onShoot, disabled }) {
  return (
    <button
      type="button"
      className="cam13-shutter"
      aria-label="Disparador"
      data-cam-action="takePicture"
      disabled={disabled}
      onClick={(e) => {
        e.stopPropagation();
        if (!disabled) onShoot?.(e);
      }}
      onPointerUp={(e) => e.stopPropagation()}
      onTouchEnd={(e) => {
        e.stopPropagation();
      }}
    >
      <span className="cam13-ring-plata" aria-hidden="true" />
      <span className="cam13-ico-cam-dark" aria-hidden="true" />
    </button>
  );
}
