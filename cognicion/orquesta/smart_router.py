# -*- coding: utf-8 -*-
"""
Smart Router — orquestación total + failover de APIs (Salomón AI).

Capa centralizada: mapea cada API key a su motor y rota sin tumbar la app.
  LLM   → gemini → deepseek → openrouter → cerebras → mistral → groq → openai → local
  MEDIA → fal → replicate → openai (DALL·E)
  TTS   → elevenlabs → cartesia
  STT   → deepgram
  WEB   → tavily → exa → respaldo
  EMBED → cohere
"""

from __future__ import annotations

from typing import Any

from cognicion.registro import evento, obtener_logger

_log = obtener_logger("orquesta.smart_router")
_VERSION = "1.0.0"


def _flag(*names: str) -> bool:
    import os

    for n in names:
        if (os.getenv(n) or "").strip():
            return True
    try:
        import settings as S

        for n in names:
            if (getattr(S, n, "") or "").strip():
                return True
    except Exception:
        pass
    return False


def mapa_claves() -> dict[str, dict[str, Any]]:
    """Inventario seguro: presencia + motor destino (nunca el secreto)."""
    import os

    import settings as S

    def _len(name: str, attr: str | None = None) -> int:
        v = (os.getenv(name) or "").strip()
        if not v and attr:
            v = (getattr(S, attr, "") or "").strip()
        return len(v)

    return {
        "GEMINI_API_KEY": {"motor": "llm.gemini", "set": _len("GEMINI_API_KEY", "GEMINI_API_KEY") > 0},
        "DEEPSEEK_API_KEY": {"motor": "llm.deepseek", "set": _len("DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY") > 0},
        "OPENROUTER_API_KEY": {
            "motor": "llm.openrouter",
            "set": _len("OPENROUTER_API_KEY", "OPENROUTER_API_KEY") > 0,
        },
        "CEREBRAS_API_KEY": {
            "motor": "llm.cerebras",
            "set": _len("CEREBRAS_API_KEY", "CEREBRAS_API_KEY") > 0,
        },
        "MISTRAL_API_KEY": {
            "motor": "llm.mistral",
            "set": _len("MISTRAL_API_KEY", "MISTRAL_API_KEY") > 0,
        },
        "GROQ_API_KEY": {"motor": "llm.groq", "set": _len("GROQ_API_KEY", "GROQ_API_KEY") > 0},
        "OPENAI_API_KEY": {
            "motor": "llm.openai+media.dalle",
            "set": _len("OPENAI_API_KEY", "OPENAI_API_KEY") > 0,
        },
        "COHERE_API_KEY": {
            "motor": "embeddings.cohere",
            "set": _len("COHERE_API_KEY", "COHERE_API_KEY") > 0,
        },
        "TAVILY_API_KEY": {"motor": "web.tavily", "set": _len("TAVILY_API_KEY", "TAVILY_API_KEY") > 0},
        "EXA_API_KEY": {"motor": "web.exa", "set": _len("EXA_API_KEY", "EXA_API_KEY") > 0},
        "ELEVENLABS_API_KEY": {
            "motor": "tts.elevenlabs",
            "set": _len("ELEVENLABS_API_KEY", "ELEVENLABS_API_KEY") > 0,
        },
        "CARTESIA_API_KEY": {
            "motor": "tts.cartesia",
            "set": _len("CARTESIA_API_KEY", "CARTESIA_API_KEY") > 0,
        },
        "DEEPGRAM_API_KEY": {
            "motor": "stt.deepgram",
            "set": _len("DEEPGRAM_API_KEY", "DEEPGRAM_API_KEY") > 0,
        },
        "FAL_KEY": {"motor": "media.fal", "set": _len("FAL_KEY", "FAL_KEY") > 0},
        "REPLICATE_API_TOKEN": {
            "motor": "media.replicate",
            "set": _len("REPLICATE_API_TOKEN", "REPLICATE_API_TOKEN") > 0
            or _len("REPLICATE_API_KEY") > 0,
        },
    }


def cadenas_failover() -> dict[str, list[str]]:
    """Orden de respaldo por capacidad (solo nombres lógicos)."""
    return {
        "llm_chat": [
            "gemini",
            "deepseek",
            "openrouter",
            "cerebras",
            "mistral",
            "groq",
            "openai",
            "local",
        ],
        "llm_razonamiento": [
            "deepseek",
            "openrouter",
            "cerebras",
            "mistral",
            "gemini",
            "groq",
            "openai",
            "local",
        ],
        "llm_rapido": ["groq", "cerebras", "gemini", "mistral", "openrouter", "openai", "local"],
        "llm_vision": ["gemini", "openai", "local"],
        "media_imagen": ["fal", "replicate", "openai"],
        "media_video": ["fal", "replicate"],
        "tts": ["elevenlabs", "cartesia"],
        "stt": ["deepgram"],
        "web": ["tavily", "exa", "respaldo"],
        "embeddings": ["cohere"],
    }


