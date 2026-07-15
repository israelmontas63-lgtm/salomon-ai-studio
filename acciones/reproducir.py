"""
Reproducción y limpieza automática de audio de Salomón.

Uso interno del agente / scripts: genera, guarda en data/audio, reproduce y limpia viejos.
"""

from __future__ import annotations

import base64
import subprocess
import time
from pathlib import Path
from typing import Any

from acciones.hablar import hablar

_AUDIO_DIR = Path(__file__).resolve().parent.parent / "data" / "audio"
_MAX_ARCHIVOS = 8
_MAX_EDAD_SEG = 60 * 60 * 24  # 24 h


def _asegurar_dir() -> Path:
    _AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    return _AUDIO_DIR


def limpiar_audio_viejo(*, max_archivos: int = _MAX_ARCHIVOS, max_edad_seg: int = _MAX_EDAD_SEG) -> int:
    """Elimina audios antiguos; deja solo los más recientes. Devuelve cuántos borró."""
    carpeta = _asegurar_dir()
    ahora = time.time()
    archivos = sorted(
        [p for p in carpeta.glob("salomon_*.*") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    borrados = 0
    for i, path in enumerate(archivos):
        edad = ahora - path.stat().st_mtime
        if i >= max_archivos or edad > max_edad_seg:
            try:
                path.unlink(missing_ok=True)
                borrados += 1
            except OSError:
                pass
    # Limpieza de restos sueltos en la raíz del proyecto
    raiz = carpeta.parent.parent
    for patron in ("hablar_prueba.*", "presentacion_oficial.*", "sapi_test.*", "hablar_respuesta.json"):
        for path in raiz.glob(patron):
            if path.is_file():
                try:
                    path.unlink(missing_ok=True)
                    borrados += 1
                except OSError:
                    pass
    return borrados


def _ext_desde_mime(mime: str | None) -> str:
    if not mime:
        return ".mp3"
    if "wav" in mime:
        return ".wav"
    if "mpeg" in mime or "mp3" in mime:
        return ".mp3"
    if "ogg" in mime:
        return ".ogg"
    return ".mp3"


def hablar_y_reproducir(texto: str, *, nombre: str | None = None) -> dict[str, Any]:
    """
    Genera audio con ElevenLabs, lo guarda en data/audio, lo reproduce y limpia viejos.
    """
    limpiar_audio_viejo()
    resultado = hablar(texto)
    if not resultado.get("exito") or not resultado.get("audio_base64"):
        return {**resultado, "reproducido": False, "ruta": None}

    carpeta = _asegurar_dir()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    base = nombre or f"salomon_{stamp}"
    ruta = carpeta / f"{base}{_ext_desde_mime(resultado.get('audio_mime'))}"
    ruta.write_bytes(base64.b64decode(resultado["audio_base64"]))

    subprocess.Popen(["cmd", "/c", "start", "", str(ruta.resolve())], shell=False)
    limpiar_audio_viejo()

    return {
        **resultado,
        "reproducido": True,
        "ruta": str(ruta),
    }
