# -*- coding: utf-8 -*-
"""
Verificación SBI-PRO: WAV → base64 → POST /api/sbi/verify

Uso:
  python api/sbi/verify.py ruta/a/israel.wav
  python api/sbi/verify.py --recovery
  python api/sbi/verify.py israel.wav --base https://salomon-ai-studio-1.onrender.com
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
    recovery_key,
    wav_a_base64,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="SBI-PRO verify")
    parser.add_argument(
        "wav",
        type=Path,
        nargs="?",
        default=None,
        help="WAV a verificar (omitir si usas --recovery)",
    )
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument(
        "--recovery",
        action="store_true",
        help="Usa SBI_RECOVERY_KEY del .env (sin audio)",
    )
    parser.add_argument("--mime", default="audio/wav")
    args = parser.parse_args()

    url = f"{args.base.rstrip('/')}/api/sbi/verify"
    headers = api_key_headers()
    payload: dict = {"audio_mime": args.mime}

    if args.recovery:
        key = recovery_key()
        if not key:
            print("[SBI] Falta SBI_RECOVERY_KEY en .env", flush=True)
            return 1
        payload["recovery_key"] = key
    else:
        if not args.wav:
            print("[SBI] Indica un WAV o usa --recovery", flush=True)
            return 1
        wav_path = args.wav if args.wav.is_absolute() else (Path.cwd() / args.wav)
        if not wav_path.is_file():
            alt = ROOT / "data" / "seguridad" / "samples" / args.wav.name
            if alt.is_file():
                wav_path = alt
            else:
                print(f"[SBI] No encuentro: {args.wav}", flush=True)
                return 1
        payload["audio_base64"] = wav_a_base64(wav_path)
        print(f"[SBI] Verificando {wav_path}", flush=True)

    print(f"[SBI] POST {url}", flush=True)
    try:
        with httpx.Client(timeout=60.0) as client:
            res = client.post(url, headers=headers, json=payload)
    except httpx.ConnectError:
        print("[SBI] Servidor no disponible. Arranca la API o usa --base.", flush=True)
        return 2

    print(f"[SBI] HTTP {res.status_code}", flush=True)
    try:
        body = res.json()
    except Exception:
        print(res.text[:500], flush=True)
        return 1

    print(json.dumps(body, ensure_ascii=False, indent=2), flush=True)
    if body.get("autenticado"):
        print("[SBI] AUTENTICADO", flush=True)
        return 0
    print("[SBI] NO AUTENTICADO", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