def elegir_cadena(tarea: str | None = None) -> list[str]:
    """Selecciona cadena LLM según complejidad / tipo de tarea."""
    t = (tarea or "chat").strip().lower()
    cadenas = cadenas_failover()
    if t in ("razonamiento", "tecnico", "codigo", "code", "debug", "investigacion"):
        return list(cadenas["llm_razonamiento"])
    if t in ("rapido", "fast", "latencia"):
        return list(cadenas["llm_rapido"])
    if t in ("vision", "imagen_analisis", "multimodal"):
        return list(cadenas["llm_vision"])
    return list(cadenas["llm_chat"])


def cadena_disponible(capacidad: str) -> list[str]:
    """Filtra eslabones con key presente (pausa inteligente de los ausentes)."""
    orden = cadenas_failover().get(capacidad) or elegir_cadena(capacidad)
    vivos: list[str] = []
    checks = {
        "gemini": lambda: _flag("GEMINI_API_KEY"),
        "deepseek": lambda: _flag("DEEPSEEK_API_KEY"),
        "openrouter": lambda: _flag("OPENROUTER_API_KEY"),
        "cerebras": lambda: _flag("CEREBRAS_API_KEY"),
        "mistral": lambda: _flag("MISTRAL_API_KEY"),
        "groq": lambda: _flag("GROQ_API_KEY"),
        "openai": lambda: _flag("OPENAI_API_KEY"),
        "local": lambda: True,
        "fal": lambda: _flag("FAL_KEY"),
        "replicate": lambda: _flag("REPLICATE_API_TOKEN", "REPLICATE_API_KEY"),
        "elevenlabs": lambda: _flag("ELEVENLABS_API_KEY"),
        "cartesia": lambda: _flag("CARTESIA_API_KEY"),
        "deepgram": lambda: _flag("DEEPGRAM_API_KEY"),
        "tavily": lambda: _flag("TAVILY_API_KEY"),
        "exa": lambda: _flag("EXA_API_KEY"),
        "respaldo": lambda: True,
        "cohere": lambda: _flag("COHERE_API_KEY"),
    }
    for nombre in orden:
        fn = checks.get(nombre)
        if fn and fn():
            vivos.append(nombre)
    return vivos


def razonar_con_failover(
    mensaje: str,
    historial: list[dict] | None = None,
    system_instruction: str = "",
    *,
    tarea: str = "chat",
) -> dict[str, Any]:
    """LLM con cascada Smart Router (nunca propaga fallo si hay local)."""
    from cognicion.llm import chat_con_historial, ultimo_uso_llm

    cadena = cadena_disponible(
        "llm_razonamiento"
        if tarea in ("razonamiento", "codigo", "tecnico", "debug")
        else "llm_rapido"
        if tarea in ("rapido", "fast")
        else "llm_vision"
        if tarea == "vision"
        else "llm_chat"
    )
    preferir = cadena[0] if cadena else None
    try:
        texto = chat_con_historial(
            mensaje,
            historial or [],
            system_instruction or "Eres Salomón AI.",
            preferir=preferir,
        )
        uso = ultimo_uso_llm()
        evento(
            _log,
            "smart_router_llm_ok",
            preferir=preferir,
            proveedor=uso.get("proveedor"),
            tarea=tarea,
        )
        return {
            "ok": True,
            "texto": texto,
            "preferir": preferir,
            "cadena": cadena,
            "uso": uso,
        }
    except Exception as exc:
        evento(_log, "smart_router_llm_fail", error=type(exc).__name__, preferir=preferir)
        return {
            "ok": False,
            "texto": (
                "Israel, estoy recalibrando el motor de razonamiento. "
                "Reintenta en un momento."
            ),
            "error": type(exc).__name__,
            "cadena": cadena,
            "preferir": preferir,
        }


