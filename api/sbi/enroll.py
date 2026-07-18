# -*- coding: utf-8 -*-
"""
Enrollment SBI-PRO: WAV → base64 → POST /api/sbi/enroll

Uso (servidor local o Render URL):
  python api/sbi/setup_env.py
  python api/sbi/enroll.py ruta/a/israel.wav
  python api/sbi/enroll.py ruta/a/israel.wav --activar
  python api/sbi/enroll.py israel.wav --base https://salomon-ai-studio-1.onrender.com
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from api.sbi.common import (  # noqa: E402
    DEFAULT_BASE,
    api_key_headers,
    asegurar_dirs,
    token_enroll,
    upsert_env,
    wav_a_base64,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="SBI-PRO enroll (WAV → API)")
    parser.add_argument("wav", type=Path, help="Ruta al archivo .wav de Israel")
    parser.add_argument(
        "--base",
        default=DEFAULT_BASE,
        help=f"Base URL API (default: {DEFAULT_BASE})",
    )
    parser.add_argument(
        "--activar",
        action="store_true",
        help="Tras enroll OK, pone SBI_ENABLED=true en .env local",
    )
    parser.add_argument(
        "--mime",
        default="audio/wav",
        help="MIME del audio (default audio/wav)",
    )
    args = parser.parse_args()

    asegurar_dirs()
    wav_path = args.wav if args.wav.is_absolute() else (Path.cwd() / args.wav)
    if not wav_path.is_file():
        # También buscar en samples/
        alt = ROOT / "data" / "seguridad" / "samples" / args.wav.name
        if alt.is_file():
            wav_path = alt
        else:
            print(f"[SBI] No encuentro el WAV: {args.wav}", flush=True)
            print(
                f"[SBI] Colócalo en: {ROOT / 'data' / 'seguridad' / 'samples'}",
                flush=True,
            )
            return 1

    token = token_enroll()
    if not token:
        print("[SBI] Falta SBI_ENROLL_TOKEN. Ejecuta primero:", flush=True)
        print("  python api/sbi/setup_env.py", flush=True)
        return 1

    b64 = wav_a_base64(wav_path)
    url = f"{args.base.rstrip('/')}/api/sbi/enroll"
    headers = api_key_headers()
    headers["X-SBI-Enroll-Token"] = token

    print(f"[SBI] Enviando enrollment → {url}", flush=True)
    print(f"[SBI] Archivo: {wav_path} ({wav_path.stat().st_size} bytes)", flush=True)

    try:
        with httpx.Client(timeout=60.0) as client:
            res = client.post(
                url,
                headers=headers,
                json={
                    "audio_base64": b64,
                    "audio_mime": args.mime,
                    "enroll_token": token,
                },
            )
    except httpx.ConnectError:
        print(
            "[SBI] No hay servidor en esa URL. Arranca Salomón "
            "(uvicorn app:app --port 8000) o usa --base con la URL de Render.",
            flush=True,
        )
        return 2

    print(f"[SBI] HTTP {res.status_code}", flush=True)
    try:
        body = res.json()
    except Exception:
        print(res.text[:500], flush=True)
        return 1

    print(json.dumps(body, ensure_ascii=False, indent=2), flush=True)
    if res.status_code != 200 or not body.get("ok"):
        return 1

    if args.activar:
        upsert_env("SBI_ENABLED", "true")
        print("[SBI] SBI_ENABLED=true escrito en .env local", flush=True)
        print(
            "[SBI] En Render: cambia también SBI_ENABLED=true tras copiar la plantilla "
            "o re-enrollar contra la URL Live.",
            flush=True,
        )

    print("", flush=True)
    print("Enrollment OK. Prueba:", flush=True)
    print(f"  python api/sbi/verify.py {wav_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
