"""
Colsub Media Engine — Multi-Model Routing (calidad Pro/Ultra).

Routing:
- Imágenes HD → Flux.1 Pro / Midjourney (gateway)
- Video → Runway Gen-3 Alpha / Kling AI
- Post-proceso → Krea.ai (upscale / refine)

El Orquestador elige el mejor motor; las claves viven en .env / secretos.
"""

from __future__ import annotations

import base64
import re
import uuid
from pathlib import Path
from typing import Any, Literal

import httpx

from settings import DATA_DIR

TareaMedia = Literal["imagen_hd", "video_gen", "postproceso", "desconocida"]

_DIR_GEN = DATA_DIR / "media" / "generadas"
_DIR_VID = DATA_DIR / "media" / "editados"
_DIR_GEN.mkdir(parents=True, exist_ok=True)
_DIR_VID.mkdir(parents=True, exist_ok=True)


def _http_timeout(poll: bool = False) -> float:
    try:
        from settings import MEDIA_HTTP_TIMEOUT, MEDIA_HTTP_TIMEOUT_POLL

        return float(MEDIA_HTTP_TIMEOUT_POLL if poll else MEDIA_HTTP_TIMEOUT)
    except Exception:
        return 30.0 if poll else 45.0


def _secreto(nombre: str, fallback_settings: str = "") -> str:
    """Lee clave de forma segura (secretos > settings > vacío)."""
    try:
        from cognicion.seguridad.secretos import obtener_secreto

        val = (obtener_secreto(nombre) or "").strip()
        if val:
            return val
    except Exception:
        pass
    if fallback_settings:
        try:
            import settings as st

            return str(getattr(st, fallback_settings, "") or "").strip()
        except Exception:
            pass
    return ""


def _cfg_media() -> dict[str, Any]:
    import settings as st

    return {
        "calidad_forzada": getattr(st, "MEDIA_CALIDAD_FORZADA", "pro_ultra"),
        "flux_url": getattr(st, "FLUX_API_URL", "").strip(),
        "flux_key": _secreto("FLUX_API_KEY", "FLUX_API_KEY"),
        "flux_model": getattr(st, "FLUX_MODEL", "flux-1-pro").strip(),
        "midjourney_url": getattr(st, "MIDJOURNEY_API_URL", "").strip(),
        "midjourney_key": _secreto("MIDJOURNEY_API_KEY", "MIDJOURNEY_API_KEY"),
        "runway_url": getattr(st, "RUNWAY_API_URL", "").strip()
        or "https://api.dev.runwayml.com/v1",
        "runway_key": _secreto("RUNWAY_API_KEY", "RUNWAY_API_KEY"),
        "runway_model": getattr(st, "RUNWAY_MODEL", "gen3a_alpha").strip(),
        "kling_url": getattr(st, "KLING_API_URL", "").strip(),
        "kling_key": _secreto("KLING_API_KEY", "KLING_API_KEY"),
        "kling_model": getattr(st, "KLING_MODEL", "kling-v1-pro").strip(),
        "krea_url": getattr(st, "KREA_API_URL", "").strip(),
        "krea_key": _secreto("KREA_API_KEY", "KREA_API_KEY"),
        "prefer_imagen": getattr(st, "MEDIA_PREFER_IMAGEN", "flux").strip().lower(),
        "prefer_video": getattr(st, "MEDIA_PREFER_VIDEO", "runway").strip().lower(),
        # Nunca degradar a “cheap” si hay clave Pro
        "forzar_pro": bool(getattr(st, "MEDIA_FORZAR_PRO", True)),
    }


# ── Routing inteligente ─────────────────────────────────────────────────────

_MARCAS_VIDEO = (
    "video",
    "clip",
    "animación",
    "animacion",
    "runway",
    "kling",
    "gen-3",
    "gen3",
    "motion",
    "secuencia",
)
_MARCAS_POST = (
    "upscale",
    "escala",
    "escalar",
    "refinar",
    "textura",
    "postproceso",
    "post-proceso",
    "krea",
    "mejorar imagen",
    "4k",
    "enhance",
)
_MARCAS_IMAGEN = (
    "imagen",
    "image",
    "foto",
    "fotorreal",
    "ilustra",
    "dibuja",
    "boceto",
    "genera",
    "crear imagen",
    "alta definición",
    "alta definicion",
    "hd",
    "flux",
    "midjourney",
    "mj",
    "render",
    "retrato",
    "dall-e",
    "dalle",
)


