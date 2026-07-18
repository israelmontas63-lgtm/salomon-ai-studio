# -*- coding: utf-8 -*-
"""
Prueba de micrófono en tiempo real — solo nivel de volumen (dB).
No graba ni enrola.

Uso:
  python scripts/mic_level_test.py
  python scripts/mic_level_test.py --segundos 12
"""

from __future__ import annotations

import argparse
import sys
import time

import numpy as np
import sounddevice as sd


def main() -> int:
    parser = argparse.ArgumentParser(description="Nivel de micrófono en dB (tiempo real)")
    parser.add_argument("--segundos", type=float, default=12.0)
    parser.add_argument("--rate", type=int, default=44100)
    args = parser.parse_args()

    try:
        info = sd.query_devices(kind="input")
    except Exception as exc:
        print(f"[MIC] ERROR: no hay dispositivo de entrada ({exc})", flush=True)
        return 2

    print("=== PRUEBA DE MICROFONO (solo dB) ===", flush=True)
    print(f"Dispositivo: {info.get('name')}", flush=True)
    print(f"Canales: {info.get('max_input_channels')} · rate={args.rate}", flush=True)
    print("Habla o haz ruido cerca del mic. Ctrl+C para salir antes.", flush=True)
    print("", flush=True)

    block = int(args.rate * 0.1)  # 100 ms
    t0 = time.time()
    peak_db = -120.0
    samples_ok = 0

    try:
        with sd.InputStream(samplerate=args.rate, channels=1, dtype="float32", blocksize=block) as stream:
            while (time.time() - t0) < args.segundos:
                data, overflowed = stream.read(block)
                rms = float(np.sqrt(np.mean(np.square(data.astype(np.float64)))))
                db = 20.0 * np.log10(rms + 1e-12)
                peak_db = max(peak_db, db)
                samples_ok += 1
                bar_n = max(0, min(40, int((db + 60) * 40 / 60)))  # -60..0 dB
                bar = "#" * bar_n
                flag = " OVERFLOW" if overflowed else ""
                print(f"\rNivel: {db:6.1f} dB  |{bar:<40}|  pico={peak_db:6.1f} dB{flag}", end="", flush=True)
    except KeyboardInterrupt:
        print("\n[MIC] Interrumpido por usuario.", flush=True)
    except Exception as exc:
        print(f"\n[MIC] ERROR: {type(exc).__name__}: {exc}", flush=True)
        return 1

    print("", flush=True)
    print("--- RESUMEN ---", flush=True)
    print(f"Bloques leidos: {samples_ok}", flush=True)
    print(f"Pico maximo: {peak_db:.1f} dB", flush=True)
    if peak_db < -50:
        print("DIAGNOSTICO: nivel muy bajo — el mic puede estar muteado o no escucharte.", flush=True)
    elif peak_db < -35:
        print("DIAGNOSTICO: nivel bajo — habla mas cerca o sube ganancia del mic.", flush=True)
    else:
        print("DIAGNOSTICO: hay senal util — el sistema te esta escuchando.", flush=True)
    print("(Sin grabacion ni enrolamiento)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
