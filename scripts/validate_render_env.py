#!/usr/bin/env python3
"""
Valida que el código sea compatible con el despliegue en Render.
No exige secretos locales: solo estructura / referencias correctas.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []
OK: list[str] = []


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        ERRORS.append(f"No se pudo leer {path}: {exc}")
        return ""


def main() -> int:
    settings = read(ROOT / "settings.py")
    cerebro = read(ROOT / "cerebro.py")
    render = read(ROOT / "render.yaml")
    sw = read(ROOT / "studio" / "dist" / "sw.js")
    index = read(ROOT / "studio" / "dist" / "index.html")
    app_py = read(ROOT / "app.py")

    if re.search(r'ELEVENLABS_API_KEY\s*=\s*os\.getenv\(\s*"ELEVENLABS_API_KEY"', settings):
        OK.append("settings.py lee ELEVENLABS_API_KEY desde entorno")
    else:
        ERRORS.append("settings.py no carga ELEVENLABS_API_KEY vía os.getenv")

    if "ELEVENLABS_VOICE_ID" in settings and "os.getenv" in settings:
        OK.append("settings.py declara ELEVENLABS_VOICE_ID")
    else:
        ERRORS.append("Falta ELEVENLABS_VOICE_ID en settings.py")

    if "xi-api-key" in cerebro and "ELEVENLABS_API_KEY" in cerebro:
        OK.append("cerebro.py usa ELEVENLABS_API_KEY para TTS")
    else:
        ERRORS.append("cerebro.py no enlaza TTS a ELEVENLABS_API_KEY")

    if re.search(r'ELEVENLABS_API_KEY\s*=\s*["\'][^"\']+["\']', settings + cerebro):
        ERRORS.append("Clave ElevenLabs hardcodeada detectada (prohibido)")
    else:
        OK.append("Sin claves ElevenLabs hardcodeadas")

    for key in ("ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID"):
        if key in render:
            OK.append(f"render.yaml declara {key}")
        else:
            ERRORS.append(f"render.yaml no declara {key}")

    if 'path.startsWith("/api/")' in sw or "path.startsWith('/api/')" in sw:
        OK.append("sw.js bypasea /api/ (voz/TTS no cacheados)")
    else:
        ERRORS.append("sw.js no bypasea /api/")

    if "salomon-update" in sw or "salomon-update" in index:
        OK.append("Cliente/SW CI/CD referenciado")
    else:
        ERRORS.append("Falta integración salomon-update en index/sw")

    if "salomon-ui-shield.js" in index and "vision-overlay.js" in index:
        shield_i = index.find("salomon-ui-shield.js")
        vision_i = index.find("vision-overlay.js")
        if 0 <= shield_i < vision_i:
            OK.append("index.html: shield antes que vision")
        else:
            ERRORS.append("index.html: orden shield/vision incorrecto")

    if "/api/version" in app_py:
        OK.append("app.py expone /api/version")
    else:
        ERRORS.append("Falta endpoint /api/version en app.py")

    print("=== validate_render_env ===")
    for line in OK:
        print(f"  OK  {line}")
    for line in ERRORS:
        print(f"  ERR {line}")

    if ERRORS:
        print(f"\nFALLÓ: {len(ERRORS)} problema(s)")
        return 1
    print(f"\nLISTO: {len(OK)} checks — compatible con Render")
    return 0


if __name__ == "__main__":
    sys.exit(main())
