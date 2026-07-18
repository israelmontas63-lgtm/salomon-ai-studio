# -*- coding: utf-8 -*-
"""Valida que el TTS use Cartesia vía entorno (sin claves hardcodeadas)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OK: list[str] = []
ERRORS: list[str] = []


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    settings = read(ROOT / "settings.py")
    cerebro = read(ROOT / "cerebro.py")
    render = read(ROOT / "render.yaml")
    sw = read(ROOT / "studio" / "dist" / "sw.js")
    index = read(ROOT / "studio" / "dist" / "index.html")
    voz = read(ROOT / "cognicion" / "voz" / "cartesia_tts.py")

    if re.search(r'CARTESIA_API_KEY\s*=\s*os\.getenv\(\s*"CARTESIA_API_KEY"', settings):
        OK.append("settings.py lee CARTESIA_API_KEY desde entorno")
    else:
        ERRORS.append("settings.py no carga CARTESIA_API_KEY vía os.getenv")

    if "CARTESIA_VOICE_ID" in settings and "os.getenv" in settings:
        OK.append("settings.py declara CARTESIA_VOICE_ID")
    else:
        ERRORS.append("Falta CARTESIA_VOICE_ID en settings.py")

    if "hablar_salomon" in cerebro and "cartesia" in cerebro.lower():
        OK.append("cerebro.py enlaza TTS a Cartesia Sonic-3.5")
    else:
        ERRORS.append("cerebro.py no enlaza TTS a Cartesia")

    if "elevenlabs" in cerebro.lower() or "ELEVENLABS" in cerebro:
        ERRORS.append("cerebro.py aún contiene rastros ElevenLabs")
    else:
        OK.append("cerebro.py sin ElevenLabs")

    if "sonic-3.5" in voz and "websocket_connect" in voz:
        OK.append("cartesia_tts.py usa Sonic-3.5 WebSocket")
    else:
        ERRORS.append("Falta integración WebSocket Sonic-3.5")

    banned = re.search(
        r'CARTESIA_API_KEY\s*=\s*["\'][^"\']+["\']',
        settings + cerebro + voz,
    )
    if banned:
        ERRORS.append("Clave Cartesia hardcodeada detectada (prohibido)")
    else:
        OK.append("Sin claves Cartesia hardcodeadas")

    for key in ("CARTESIA_API_KEY", "CARTESIA_VOICE_ID"):
        if key in render:
            OK.append(f"render.yaml declara {key}")
        else:
            ERRORS.append(f"render.yaml no declara {key}")

    if "ELEVENLABS" in render:
        ERRORS.append("render.yaml aún declara ELEVENLABS_*")
    else:
        OK.append("render.yaml sin ELEVENLABS")

    if 'path.startsWith("/api/")' in sw or "path.startsWith('/api/')" in sw:
        OK.append("sw.js bypasea /api/ (voz/TTS no cacheados)")
    else:
        ERRORS.append("sw.js no bypasea /api/")

    if "salomon-update" in sw or "salomon-update" in index:
        OK.append("Cliente/SW CI/CD referenciado")
    else:
        ERRORS.append("Falta integración salomon-update en index/sw")

    print("OK:")
    for x in OK:
        print(" -", x)
    if ERRORS:
        print("ERRORS:")
        for x in ERRORS:
            print(" -", x)
        return 1
    print("validate_render_env: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
