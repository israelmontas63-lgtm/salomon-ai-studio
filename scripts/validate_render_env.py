# -*- coding: utf-8 -*-
"""Valida TTS Cartesia vía entorno + lazy-load Free Tier (sin claves hardcodeadas)."""
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

    head, _, _ = cerebro.partition("def texto_a_voz")
    if "from cognicion.voz.cartesia_tts import" in head:
        ERRORS.append("cerebro.py importa cartesia_tts de forma eager (debe ser lazy)")
    else:
        OK.append("cerebro.py no importa cartesia_tts al boot")

    if "hablar_salomon" in cerebro and "cartesia_tts" in cerebro:
        OK.append("cerebro.py enlaza TTS a Cartesia Sonic-3.5 (lazy)")
    else:
        ERRORS.append("cerebro.py no enlaza TTS a Cartesia")

    if "elevenlabs" in cerebro.lower() or "ELEVENLABS" in cerebro:
        ERRORS.append("cerebro.py aún contiene rastros ElevenLabs")
    else:
        OK.append("cerebro.py sin ElevenLabs")

    if "sonic-3.5" in voz and "websocket_connect" in voz and "_liberar_recursos" in voz:
        OK.append("cartesia_tts.py Sonic-3.5 WebSocket + liberación post-uso")
    else:
        ERRORS.append("Falta WebSocket Sonic-3.5 o _liberar_recursos")

    if 'from cartesia import Cartesia' in voz and "def _cliente" in voz:
        # debe estar dentro de función, no a nivel módulo antes de defs
        before_cliente = voz.split("def _cliente")[0]
        if "from cartesia import Cartesia" in before_cliente:
            ERRORS.append("import cartesia a nivel de módulo (debe ser solo en _cliente)")
        else:
            OK.append("import cartesia diferido dentro de _cliente()")
    else:
        ERRORS.append("No se encontró patrón lazy Cartesia")

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
