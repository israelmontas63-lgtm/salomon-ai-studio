# -*- coding: utf-8 -*-
"""
Captura biométrica de voz — Israel Montas (ISO-27001 oriented).

Graba 5 s por micrófono → security/credentials/voice_signature.wav
Deps: sounddevice, scipy, numpy

Uso:
  python scripts/record_voice.py
"""

from __future__ import annotations

import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "security" / "credentials" / "voice_signature.wav"
RATE = 16000
SEGUNDOS = 5.0
CHALLENGE = "Salomon autentica a Israel"


def main() -> int:
    try:
        import numpy as np
        import sounddevice as sd
        from scipy.io import wavfile  # noqa: F401 — dependencia requerida por protocolo
    except ImportError as exc:
        print(f"[SBI] Dependencia faltante: {exc}", flush=True)
        print("  pip install sounddevice scipy numpy", flush=True)
        return 2

    OUT.parent.mkdir(parents=True, exist_ok=True)

    print("", flush=True)
    print("=== CAPTURA BIOMÉTRICA SBI-PRO ===", flush=True)
    print(f"Destino: {OUT}", flush=True)
    print(f"Lee en voz alta: «{CHALLENGE}»", flush=True)
    print(f"Duración: {SEGUNDOS}s · {RATE} Hz · mono", flush=True)
    print("Preparación…", flush=True)
    for n in (3, 2, 1):
        print(f"  {n}…", flush=True)
        time.sleep(1.0)
    print("¡AHORA — habla!", flush=True)

    frames = int(RATE * SEGUNDOS)
    audio = sd.rec(frames, samplerate=RATE, channels=1, dtype="float32")
    sd.wait()

    peak = float(np.max(np.abs(audio))) or 1.0
    pcm = (audio[:, 0] / peak * 30000.0).astype(np.int16)

    # Persistencia WAV PCM16 (wave + scipy disponibles)
    with wave.open(str(OUT), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(pcm.tobytes())

    # Verificación de lectura con scipy
    rate_r, data_r = wavfile.read(str(OUT))
    if rate_r != RATE or getattr(data_r, "size", 0) < RATE // 2:
        print("[SBI] ERROR: archivo WAV inválido tras grabación", flush=True)
        return 1

    print("Grabación de firma de voz completada correctamente", flush=True)
    print(f"[SBI] bytes={OUT.stat().st_size} samples={data_r.size} rate={rate_r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
