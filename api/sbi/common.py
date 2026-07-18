# -*- coding: utf-8 -*-
"""Utilidades compartidas CLI SBI-PRO."""

from __future__ import annotations

import base64
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

CREDENTIALS_DIR = ROOT / "security" / "credentials"
DEFAULT_TEMPLATE = "security/credentials/sbi_israel.json"
DEFAULT_VOICE_WAV = CREDENTIALS_DIR / "voice_signature.wav"

load_dotenv(ROOT / ".env")
load_dotenv(CREDENTIALS_DIR / "sbi.env", override=True)

DEFAULT_BASE = os.getenv("SBI_API_BASE", "http://127.0.0.1:8000").rstrip("/")


def wav_a_base64(ruta: Path) -> str:
    data = ruta.read_bytes()
    if len(data) < 1000:
        raise SystemExit(f"Audio demasiado corto o vacío: {ruta}")
    if not (data[:4] == b"RIFF" or ruta.suffix.lower() == ".wav"):
        print("[SBI] Aviso: se espera WAV PCM; continuando…", flush=True)
    return base64.b64encode(data).decode("ascii")


def token_enroll() -> str:
    return (os.getenv("SBI_ENROLL_TOKEN") or "").strip()


def recovery_key() -> str:
    return (os.getenv("SBI_RECOVERY_KEY") or "").strip()


def api_key_headers() -> dict[str, str]:
    key = (os.getenv("SALOMON_API_KEY") or "").strip()
    h: dict[str, str] = {"Content-Type": "application/json"}
    if key:
        h["X-API-Key"] = key
    return h


def upsert_env(clave: str, valor: str, *, env_path: Path | None = None) -> None:
    """Crea o actualiza una clave en .env (o sbi.env del vault) sin borrar el resto."""
    if env_path is None and clave.startswith("SBI_"):
        # Preferir vault si ya existe; si no, .env raíz.
        vault = CREDENTIALS_DIR / "sbi.env"
        path = vault if vault.is_file() else (ROOT / ".env")
    else:
        path = env_path or (ROOT / ".env")
    lineas: list[str] = []
    if path.is_file():
        lineas = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    found = False
    pref = f"{clave}="
    for ln in lineas:
        if ln.startswith(pref) or ln.startswith(f"# {pref}"):
            out.append(f"{clave}={valor}")
            found = True
        else:
            out.append(ln)
    if not found:
        if out and out[-1].strip():
            out.append("")
        out.append(f"{clave}={valor}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def generar_secreto(nbytes: int = 24) -> str:
    return secrets.token_urlsafe(nbytes)


def asegurar_dirs() -> Path:
    dest = CREDENTIALS_DIR
    dest.mkdir(parents=True, exist_ok=True)
    samples = dest / "samples"
    samples.mkdir(parents=True, exist_ok=True)
    # Compat: carpeta histórica de samples (docs antiguos)
    legacy = ROOT / "data" / "seguridad" / "samples"
    legacy.mkdir(parents=True, exist_ok=True)
    keep = ROOT / "data" / "seguridad" / ".gitkeep"
    if not keep.exists():
        keep.write_text("", encoding="utf-8")
    return dest