def clasificar_tarea(prompt: str, hint: str | None = None) -> TareaMedia:
    h = (hint or "").strip().lower()
    if h in ("imagen_hd", "video_gen", "postproceso"):
        return h  # type: ignore[return-value]
    t = (prompt or "").lower()
    if any(m in t for m in _MARCAS_POST):
        return "postproceso"
    if any(m in t for m in _MARCAS_VIDEO):
        return "video_gen"
    if any(m in t for m in _MARCAS_IMAGEN):
        return "imagen_hd"
    # Por defecto: imagen HD (hub creativo)
    return "imagen_hd"


def seleccionar_motor(tarea: TareaMedia, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Elige el mejor motor Pro/Ultra disponible para la tarea."""
    cfg = cfg or _cfg_media()
    forzar = cfg.get("forzar_pro", True)

    if tarea == "imagen_hd":
        prefer = cfg.get("prefer_imagen") or "flux"
        candidatos = []
        if prefer == "midjourney":
            candidatos = ["midjourney", "flux"]
        else:
            candidatos = ["flux", "midjourney"]
        for motor in candidatos:
            key = cfg.get(f"{motor}_key") if motor != "midjourney" else cfg.get("midjourney_key")
            url = cfg.get(f"{motor}_url") if motor != "midjourney" else cfg.get("midjourney_url")
            if motor == "flux":
                key, url = cfg["flux_key"], cfg["flux_url"]
            if key:
                modelo = cfg["flux_model"] if motor == "flux" else "midjourney-ultra"
                if forzar and motor == "flux" and "pro" not in modelo.lower():
                    modelo = "flux-1-pro"
                return {
                    "motor": motor,
                    "modelo": modelo,
                    "calidad": "pro_ultra",
                    "listo": True,
                    "url_gateway": url or "(default)",
                }
        return {
            "motor": "dalle_fallback",
            "modelo": "dall-e-3-hd",
            "calidad": "pro_ultra",
            "listo": bool(_secreto("OPENAI_API_KEY", "OPENAI_API_KEY")),
            "aviso": "Sin Flux/MJ: se usará DALL·E 3 HD o placeholder.",
        }

    if tarea == "video_gen":
        prefer = cfg.get("prefer_video") or "runway"
        orden = ["runway", "kling"] if prefer == "runway" else ["kling", "runway"]
        for motor in orden:
            key = cfg[f"{motor}_key"]
            if key:
                modelo = cfg["runway_model"] if motor == "runway" else cfg["kling_model"]
                if forzar:
                    if motor == "runway":
                        from settings import RUNWAY_MODEL_PRO

                        modelo = RUNWAY_MODEL_PRO or "gen3a_alpha"
                    if motor == "kling" and "pro" not in modelo.lower():
                        modelo = "kling-v1-pro"
                return {
                    "motor": motor,
                    "modelo": modelo,
                    "calidad": "pro_ultra",
                    "listo": True,
                    "url_gateway": cfg[f"{motor}_url"],
                }
        return {
            "motor": "moviepy_local",
            "modelo": "edicion_local",
            "calidad": "local",
            "listo": False,
            "aviso": "Sin Runway/Kling: solo edición local MoviePy disponible.",
        }

    # postproceso
    if cfg["krea_key"]:
        return {
            "motor": "krea",
            "modelo": "krea-upscale-pro",
            "calidad": "pro_ultra",
            "listo": True,
            "url_gateway": cfg["krea_url"] or "https://api.krea.ai",
        }
    return {
        "motor": "local_refine",
        "modelo": "pillow_sharpen",
        "calidad": "local",
        "listo": True,
        "aviso": "Sin Krea: refinamiento local básico.",
    }


# ── Proveedores ─────────────────────────────────────────────────────────────

def _guardar_bytes(datos: bytes, carpeta: Path, prefijo: str, ext: str) -> Path:
    path = carpeta / f"{prefijo}_{uuid.uuid4().hex[:12]}.{ext}"
    path.write_bytes(datos)
    return path


def _llamar_flux(prompt: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Flux.1 Pro vía gateway configurable (fal / replicate / custom)."""
    key = cfg["flux_key"]
    if not key:
        return {"exito": False, "error": "flux_api_key_ausente"}
    url = cfg["flux_url"] or "https://fal.run/fal-ai/flux-pro"
    headers = {
        "Authorization": f"Key {key}",
        "Content-Type": "application/json",
    }
    # También soportar Bearer
    if key.startswith("sk-") or len(key) > 40:
        headers["Authorization"] = f"Bearer {key}"
    payload = {
        "prompt": prompt,
        "image_size": "landscape_16_9",
        "num_inference_steps": 28,
        "guidance_scale": 3.5,
        "enable_safety_checker": True,
        "model": cfg["flux_model"],
        "quality": "ultra",
    }
    try:
        with httpx.Client(timeout=_http_timeout()) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        # Normalizar respuestas comunes
        b64 = None
        img_url = None
        if isinstance(data, dict):
            b64 = data.get("image_base64") or data.get("b64_json")
            images = data.get("images") or data.get("output") or []
            if not b64 and images:
                first = images[0]
                if isinstance(first, str):
                    img_url = first
                elif isinstance(first, dict):
                    img_url = first.get("url")
                    b64 = first.get("b64_json") or first.get("base64")
            img_url = img_url or data.get("url") or data.get("image_url")
        raw: bytes | None = None
        if b64:
            raw = base64.b64decode(b64)
        elif img_url:
            with httpx.Client(timeout=_http_timeout(poll=True)) as client:
                raw = client.get(img_url).content
        if not raw:
            return {"exito": False, "error": "flux_sin_imagen", "raw": str(data)[:300]}
        path = _guardar_bytes(raw, _DIR_GEN, "flux", "png")
        return {
            "exito": True,
            "motor": "flux",
            "modelo": cfg["flux_model"],
            "calidad": "pro_ultra",
            "ruta": str(path),
            "url_relativa": f"/media/generadas/{path.name}",
            "imagen_base64": base64.b64encode(raw).decode("ascii"),
            "mime": "image/png",
        }
    except Exception as exc:
        return {"exito": False, "motor": "flux", "error": f"{type(exc).__name__}: {exc}"}


def _llamar_midjourney(prompt: str, cfg: dict[str, Any]) -> dict[str, Any]:
    key = cfg["midjourney_key"]
    url = cfg["midjourney_url"]
    if not key or not url:
        return {"exito": False, "error": "midjourney_gateway_no_configurado"}
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": f"{prompt} --v 6 --q 2 --style raw",
        "process_mode": "ultra",
        "aspect_ratio": "16:9",
    }
    try:
        with httpx.Client(timeout=_http_timeout()) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        img_url = (
            data.get("image_url")
            or data.get("uri")
            or (data.get("imageUrls") or [None])[0]
        )
        if not img_url:
            return {"exito": False, "error": "mj_sin_url", "raw": str(data)[:300]}
        with httpx.Client(timeout=_http_timeout(poll=True)) as client:
            raw = client.get(img_url).content
        path = _guardar_bytes(raw, _DIR_GEN, "mj", "png")
        return {
            "exito": True,
            "motor": "midjourney",
            "modelo": "midjourney-ultra",
            "calidad": "pro_ultra",
            "ruta": str(path),
            "url_relativa": f"/media/generadas/{path.name}",
            "imagen_base64": base64.b64encode(raw).decode("ascii"),
            "mime": "image/png",
        }
    except Exception as exc:
        return {"exito": False, "motor": "midjourney", "error": f"{type(exc).__name__}: {exc}"}


