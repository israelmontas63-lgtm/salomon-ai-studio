#!/usr/bin/env python3
"""Genera SALOMON_API_KEY y la sincroniza con studio/.env (protección /api/*)."""

from __future__ import annotations

import re
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
STUDIO_ENV = ROOT / "studio" / ".env"


def main() -> None:
    key = secrets.token_urlsafe(32)
    text = ENV.read_text(encoding="utf-8") if ENV.exists() else ""
    if re.search(r"^SALOMON_API_KEY=\S", text, re.M):
        print("SALOMON_API_KEY ya existe en .env — no se sobrescribe.")
        print("Elimínala manualmente si quieres regenerar.")
        return
    text = text.rstrip() + f"\n\n# Protección API — header X-API-Key\nSALOMON_API_KEY={key}\n"
    ENV.write_text(text, encoding="utf-8")
    STUDIO_ENV.write_text(f"VITE_SALOMON_API_KEY={key}\n", encoding="utf-8")
    print("OK: claves sincronizadas en .env y studio/.env")
    print("Reinicia el backend y ejecuta: cd studio && npm run build")


if __name__ == "__main__":
    main()
