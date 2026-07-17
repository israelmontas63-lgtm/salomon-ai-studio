export default function LockButton({ locked, onToggle }) {
  return (
    <button
      type="button"
      className={`cam13-lock${locked ? " is-locked" : ""}`}
      aria-label=" "
      onClick={onToggle}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="5" y="11" width="14" height="10" rx="2" />
        <path d={locked ? "M8 11V8a4 4 0 0 1 8 0v3" : "M8 11V8a4 4 0 0 1 8 0"} />
      </svg>
    </button>
  );
}