def _llamar_runway(prompt: str, cfg: dict[str, Any]) -> dict[str, Any]:
    key = cfg["runway_key"]
    if not key:
        return {"exito": False, "error": "runway_api_key_ausente"}
    base = cfg["runway_url"].rstrip("/")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "X-Runway-Version": "2024-11-06",
    }
    payload = {
        "promptText": prompt,
        "model": cfg.get("runway_model") or "gen3a_alpha",
        "duration": 5,
        "ratio": "16:9",
        "watermark": False,
    }
    try:
        with httpx.Client(timeout=_http_timeout()) as client:
            r = client.post(f"{base}/image_to_video", json=payload, headers=headers)
            # Algunos gateways usan /text_to_video
            if r.status_code >= 400:
                r = client.post(f"{base}/text_to_video", json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        task_id = data.get("id") or data.get("task_id")
        video_url = data.get("output") or data.get("video_url")
        if isinstance(video_url, list):
            video_url = video_url[0] if video_url else None
        # Tarea async: devolver id para polling
        if task_id and not video_url:
            return {
                "exito": True,
                "motor": "runway",
                "modelo": payload["model"],
                "calidad": "pro_ultra",
                "estado": "procesando",
                "task_id": task_id,
                "aviso": "Runway Gen-3 en cola; consulta el task_id.",
            }
        if not video_url:
            return {"exito": False, "error": "runway_sin_video", "raw": str(data)[:300]}
        with httpx.Client(timeout=_http_timeout()) as client:
            raw = client.get(video_url).content
        path = _guardar_bytes(raw, _DIR_VID, "runway", "mp4")
        return {
            "exito": True,
            "motor": "runway",
            "modelo": payload["model"],
            "calidad": "pro_ultra",
            "ruta": str(path),
            "url_relativa": f"/media/editados/{path.name}",
            "mime": "video/mp4",
        }
    except Exception as exc:
        return {"exito": False, "motor": "runway", "error": f"{type(exc).__name__}: {exc}"}


def _llamar_kling(prompt: str, cfg: dict[str, Any]) -> dict[str, Any]:
    key = cfg["kling_key"]
    url = cfg["kling_url"]
    if not key or not url:
        return {"exito": False, "error": "kling_gateway_no_configurado"}
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "model_name": cfg["kling_model"],
        "mode": "pro",
        "duration": "5",
        "aspect_ratio": "16:9",
    }
    try:
        with httpx.Client(timeout=_http_timeout()) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        video_url = data.get("video_url") or data.get("url")
        task_id = data.get("task_id") or data.get("id")
        if task_id and not video_url:
            return {
                "exito": True,
                "motor": "kling",
                "modelo": cfg["kling_model"],
                "calidad": "pro_ultra",
                "estado": "procesando",
                "task_id": task_id,
            }
        if not video_url:
            return {"exito": False, "error": "kling_sin_video", "raw": str(data)[:300]}
        with httpx.Client(timeout=_http_timeout()) as client:
            raw = client.get(video_url).content
        path = _guardar_bytes(raw, _DIR_VID, "kling", "mp4")
        return {
            "exito": True,
            "motor": "kling",
            "modelo": cfg["kling_model"],
            "calidad": "pro_ultra",
            "ruta": str(path),
            "url_relativa": f"/media/editados/{path.name}",
            "mime": "video/mp4",
        }
    except Exception as exc:
        return {"exito": False, "motor": "kling", "error": f"{type(exc).__name__}: {exc}"}


