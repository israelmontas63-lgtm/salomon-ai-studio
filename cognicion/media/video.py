"""Edición básica de video — MoviePy (cortes, overlay, filtros)."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from settings import DATA_DIR

_UPLOADS = DATA_DIR / "media" / "uploads"
_EDITADOS = DATA_DIR / "media" / "editados"
_UPLOADS.mkdir(parents=True, exist_ok=True)
_EDITADOS.mkdir(parents=True, exist_ok=True)

OPERACIONES = frozenset({"cortar", "overlay_texto", "filtro_bn", "filtro_brillo", "info"})


def guardar_upload(nombre: str, contenido: bytes) -> Path:
    safe = "".join(c for c in (nombre or "video.mp4") if c.isalnum() or c in "._-")[:80]
    if "." not in safe:
        safe += ".mp4"
    path = _UPLOADS / f"{uuid.uuid4().hex[:10]}_{safe}"
    path.write_bytes(contenido)
    return path


def _moviepy_disponible() -> bool:
    try:
        import moviepy  # noqa: F401

        return True
    except Exception:
        return False


def info_video(ruta: Path) -> dict[str, Any]:
    if not _moviepy_disponible():
        return {
            "exito": False,
            "error": "moviepy_no_instalado",
            "detalle": "pip install moviepy imageio-ffmpeg",
        }
    from moviepy import VideoFileClip

    with VideoFileClip(str(ruta)) as clip:
        return {
            "exito": True,
            "duracion_s": float(clip.duration or 0),
            "fps": float(clip.fps or 0),
            "tamano": [int(clip.w or 0), int(clip.h or 0)],
            "ruta": str(ruta),
        }


def editar_video(
    ruta_entrada: str | Path,
    *,
    operacion: str = "cortar",
    inicio: float = 0.0,
    fin: float | None = None,
    texto_overlay: str = "",
    brillo: float = 1.2,
) -> dict[str, Any]:
    """
    Operaciones:
    - cortar: subclip inicio→fin
    - overlay_texto: texto centrado inferior
    - filtro_bn: blanco y negro
    - filtro_brillo: multiplica luminosidad
    - info: metadatos sin escribir archivo
    """
    path = Path(ruta_entrada)
    if not path.exists():
        return {"exito": False, "error": "archivo_no_encontrado"}

    op = (operacion or "cortar").strip().lower()
    if op not in OPERACIONES:
        return {"exito": False, "error": "operacion_invalida", "permitidas": sorted(OPERACIONES)}

    if not _moviepy_disponible():
        # Copia passthrough para no romper el flujo operativo
        dest = _EDITADOS / f"copy_{uuid.uuid4().hex[:10]}_{path.name}"
        shutil.copy2(path, dest)
        return {
            "exito": True,
            "motor": "passthrough",
            "aviso": "MoviePy no instalado; se devolvió copia sin editar.",
            "operacion": op,
            "ruta": str(dest),
            "url_relativa": f"/media/editados/{dest.name}",
        }

    if op == "info":
        return info_video(path)

    from moviepy import VideoFileClip, TextClip, CompositeVideoClip

    out_name = f"{op}_{uuid.uuid4().hex[:10]}.mp4"
    out_path = _EDITADOS / out_name

    try:
        clip = VideoFileClip(str(path))
        dur = float(clip.duration or 0)
        t0 = max(0.0, float(inicio or 0))
        t1 = float(fin) if fin is not None else dur
        t1 = min(max(t0 + 0.1, t1), dur) if dur else t1

        if op == "cortar":
            result = clip.subclipped(t0, t1) if hasattr(clip, "subclipped") else clip.subclip(t0, t1)
        else:
            base = clip.subclipped(t0, t1) if hasattr(clip, "subclipped") else clip.subclip(t0, t1)
            if op == "filtro_bn":
                try:
                    from moviepy.video.fx import BlackAndWhite

                    result = base.with_effects([BlackAndWhite()])
                except Exception:
                    import numpy as np

                    def _bn(get_frame, t):
                        frame = get_frame(t)
                        g = frame.mean(axis=2, keepdims=True)
                        return np.repeat(g, 3, axis=2).astype(frame.dtype)

                    try:
                        result = base.transform(_bn)
                    except Exception:
                        try:
                            result = base.fl(_bn)
                        except Exception:
                            result = base
            elif op == "filtro_brillo":
                factor = max(0.3, min(2.5, float(brillo or 1.2)))

                def _bright(get_frame, t):
                    frame = get_frame(t)
                    import numpy as np

                    return np.clip(frame.astype("float32") * factor, 0, 255).astype("uint8")

                try:
                    result = base.transform(_bright)
                except Exception:
                    try:
                        result = base.fl(_bright)
                    except Exception:
                        result = base
            elif op == "overlay_texto":
                txt = (texto_overlay or "Salomón").strip()[:120]
                try:
                    txt_clip = TextClip(
                        text=txt,
                        font_size=42,
                        color="white",
                        method="caption",
                        size=(int(base.w * 0.9), None),
                    )
                    txt_clip = txt_clip.with_duration(base.duration).with_position(
                        ("center", "bottom")
                    )
                except TypeError:
                    txt_clip = (
                        TextClip(
                            txt,
                            fontsize=42,
                            color="white",
                            method="caption",
                            size=(int(base.w * 0.9), None),
                        )
                        .set_duration(base.duration)
                        .set_position(("center", "bottom"))
                    )
                result = CompositeVideoClip([base, txt_clip])
            else:
                result = base

        result.write_videofile(
            str(out_path),
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )
        clip.close()
        try:
            result.close()
        except Exception:
            pass

        return {
            "exito": True,
            "motor": "moviepy",
            "operacion": op,
            "ruta": str(out_path),
            "url_relativa": f"/media/editados/{out_path.name}",
            "inicio": t0,
            "fin": t1,
        }
    except Exception as exc:
        return {
            "exito": False,
            "error": type(exc).__name__,
            "detalle": str(exc)[:400],
            "operacion": op,
        }
