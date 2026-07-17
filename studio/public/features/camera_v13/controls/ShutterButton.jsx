export default function ShutterButton({ onShoot, disabled }) {
  return (
    <button
      type="button"
      className="cam13-shutter"
      aria-label=" "
      disabled={disabled}
      onClick={onShoot}
    >
      <span className="cam13-ring-plata" aria-hidden="true" />
      <span className="cam13-ico-cam-dark" aria-hidden="true" />
    </button>
  );
}