def _llamar_krea(prompt: str, imagen_path: str | None, cfg: dict[str, Any]) -> dict[str, Any]:
    key = cfg["krea_key"]
    if not key:
        return {"exito": False, "error": "krea_api_key_ausente"}
    url = (cfg["krea_url"] or "https://api.krea.ai").rstrip("/") + "/v1/enhance"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "prompt": prompt or "enhance textures, ultra detail",
        "mode": "pro",
        "scale": 2,
    }
    if imagen_path and Path(imagen_path).exists():
        payload["image_base64"] = base64.b64encode(
            Path(imagen_path).read_bytes()
        ).decode("ascii")
    try:
        with httpx.Client(timeout=_http_timeout()) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        b64 = data.get("image_base64") or data.get("b64_json")
        img_url = data.get("url")
        raw: bytes | None = None
        if b64:
            raw = base64.b64decode(b64)
        elif img_url:
            with httpx.Client(timeout=_http_timeout(poll=True)) as client:
                raw = client.get(img_url).content
        if not raw:
            return {"exito": False, "error": "krea_sin_salida"}
        path = _guardar_bytes(raw, _DIR_GEN, "krea", "png")
        return {
            "exito": True,
            "motor": "krea",
            "modelo": "krea-upscale-pro",
            "calidad": "pro_ultra",
            "ruta": str(path),
            "url_relativa": f"/media/generadas/{path.name}",
            "imagen_base64": base64.b64encode(raw).decode("ascii"),
            "mime": "image/png",
        }
    except Exception as exc:
        return {"exito": False, "motor": "krea", "error": f"{type(exc).__name__}: {exc}"}


