# -*- coding: utf-8 -*-
"""
Genera / completa .env con variables SBI-PRO (tokens seguros).
No pisa CARTESIA_* ni otras claves ya definidas.

Uso:
  python api/sbi/setup_env.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from api.sbi.common import asegurar_dirs, generar_secreto, upsert_env  # noqa: E402


SBI_DEFAULTS = {
    "SBI_ENABLED": "false",
    "SBI_MODE": "soft",
    "SBI_THRESHOLD": "0.82",
    "SBI_OWNER_NAME": "Israel Monta",
    "SBI_CHALLENGE_PHRASE": "Salomon autentica a Israel",
    "SBI_TEMPLATE_PATH": "data/seguridad/sbi_israel.json",
    "SBI_API_BASE": "http://127.0.0.1:8000",
}


def _leer_env(path: Path) -> dict[str, str]:
    vals: dict[str, str] = {}
    if not path.is_file():
        return vals
    for ln in path.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        vals[k.strip()] = v.strip()
    return vals


def main() -> int:
    asegurar_dirs()
    env_path = ROOT / ".env"
    example = ROOT / ".env.example"

    if not env_path.is_file() and example.is_file():
        env_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[SBI] Creado .env desde .env.example", flush=True)
    elif not env_path.is_file():
        env_path.write_text("# Salomón AI — entorno local\n", encoding="utf-8")
        print("[SBI] Creado .env vacío", flush=True)

    actual = _leer_env(env_path)
    for k, v in SBI_DEFAULTS.items():
        if not actual.get(k):
            upsert_env(k, v, env_path=env_path)

    # Tokens: generar solo si faltan
    for clave in ("SBI_ENROLL_TOKEN", "SBI_RECOVERY_KEY", "SBI_TEMPLATE_SECRET"):
        if not actual.get(clave):
            secreto = generar_secreto(24)
            upsert_env(clave, secreto, env_path=env_path)
            print(f"[SBI] Generado {clave}", flush=True)
        else:
            print(f"[SBI] Conservado {clave} (ya existía)", flush=True)

    actual = _leer_env(env_path)
    print("", flush=True)
    print("=== SBI-PRO listo en .env (local) ===", flush=True)
    print(f"SBI_ENABLED={actual.get('SBI_ENABLED')}", flush=True)
    print(f"SBI_MODE={actual.get('SBI_MODE')}", flush=True)
    print(f"SBI_ENROLL_TOKEN={actual.get('SBI_ENROLL_TOKEN')}", flush=True)
    print(f"SBI_RECOVERY_KEY={actual.get('SBI_RECOVERY_KEY')}", flush=True)
    print(f"SBI_TEMPLATE_SECRET={actual.get('SBI_TEMPLATE_SECRET')}", flush=True)
    print("", flush=True)
    print("Copia esos tres secretos al Dashboard de Render > Environment.", flush=True)
    print("Deja SBI_ENABLED=false en Render hasta enrollar tu voz.", flush=True)
    print("", flush=True)
    print("Siguiente paso (con tu WAV):", flush=True)
    print("  python api/sbi/enroll.py data/seguridad/samples/israel.wav --activar", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
