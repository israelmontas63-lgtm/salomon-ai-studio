# -*- coding: utf-8 -*-
"""
Diccionario oficial de códigos de error — Salomón AI (kernel /core).

Rangos:
  20–29  Herramientas / capacidades
  30–39  Memoria / historial de contexto
  40–49  Conexión / API externa del modelo (p. ej. Error 49)

API pública:
  · get_error_info(code) → {code, message, range, label}
  · format_error_response(exc|code, ...) → estructura estándar para ChatResponse
  · classify_exception(exc) → código numérico
"""

from __future__ import annotations

import traceback
from typing import Any

ERROR_CODES: dict[int, str] = {
    # 20–29 herramientas / capacidades
    20: "Fallo de herramienta o capacidad cognitiva",
    21: "Herramienta no encontrada",
    22: "Herramienta desactivada",
    23: "Fallo de media o generación",
    24: "Fallo de búsqueda web",
    25: "Recurso no disponible",
    26: "Fallo de visión o captura",
    27: "Fallo de síntesis de voz (TTS)",
    28: "Fallo de reconocimiento de voz (STT)",
    29: "Fallo de agente o autonomía",
    # 30–39 memoria / historial
    30: "Fallo de memoria o contexto",
    31: "Historial de chat inválido o corrupto",
    32: "Historial vacío o fuera de límite",
    33: "Fallo al persistir la sesión",
    34: "Fallo de memoria personal",
    35: "Fallo de memoria vectorial / RAG",
    36: "Fallo al enriquecer el mensaje",
    37: "Contexto truncado por límite de tokens",
    38: "Sesión de memoria no encontrada",
    39: "Inconsistencia de roles en el historial",
    # 40–49 API / conexión
    40: "Fallo del proveedor LLM",
    41: "Fallo de conexión o timeout con el modelo",
    42: "Clave de API ausente o inválida",
    43: "Permiso denegado por el proveedor (403)",
    44: "Cuota o límite de uso alcanzado (429)",
    45: "Modelo no encontrado o no disponible",
    46: "Respuesta vacía o inválida del modelo",
    47: "Proveedor temporalmente no disponible (503)",
    48: "Payload o formato de solicitud rechazado",
    49: "Error desconocido del proveedor",
}

_RANGE_LABEL = {
    "herramienta": (20, 29),
    "memoria": (30, 39),
    "api": (40, 49),
}


def _range_for(code: int) -> str:
    if 20 <= code <= 29:
        return "herramienta"
    if 30 <= code <= 39:
        return "memoria"
    if 40 <= code <= 49:
        return "api"
    return "desconocido"


def get_error_info(code: int | str) -> dict[str, Any]:
    """Devuelve la ficha oficial del código (20–49)."""
    try:
        c = int(code)
    except (TypeError, ValueError):
        c = 49
    if c not in ERROR_CODES:
        c = 49
    return {
        "code": c,
        "message": ERROR_CODES[c],
        "range": _range_for(c),
        "label": f"Error {c}",
        "ok": False,
    }


def classify_exception(
    exc: BaseException | str | None = None,
    *,
    hint: str | None = None,
) -> int:
    """
    Evalúa la excepción y devuelve el código numérico oficial.
    Preferencia: cognicion.errores.clasificar (misma taxonomía).
    """
    try:
        from cognicion.errores import clasificar

        return int(clasificar(exc, pista=hint).codigo)
    except Exception:
        blob = f"{hint or ''} {type(exc).__name__ if isinstance(exc, BaseException) else ''} {exc or ''}".lower()
        if any(x in blob for x in ("api key", "401", "unauthorized", "clave")):
            return 42
        if any(x in blob for x in ("403", "permission", "forbidden")):
            return 43
        if any(x in blob for x in ("429", "quota", "rate limit")):
            return 44
        if any(x in blob for x in ("timeout", "connect", "aborted", "network")):
            return 41
        if any(x in blob for x in ("404", "not found", "model")):
            return 45
        if any(x in blob for x in ("503", "unavailable", "overloaded")):
            return 47
        if hint in _RANGE_LABEL:
            return _RANGE_LABEL[hint][0]
        return 49


def format_error_response(
    source: BaseException | int | str | None = None,
    *,
    code: int | None = None,
    cause: str | None = None,
    hint: str | None = None,
    origin: str = "chat",
    audit: bool = True,
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Estructura estandarizada para respuestas de Salomón (ChatResponse / metadata).

    {
      "texto": "Error NN: causa",
      "exito": False,
      "error_codigo": NN,
      "error_causa": "...",
      "error_rango": "api|memoria|herramienta",
      "error_etiqueta": "...",
      "fail_soft": True,
      "origin": "...",
      ...
    }
    """
    exc: BaseException | None = source if isinstance(source, BaseException) else None
    numeric: int | None = None
    if code is not None:
        try:
            numeric = int(code)
        except (TypeError, ValueError):
            numeric = None
    elif isinstance(source, int):
        numeric = source
    elif isinstance(source, str) and source.strip().isdigit():
        numeric = int(source.strip())

    if numeric is None or not (20 <= numeric <= 49):
        numeric = classify_exception(exc if exc is not None else source, hint=hint)

    info = get_error_info(numeric)
    causa = (cause or "").strip()
    if not causa and exc is not None:
        causa = str(exc).strip()[:240]
    if not causa:
        causa = str(info["message"])

    texto = f"Error {numeric}: {causa}"
    if causa.lower().startswith(f"error {numeric}"):
        texto = causa

    if audit and exc is not None:
        try:
            from cognicion.errores import auditar_excepcion

            auditar_excepcion(
                exc,
                origen=origin,
                pista=hint or info["range"],
                codigo=numeric,
                causa=causa,
            )
        except Exception:
            tb = traceback.format_exc()
            print(
                f"\n[SALOMON ERROR {numeric}] origin={origin}\n{tb}\n",
                flush=True,
            )

    pack: dict[str, Any] = {
        "texto": texto,
        "exito": False,
        "ok": False,
        "error_codigo": numeric,
        "error_causa": causa[:240],
        "error_rango": info["range"],
        "error_etiqueta": info["message"],
        "error_tipo": type(exc).__name__ if exc else None,
        "fail_soft": True,
        "origin": origin,
        "error": type(exc).__name__ if exc else f"E{numeric}",
        "detail": (str(exc) if exc else causa)[:240],
    }
    if extra_meta:
        pack.update(extra_meta)
    # Espejo bajo cognicion (compatibilidad frontend / cerebro)
    pack["cognicion"] = {
        "error_codigo": numeric,
        "error_causa": causa[:240],
        "error_rango": info["range"],
        "llm_error": pack.get("error_tipo") or pack.get("error"),
        "fail_soft": True,
    }
    return pack


def exception_from_provider(
    exc: BaseException,
    *,
    provider: str = "llm",
    origin: str = "cognicion.llm",
) -> dict[str, Any]:
    """Atajo para conectores LLM: clasifica + formatea + audita."""
    return format_error_response(
        exc,
        hint="api",
        origin=f"{origin}.{provider}",
        audit=True,
        extra_meta={"provider": provider},
    )