def _postproceso_local(imagen_path: str | None, prompt: str) -> dict[str, Any]:
    try:
        from PIL import Image, ImageEnhance, ImageFilter

        if not imagen_path or not Path(imagen_path).exists():
            from cognicion.media.imagen import _placeholder_local

            return {
                **_placeholder_local(prompt or "refine"),
                "motor": "local_refine",
                "aviso": "Sin imagen de entrada; placeholder.",
            }
        img = Image.open(imagen_path).convert("RGB")
        img = ImageEnhance.Sharpness(img).enhance(1.35)
        img = ImageEnhance.Contrast(img).enhance(1.08)
        img = img.filter(ImageFilter.DETAIL)
        path = _DIR_GEN / f"refine_{uuid.uuid4().hex[:12]}.png"
        img.save(path, format="PNG")
        raw = path.read_bytes()
        return {
            "exito": True,
            "motor": "local_refine",
            "modelo": "pillow_sharpen",
            "calidad": "local",
            "ruta": str(path),
            "url_relativa": f"/media/generadas/{path.name}",
            "imagen_base64": base64.b64encode(raw).decode("ascii"),
            "mime": "image/png",
            "aviso": "Krea no configurado; refinamiento local.",
        }
    except Exception as exc:
        return {"exito": False, "error": type(exc).__name__}


# ── Bridge Colsub ───────────────────────────────────────────────────────────

