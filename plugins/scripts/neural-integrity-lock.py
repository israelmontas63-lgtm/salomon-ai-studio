# -*- coding: utf-8 -*-
"""
Neural Integrity Lock v32 — checksum del Core vs Golden Snapshot.
Uso: python scripts/neural-integrity-lock.py
Exit 0 = LOCK_OK | Exit 1 = LOCK_BLOCKED (drift)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "salomon_integrity_ledger.json"
ATTEMPTS = ROOT / "salomon_integrity_attempts.jsonl"

# Presupuesto Zero-Lag: overhead de código nuevo sobre cámara
ZERO_LAG_OVERHEAD_MS = 100


def sha256(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def log_denied(component: str, detail: str) -> None:
    line = json.dumps(
        {
            "at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "component": component,
            "detail": detail,
            "protocol": "NEURAL_INTEGRITY_LOCK",
        },
        ensure_ascii=False,
    )
    with ATTEMPTS.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(
        f"[NeuralLock] Intento de modificación no autorizado detectado en {component}. Acceso denegado. ({detail})"
    )


def main() -> int:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    neural = ledger.get("neural_integrity_lock") or {}
    if not neural.get("active"):
        print("[NeuralLock] INACTIVE in ledger")
        return 2

    sigs = ledger.get("file_signatures_sha256") or {}
    # Neural core set
    core = neural.get("core_files") or list(sigs.keys())
    drift = 0
    for rel in core:
        path = ROOT / rel
        if not path.exists():
            log_denied(rel, "MISSING")
            drift += 1
            continue
        actual = sha256(rel)
        expected = sigs.get(rel)
        if not expected:
            print(f"[NeuralLock] WARN no signature for {rel}")
            continue
        if actual != expected:
            log_denied(rel, "CHECKSUM_DRIFT")
            print(f"  expected {expected}")
            print(f"  actual   {actual}")
            drift += 1
        else:
            print(f"OK {rel}")

    # Spot-check CameraEngine invariants (non-distraction: no extra runtime)
    engine = (ROOT / "studio/dist/camera-engine.js").read_text(encoding="utf-8", errors="replace")
    for needle in ("forceReset", "READY_TIMEOUT_MS = 2000", "STABLE_PRODUCTION_READY"):
        if needle not in engine:
            log_denied("camera-engine.js", f"INVARIANT_MISSING:{needle}")
            drift += 1
        else:
            print(f"OK invariant:{needle}")

    print(f"ZERO_LAG_BUDGET_MS={ZERO_LAG_OVERHEAD_MS}")
    if drift:
        print(f"[NeuralLock] BLOCKED — drift={drift}")
        return 1
    print("[NeuralLock] ACTIVE — Golden Snapshot MATCH — Core sealed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