def generar_imagen_con_failover(prompt: str) -> dict[str, Any]:
    """
    Imagen obligatoria con failover: Fal → Replicate → OpenAI DALL·E.
    Nunca responde 'no puedo' si hay al menos un motor con key.
    """
    p = (prompt or "").strip()
    if not p:
        return {"exito": False, "error": "prompt_vacio"}

    errores: list[str] = []
    cadena = cadena_disponible("media_imagen")
    if not cadena:
        return {
            "exito": False,
            "error": "sin_motores_media",
            "aviso": "Configura FAL_KEY / REPLICATE_API_KEY / OPENAI_API_KEY",
        }

    # 1) Ruta neuronal canónica (Fal → Replicate)
    if any(m in cadena for m in ("fal", "replicate")):
        try:
            from cognicion.servicios import obtener_manager

            pack = obtener_manager().generar_activo(p, video=False)
            if pack.get("exito") and (
                pack.get("url_relativa") or pack.get("imagen_base64") or pack.get("url")
            ):
                evento(_log, "smart_router_media_ok", motor=pack.get("motor"), via="manager")
                return {**pack, "cadena": cadena, "via": "smart_router"}
            if pack.get("error"):
                errores.append(f"manager:{pack.get('error')}")
        except Exception as exc:
            errores.append(f"manager:{type(exc).__name__}")

    # 2) Bridge Colsub (Flux alias FAL + MJ + DALL·E)
    try:
        from cognicion.media.media_engine import bridge_colsub_media

        pack = bridge_colsub_media(p, hint="imagen_hd")
        res = pack.get("resultado") if isinstance(pack.get("resultado"), dict) else {}
        if not res and pack.get("exito") and (
            pack.get("url_relativa") or pack.get("imagen_base64") or pack.get("url")
        ):
            res = dict(pack)
        if pack.get("exito") or res.get("exito") or res.get("imagen_base64") or res.get(
            "url_relativa"
        ):
            out = res or pack
            evento(
                _log,
                "smart_router_media_ok",
                motor=out.get("motor"),
                via="bridge_colsub",
            )
            return {
                "exito": True,
                **{k: v for k, v in out.items() if k != "exito"},
                "cadena": cadena,
                "via": "smart_router.bridge",
            }
        if pack.get("error") or res.get("error"):
            errores.append(f"bridge:{pack.get('error') or res.get('error')}")
    except Exception as exc:
        errores.append(f"bridge:{type(exc).__name__}")

    # 3) OpenAI DALL·E directo
    if "openai" in cadena:
        try:
            from cognicion.media.imagen import generar_imagen

            dalle = generar_imagen(p, usar_manager=False)
            if dalle.get("exito") or dalle.get("imagen_base64") or dalle.get("url"):
                evento(_log, "smart_router_media_ok", motor="openai", via="dalle")
                return {
                    "exito": True,
                    **dalle,
                    "motor": dalle.get("motor") or "openai",
                    "cadena": cadena,
                    "via": "smart_router.dalle",
                }
            errores.append(f"dalle:{dalle.get('error') or 'fail'}")
        except Exception as exc:
            errores.append(f"dalle:{type(exc).__name__}")

    return {
        "exito": False,
        "error": "media_failover_agotado",
        "detalle": errores[:6],
        "cadena": cadena,
        "aviso": "Todos los motores de imagen fallaron; reintenta en unos segundos.",
    }


def generar_video_con_failover(prompt: str, *, duracion_s: int = 20) -> dict[str, Any]:
    """Video 15–30s vía Fal (failover transparente)."""
    p = (prompt or "").strip()
    if not p:
        return {"exito": False, "error": "prompt_vacio"}
    cadena = cadena_disponible("media_video")
    if not cadena:
        return {
            "exito": False,
            "error": "sin_motores_video",
            "aviso": "Configura FAL_KEY para video HD",
        }
    try:
        from cognicion.servicios import obtener_manager

        pack = obtener_manager().generar_activo(p, video=True, duracion_s=duracion_s)
        if pack.get("exito"):
            evento(_log, "smart_router_video_ok", motor=pack.get("motor"))
            return {**pack, "cadena": cadena, "via": "smart_router.video"}
        return {**pack, "cadena": cadena, "via": "smart_router.video"}
    except Exception as exc:
        return {
            "exito": False,
            "error": type(exc).__name__,
            "cadena": cadena,
        }


def hablar_con_failover(texto: str) -> Any:
    """TTS con failover ElevenLabs → Cartesia."""
    from cognicion.servicios import obtener_manager

    return obtener_manager().hablar(texto)


def estado_smart_router() -> dict[str, Any]:
    """Diagnóstico público sin secretos."""
    claves = mapa_claves()
    huerfanas = [k for k, v in claves.items() if not v.get("set")]
    return {
        "ok": True,
        "version": _VERSION,
        "protocol": "SMART_ROUTER_FAILOVER",
        "claves": {
            k: ("set" if v.get("set") else "missing") for k, v in claves.items()
        },
        "motores": {k: v.get("motor") for k, v in claves.items()},
        "cadenas": {cap: cadena_disponible(cap) for cap in cadenas_failover()},
        "huerfanas": huerfanas,
        "media_listo": bool(cadena_disponible("media_imagen")),
        "llm_listo": bool(
            [x for x in cadena_disponible("llm_chat") if x != "local"]
            or cadena_disponible("llm_chat")
        ),
        "tts_listo": bool(cadena_disponible("tts")),
        "web_listo": bool(cadena_disponible("web")),
    }
