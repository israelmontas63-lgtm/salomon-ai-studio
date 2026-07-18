# -*- coding: utf-8 -*-
"""
Captura de muestra de voz para SBI-PRO (Windows / micrófono).

Uso:
  pip install sounddevice
  python api/sbi/capturar.py
  python api/sbi/capturar.py --segundos 5 --salida security/credentials/voice_signature.wav

Frase a leer en voz alta:
  «Salomon autentica a Israel»
"""

from __future__ import annotations

import argparse
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from api.sbi.common import CREDENTIALS_DIR, asegurar_dirs  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Captura WAV para SBI-PRO")
    parser.add_argument("--segundos", type=float, default=5.0)
    parser.add_argument("--rate", type=int, default=16000)
    parser.add_argument(
        "--salida",
        type=Path,
        default=CREDENTIALS_DIR / "voice_signature.wav",
    )
    args = parser.parse_args()

    try:
        import numpy as np
        import sounddevice as sd
    except ImportError:
        print("[SBI] Falta sounddevice. Instala con:", flush=True)
        print("  pip install sounddevice", flush=True)
        return 2

    asegurar_dirs()
    out: Path = args.salida if args.salida.is_absolute() else (ROOT / args.salida)
    out.parent.mkdir(parents=True, exist_ok=True)

    print("", flush=True)
    print("=== CAPTURA SBI-PRO ===", flush=True)
    print("Lee en voz alta (tono natural):", flush=True)
    print('  "Salomon autentica a Israel"', flush=True)
    print(f"Duración: {args.segundos}s · {args.rate} Hz · mono", flush=True)
    print("Grabando en 3…", flush=True)
    import time

    for n in (2, 1):
        time.sleep(1)
        print(f"  {n}…", flush=True)
    time.sleep(1)
    print("¡AHORA!", flush=True)

    frames = int(args.rate * args.segundos)
    audio = sd.rec(frames, samplerate=args.rate, channels=1, dtype="float32")
    sd.wait()
    print("Listo. Guardando…", flush=True)

    peak = float(abs(audio).max()) or 1.0
    pcm = (audio[:, 0] / peak * 30000.0).astype("int16")
    with wave.open(str(out), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(args.rate)
        wf.writeframes(pcm.tobytes())

    print(f"[SBI] WAV guardado: {out} ({out.stat().st_size} bytes)", flush=True)
    print("", flush=True)
    print("Siguiente (servidor local o Render):", flush=True)
    print(f"  python api/sbi/enroll.py {out}", flush=True)
    print("NO uses --activar hasta que Israel diga: APROBADO: Activar SBI_ENABLED=true", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
