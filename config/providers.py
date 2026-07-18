# -*- coding: utf-8 -*-
"""
Provider Pattern — selección dinámica de servicios según la tarea.

Cadena oficial (Render):
  LLM        → GEMINI → GROQ → OPENAI
  MEDIA      → FAL → REPLICATE
  STT        → DEEPGRAM
  TTS        → ELEVENLABS (Cartesia como respaldo si existe)
  EMBEDDINGS → COHERE
  SBI        → SBI_ENABLED + SBI_MODE
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Servicio(str, Enum):
    LLM = "llm"
    MEDIA = "media"
    STT = "stt"
    TTS = "tts"
    EMBEDDINGS = "embeddings"
    SBI = "sbi"


@dataclass(frozen=True)
class ProviderSlot:
    """Un eslabón de la cadena de rotación."""

    nombre: str
    env_key: str
    presente: bool
    critico: bool = False


class ProviderConfigError(RuntimeError):
    """Falta una clave crítica de entorno."""


def _presente(valor: str | None) -> bool:
    return bool((valor or "").strip())


def inventario_claves() -> dict[str, str]:
    """Snapshot de claves (nunca expone el secreto completo)."""
    import settings as S

    raw = {
        "GEMINI_API_KEY": S.GEMINI_API_KEY,
        "GROQ_API_KEY": S.GROQ_API_KEY,
        "OPENAI_API_KEY": S.OPENAI_API_KEY,
        "COHERE_API_KEY": S.COHERE_API_KEY,
        "DEEPGRAM_API_KEY": S.DEEPGRAM_API_KEY,
        "ELEVENLABS_API_KEY": S.ELEVENLABS_API_KEY,
        "FAL_KEY": S.FAL_KEY,
        "REPLICATE_API_TOKEN": S.REPLICATE_API_TOKEN,
        "CARTESIA_API_KEY": getattr(S, "CARTESIA_API_KEY", ""),
        "SBI_ENABLED": "true" if S.SBI_ENABLED else "false",
        "SBI_MODE": S.SBI_MODE,
    }
    out: dict[str, str] = {}
    for k, v in raw.items():
        if k.startswith("SBI_"):
            out[k] = str(v)
            continue
        if _presente(v):
            out[k] = f"set:{len(v)}c"
        else:
            out[k] = "missing"
    return out


def cadenas() -> dict[Servicio, list[ProviderSlot]]:
    """Cadenas de prioridad por tarea (Provider Pattern)."""
    import settings as S

    return {
        Servicio.LLM: [
            ProviderSlot("gemini", "GEMINI_API_KEY", _presente(S.GEMINI_API_KEY), True),
            ProviderSlot("groq", "GROQ_API_KEY", _presente(S.GROQ_API_KEY), True),
            ProviderSlot("openai", "OPENAI_API_KEY", _presente(S.OPENAI_API_KEY), True),
        ],
        Servicio.MEDIA: [
            ProviderSlot("fal", "FAL_KEY", _presente(S.FAL_KEY)),
            ProviderSlot(
                "replicate", "REPLICATE_API_TOKEN", _presente(S.REPLICATE_API_TOKEN)
            ),
        ],
        Servicio.STT: [
            ProviderSlot("deepgram", "DEEPGRAM_API_KEY", _presente(S.DEEPGRAM_API_KEY)),
        ],
        Servicio.TTS: [
            ProviderSlot(
                "elevenlabs", "ELEVENLABS_API_KEY", _presente(S.ELEVENLABS_API_KEY)
            ),
            ProviderSlot(
                "cartesia",
                "CARTESIA_API_KEY",
                _presente(getattr(S, "CARTESIA_API_KEY", "")),
            ),
        ],
        Servicio.EMBEDDINGS: [
            ProviderSlot("cohere", "COHERE_API_KEY", _presente(S.COHERE_API_KEY)),
        ],
        Servicio.SBI: [
            ProviderSlot(
                "sbi_pro",
                "SBI_ENABLED",
                bool(S.SBI_ENABLED) and (S.SBI_MODE or "soft") != "off",
            ),
        ],
    }


def seleccionar(servicio: Servicio | str) -> ProviderSlot | None:
    """Primer proveedor disponible de la cadena para la tarea."""
    if isinstance(servicio, str):
        servicio = Servicio(servicio.strip().lower())
    for slot in cadenas().get(servicio, []):
        if slot.presente:
            return slot
    return None


def cadena_nombres(servicio: Servicio | str) -> list[str]:
    """Nombres de proveedores disponibles en orden de prioridad."""
    if isinstance(servicio, str):
        servicio = Servicio(servicio.strip().lower())
    return [s.nombre for s in cadenas().get(servicio, []) if s.presente]


def validar_entorno(*, strict: bool | None = None) -> dict[str, Any]:
    """
    Valida claves críticas.

    Crítico: al menos UNA de GEMINI / GROQ / OPENAI.
    Si strict=True (o PROVIDERS_STRICT), lanza ProviderConfigError.
    """
    import settings as S

    if strict is None:
        strict = bool(getattr(S, "PROVIDERS_STRICT", False))

    llm_ok = any(s.presente for s in cadenas()[Servicio.LLM])
    faltan_opcionales: list[str] = []
    for servicio, slots in cadenas().items():
        if servicio in (Servicio.LLM, Servicio.SBI):
            continue
        if not any(s.presente for s in slots):
            faltan_opcionales.append(servicio.value)

    errores: list[str] = []
    if not llm_ok:
        errores.append(
            "Falta clave LLM crítica: configure GEMINI_API_KEY, GROQ_API_KEY u OPENAI_API_KEY"
        )

    sbi_mode = (S.SBI_MODE or "soft").strip().lower()
    if sbi_mode not in ("off", "soft", "strict"):
        errores.append(f"SBI_MODE inválido '{S.SBI_MODE}' (use off|soft|strict)")

    reporte = {
        "ok": not errores,
        "strict": strict,
        "llm_disponible": llm_ok,
        "activo": {
            s.value: (seleccionar(s).nombre if seleccionar(s) else None)
            for s in Servicio
        },
        "cadenas": {s.value: cadena_nombres(s) for s in Servicio},
        "claves": inventario_claves(),
        "sbi": {
            "enabled": bool(S.SBI_ENABLED),
            "mode": sbi_mode if S.SBI_ENABLED else "off",
            "agents_gated": bool(S.SBI_ENABLED) and sbi_mode == "strict",
        },
        "opcionales_faltantes": faltan_opcionales,
        "errores": errores,
    }

    if errores and strict:
        raise ProviderConfigError("; ".join(errores))
    return reporte


def estado_proveedores() -> dict[str, Any]:
    """Estado público para /api/proveedores y salud."""
    return validar_entorno(strict=False)
