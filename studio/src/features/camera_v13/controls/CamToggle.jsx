export default function CamToggle({ active, onToggle }) {
  return (
    <button
      type="button"
      className={`cam13-icon${active ? " is-on" : ""}`}
      aria-label=" "
      onClick={onToggle}
    >
      <span className="cam13-ico-cam" aria-hidden="true" />
    </button>
  );
}