def bridge_colsub_media(
    prompt: str,
    *,
    hint: str | None = None,
    imagen_entrada: str | None = None,
    forzar_motor: str | None = None,
    mejorar_prompt_flag: bool = True,
) -> dict[str, Any]:
    """
    Bridge: prompt → Prompt Enhancer → Orquestador de routing → motor Pro/Ultra.
    """
    from cognicion.multimodal import ejecutar_con_presupuesto

    def _pipeline() -> dict[str, Any]:
        cfg = _cfg_media()
        tarea = clasificar_tarea(prompt, hint)
        prompt_trabajo = (prompt or "").strip()
        enhancer_meta: dict[str, Any] = {}
        if mejorar_prompt_flag and tarea in {"imagen_hd", "video_gen"}:
            from cognicion.media.prompt_enhancer import mejorar_prompt

            enh = mejorar_prompt(prompt_trabajo, video=(tarea == "video_gen"))
            enhancer_meta = {
                "prompt_enhancer": True,
                "motor_enhancer": enh.get("motor"),
                "prompt_original": enh.get("prompt_original"),
            }
            if enh.get("prompt_mejorado"):
                prompt_trabajo = str(enh["prompt_mejorado"])

        seleccion = seleccionar_motor(tarea, cfg)
        if forzar_motor:
            seleccion["motor"] = forzar_motor.strip().lower()
            seleccion["listo"] = True

        motor = seleccion["motor"]
        resultado: dict[str, Any]

        # Ruta neuronal única: Fal → Replicate (ServiceManager) antes de gateways legacy
        if tarea in {"imagen_hd", "video_gen"} and not forzar_motor:
            try:
                from cognicion.servicios import obtener_manager

                mgr = obtener_manager()
                if mgr.activo("media"):
                    neural = mgr.generar_activo(
                        prompt_trabajo, video=(tarea == "video_gen")
                    )
                    if neural.get("exito"):
                        return {
                            **neural,
                            "tarea": tarea,
                            "calidad": cfg.get("calidad_forzada") or "pro_ultra",
                            **enhancer_meta,
                            "ruta_neuronal": True,
                        }
            except Exception:
                pass

        if tarea == "imagen_hd":
            if motor == "flux":
                resultado = _llamar_flux(prompt_trabajo, cfg)
                if not resultado.get("exito"):
                    alt = _llamar_midjourney(prompt_trabajo, cfg)
                    if alt.get("exito"):
                        resultado = {**alt, "failover_desde": "flux"}
                    else:
                        from cognicion.media.imagen import generar_imagen

                        fb = generar_imagen(prompt_trabajo, quality="hd", estilo_marca=False)
                        resultado = {
                            **fb,
                            "failover_desde": "flux",
                            "calidad": "pro_ultra",
                            "aviso": resultado.get("error") or fb.get("aviso"),
                        }
            elif motor == "midjourney":
                resultado = _llamar_midjourney(prompt_trabajo, cfg)
                if not resultado.get("exito"):
                    alt = _llamar_flux(prompt_trabajo, cfg)
                    resultado = alt if alt.get("exito") else resultado
                    if not resultado.get("exito"):
                        from cognicion.media.imagen import generar_imagen

                        resultado = {
                            **generar_imagen(prompt_trabajo, quality="hd", estilo_marca=False),
                            "failover_desde": "midjourney",
                        }
            else:
                from cognicion.media.imagen import generar_imagen

                resultado = {
                    **generar_imagen(prompt_trabajo, quality="hd", estilo_marca=False),
                    "calidad": "pro_ultra",
                }

        elif tarea == "video_gen":
            if motor == "runway":
                resultado = _llamar_runway(prompt_trabajo, cfg)
                if not resultado.get("exito"):
                    alt = _llamar_kling(prompt_trabajo, cfg)
                    resultado = alt if alt.get("exito") else resultado
            elif motor == "kling":
                resultado = _llamar_kling(prompt_trabajo, cfg)
                if not resultado.get("exito"):
                    alt = _llamar_runway(prompt_trabajo, cfg)
                    resultado = alt if alt.get("exito") else resultado
            else:
                resultado = {
                    "exito": False,
                    "error": "video_pro_no_configurado",
                    "aviso": seleccion.get("aviso"),
                    "motor": motor,
                }

        else:  # postproceso
            if motor == "krea":
                resultado = _llamar_krea(prompt_trabajo, imagen_entrada, cfg)
                if not resultado.get("exito"):
                    resultado = _postproceso_local(imagen_entrada, prompt_trabajo)
            else:
                resultado = _postproceso_local(imagen_entrada, prompt_trabajo)

        if isinstance(resultado, dict):
            resultado["prompt_usado"] = prompt_trabajo

        return {
            "exito": bool(resultado.get("exito")),
            "tarea": tarea,
            "routing": seleccion,
            "resultado": resultado,
            "protocolo": "MULTIMODAL_CORE",
            "hub": "colsub_media",
            "version": "70.0.0",
            **enhancer_meta,
        }

    return ejecutar_con_presupuesto(_pipeline)


def estado_media_routing() -> dict[str, Any]:
    cfg = _cfg_media()
    return {
        "hub": "Colsub Media Engine",
        "calidad_forzada": cfg["calidad_forzada"],
        "forzar_pro": cfg["forzar_pro"],
        "motores": {
            "flux": {"configurado": bool(cfg["flux_key"]), "modelo": cfg["flux_model"]},
            "midjourney": {
                "configurado": bool(cfg["midjourney_key"] and cfg["midjourney_url"]),
                "modelo": "midjourney-ultra",
            },
            "runway": {
                "configurado": bool(cfg["runway_key"]),
                "modelo": cfg["runway_model"],
            },
            "kling": {
                "configurado": bool(cfg["kling_key"] and cfg["kling_url"]),
                "modelo": cfg["kling_model"],
            },
            "krea": {"configurado": bool(cfg["krea_key"]), "modelo": "krea-upscale-pro"},
        },
        "routing_ejemplo": {
            "imagen": seleccionar_motor("imagen_hd", cfg),
            "video": seleccionar_motor("video_gen", cfg),
            "post": seleccionar_motor("postproceso", cfg),
        },
    }
