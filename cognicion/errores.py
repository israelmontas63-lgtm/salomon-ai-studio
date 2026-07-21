# -*- coding: utf-8 -*-
"""
Códigos de error numéricos — Salomón AI (capa cognitiva, no UI).

Rangos:
  20–29  Herramientas / capacidades
  30–39  Memoria / historial de contexto
  40–49  Conexión / API externa del modelo

Uso: clasificar excepciones técnicas → mensaje explícito «Error NN: causa»
sin tumbar el flujo ni mezclar con SalomonVisionArchitecture / UI.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

T = TypeVar("T")

# --- Catálogo canónico (fuente oficial: core.error_codes) --------------------

try:
    from core.error_codes import ERROR_CODES as CODIGOS
except Exception:  # boot parcial / tests sin core
    CODIGOS: dict[int, str] = {
        20: "Fallo de herramienta o capacidad cognitiva",
        25: "Recurso no disponible",
        30: "Fallo de memoria o contexto",
        40: "Fallo del proveedor LLM",
        41: "Fallo de conexión o timeout con el modelo",
        49: "Error desconocido del proveedor",
    }

_DEFAULT_RANGO = {
    "herramienta": 20,
    "memoria": 30,
    "api": 40,
}


@dataclass(frozen=True)
class ErrorSalomon:
    """Error tipado con código numérico y causa legible."""

    codigo: int
    causa: str
    tipo: str = ""
    detalle: str = ""

    @property
    def etiqueta_rango(self) -> str:
        if 20 <= self.codigo <= 29:
            return "herramienta"
        if 30 <= self.codigo <= 39:
            return "memoria"
        if 40 <= self.codigo <= 49:
            return "api"
        return "desconocido"

    def mensaje_usuario(self) -> str:
        return formatear_mensaje(self.codigo, self.causa)

    def to_meta(self) -> dict[str, Any]:
        return {
            "error_codigo": self.codigo,
            "error_causa": self.causa[:240],
            "error_rango": self.etiqueta_rango,
            "error_etiqueta": CODIGOS.get(self.codigo, "Error"),
            "error_tipo": self.tipo or None,
            "fail_soft": True,
        }


class SalomonCodedError(Exception):
    """Excepción con código Salomón (20–49)."""

    def __init__(self, codigo: int, causa: str, *, cause: BaseException | None = None):
        self.codigo = int(codigo)
        self.causa = (causa or CODIGOS.get(self.codigo, "Error")).strip()
        super().__init__(f"Error {self.codigo}: {self.causa}")
        self.__cause__ = cause

    def as_error(self) -> ErrorSalomon:
        return ErrorSalomon(
            codigo=self.codigo,
            causa=self.causa,
            tipo=type(self.__cause__).__name__ if self.__cause__ else "SalomonCodedError",
            detalle=str(self.__cause__ or "")[:240],
        )


def formatear_mensaje(codigo: int, causa: str | None = None) -> str:
    """Formato canónico visible al usuario: «Error NN: causa»."""
    c = int(codigo)
    etiqueta = CODIGOS.get(c, "Error del sistema")
    causa_limpia = (causa or "").strip() or etiqueta
    # Evitar duplicar «Error NN:» si ya viene en la causa
    if causa_limpia.lower().startswith(f"error {c}"):
        return causa_limpia
    return f"Error {c}: {causa_limpia}"


def adjuntar_meta(meta: dict[str, Any] | None, err: ErrorSalomon) -> dict[str, Any]:
    """Inyecta error tipado en metadata de chat (cognicion + raíz)."""
    out = meta if isinstance(meta, dict) else {}
    pack = err.to_meta()
    out.update(pack)
    cog = out.setdefault("cognicion", {})
    if isinstance(cog, dict):
        cog.update(pack)
        cog["llm_error"] = err.tipo or cog.get("llm_error") or f"E{err.codigo}"
    return out


def _texto_exc(exc: BaseException | str | None) -> str:
    if exc is None:
        return ""
    if isinstance(exc, str):
        return exc
    return f"{type(exc).__name__}: {exc}"


def clasificar(
    fuente: BaseException | str | dict | None = None,
    *,
    pista: str | None = None,
) -> ErrorSalomon:
    """
    Mapea excepción / texto / dict técnico → ErrorSalomon (20–49).
    No lanza: siempre devuelve un código en rango.
    """
    if isinstance(fuente, SalomonCodedError):
        return fuente.as_error()

    texto = ""
    tipo = ""
    if isinstance(fuente, dict):
        texto = str(
            fuente.get("error")
            or fuente.get("detalle")
            or fuente.get("detail")
            or fuente.get("mensaje")
            or ""
        )
        tipo = str(fuente.get("tipo") or fuente.get("error") or "")
        if fuente.get("error_codigo"):
            try:
                c = int(fuente["error_codigo"])
                if 20 <= c <= 49:
                    return ErrorSalomon(
                        codigo=c,
                        causa=str(fuente.get("causa") or texto or CODIGOS[c])[:240],
                        tipo=tipo,
                        detalle=texto[:240],
                    )
            except (TypeError, ValueError):
                pass
    elif isinstance(fuente, BaseException):
        tipo = type(fuente).__name__
        texto = str(fuente)
        codigo_attr = getattr(fuente, "codigo", None)
        if isinstance(codigo_attr, int) and 20 <= codigo_attr <= 49:
            return ErrorSalomon(
                codigo=codigo_attr,
                causa=str(getattr(fuente, "causa", None) or texto)[:240],
                tipo=tipo,
                detalle=texto[:240],
            )
    elif isinstance(fuente, str):
        texto = fuente

    blob = f"{pista or ''} {tipo} {texto}".lower()

    # --- 40–49 API / red ---
    if any(
        x in blob
        for x in (
            "api key",
            "api_key",
            "apikey",
            "invalid_api_key",
            "authentication",
            "unauthorized",
            "401",
            "clave",
            "no tiene configurada la clave",
            "gemini_api_key",
            "openai_api_key",
        )
    ):
        return ErrorSalomon(42, _causa_corta(texto, CODIGOS[42]), tipo=tipo, detalle=texto[:240])

    if any(x in blob for x in ("permission", "403", "forbidden", "access denied")):
        return ErrorSalomon(43, _causa_corta(texto, CODIGOS[43]), tipo=tipo, detalle=texto[:240])

    if any(
        x in blob
        for x in (
            "quota",
            "429",
            "rate limit",
            "too many requests",
            "resourceexhausted",
            "resource_exhausted",
        )
    ):
        return ErrorSalomon(44, _causa_corta(texto, CODIGOS[44]), tipo=tipo, detalle=texto[:240])

    if any(
        x in blob
        for x in (
            "model_not_found",
            "does not exist",
            "404",
            "not found",
            "model not found",
            "unknown model",
        )
    ):
        return ErrorSalomon(45, _causa_corta(texto, CODIGOS[45]), tipo=tipo, detalle=texto[:240])

    if any(
        x in blob
        for x in (
            "timeout",
            "timed out",
            "connect",
            "connection",
            "network",
            "unreachable",
            "broken pipe",
            "connection aborted",
            "connection reset",
            "ssl",
            "dns",
        )
    ):
        return ErrorSalomon(41, _causa_corta(texto, CODIGOS[41]), tipo=tipo, detalle=texto[:240])

    if any(x in blob for x in ("503", "service unavailable", "unavailable", "overloaded")):
        return ErrorSalomon(47, _causa_corta(texto, CODIGOS[47]), tipo=tipo, detalle=texto[:240])

    if any(
        x in blob
        for x in (
            "must alternate",
            "multiturn",
            "invalid argument",
            "invalid_request",
            "bad request",
            "400",
            "payload",
            "json",
        )
    ):
        # multiturn/roles → memoria; payload genérico → 48
        if any(
            x in blob
            for x in ("must alternate", "multiturn", "role", "historial", "history")
        ):
            return ErrorSalomon(
                39, _causa_corta(texto, CODIGOS[39]), tipo=tipo, detalle=texto[:240]
            )
        return ErrorSalomon(48, _causa_corta(texto, CODIGOS[48]), tipo=tipo, detalle=texto[:240])

    if any(
        x in blob
        for x in ("empty", "vacío", "vacio", "respuesta vacía", "respondió vacío", "no content")
    ):
        return ErrorSalomon(46, _causa_corta(texto, CODIGOS[46]), tipo=tipo, detalle=texto[:240])

    # --- 30–39 memoria ---
    if any(
        x in blob
        for x in (
            "historial",
            "history",
            "contexto",
            "memoria",
            "session",
            "chromadb",
            "rag",
            "vector",
            "sqlite",
        )
    ):
        if "personal" in blob:
            return ErrorSalomon(
                34, _causa_corta(texto, CODIGOS[34]), tipo=tipo, detalle=texto[:240]
            )
        if any(x in blob for x in ("chroma", "rag", "vector")):
            return ErrorSalomon(
                35, _causa_corta(texto, CODIGOS[35]), tipo=tipo, detalle=texto[:240]
            )
        if any(x in blob for x in ("corrupt", "invalid", "sanitiz")):
            return ErrorSalomon(
                31, _causa_corta(texto, CODIGOS[31]), tipo=tipo, detalle=texto[:240]
            )
        if "persist" in blob or "guardar" in blob:
            return ErrorSalomon(
                33, _causa_corta(texto, CODIGOS[33]), tipo=tipo, detalle=texto[:240]
            )
        return ErrorSalomon(30, _causa_corta(texto, CODIGOS[30]), tipo=tipo, detalle=texto[:240])

    if any(x in blob for x in ("enriquecer", "enrich", "orquest")):
        return ErrorSalomon(36, _causa_corta(texto, CODIGOS[36]), tipo=tipo, detalle=texto[:240])

    # --- 20–29 herramientas ---
    if any(x in blob for x in ("tts", "elevenlabs", "cartesia", "voz")):
        return ErrorSalomon(27, _causa_corta(texto, CODIGOS[27]), tipo=tipo, detalle=texto[:240])
    if any(x in blob for x in ("stt", "whisper", "deepgram", "transcri")):
        return ErrorSalomon(28, _causa_corta(texto, CODIGOS[28]), tipo=tipo, detalle=texto[:240])
    if any(x in blob for x in ("vision", "camera", "captura", "frame", "opencv")):
        return ErrorSalomon(26, _causa_corta(texto, CODIGOS[26]), tipo=tipo, detalle=texto[:240])
    if any(x in blob for x in ("buscar_web", "tavily", "busqueda", "búsqueda", "search")):
        return ErrorSalomon(24, _causa_corta(texto, CODIGOS[24]), tipo=tipo, detalle=texto[:240])
    if any(
        x in blob
        for x in ("flux", "imagen", "image", "replicate", "fal", "runway", "midjourney")
    ):
        return ErrorSalomon(23, _causa_corta(texto, CODIGOS[23]), tipo=tipo, detalle=texto[:240])
    if any(x in blob for x in ("not available", "no disponible", "resource", "recurso")):
        return ErrorSalomon(25, _causa_corta(texto, CODIGOS[25]), tipo=tipo, detalle=texto[:240])
    if any(x in blob for x in ("herramienta no encontrada", "tool not found")):
        return ErrorSalomon(21, _causa_corta(texto, CODIGOS[21]), tipo=tipo, detalle=texto[:240])
    if any(x in blob for x in ("desactivada", "disabled", "tool")):
        return ErrorSalomon(20, _causa_corta(texto, CODIGOS[20]), tipo=tipo, detalle=texto[:240])

    # LLM genérico / SDKs
    if any(
        x in blob
        for x in (
            "gemini",
            "openai",
            "groq",
            "llm",
            "generativelanguage",
            "anthropic",
            "cohere",
            "clienterror",
            "apierror",
            "google.genai",
            "servererror",
            "internal server",
            "cancelled",
            "canceled",
            "aborted",
            "remoteprotocol",
            "httpx",
            "httpcore",
        )
    ):
        if any(x in blob for x in ("cancel", "abort", "timeout", "connect")):
            return ErrorSalomon(41, _causa_corta(texto, CODIGOS[41]), tipo=tipo, detalle=texto[:240])
        return ErrorSalomon(40, _causa_corta(texto, CODIGOS[40]), tipo=tipo, detalle=texto[:240])

    # Pista explícita de rango
    if pista:
        p = pista.lower()
        if p in _DEFAULT_RANGO:
            c = _DEFAULT_RANGO[p]
            return ErrorSalomon(c, _causa_corta(texto, CODIGOS[c]), tipo=tipo, detalle=texto[:240])

    # Último recurso: si hay excepción tipada, tratar como API 40 (no 49 opaco)
    if tipo and tipo not in ("", "str", "NoneType"):
        return ErrorSalomon(
            40,
            _causa_corta(texto or tipo, CODIGOS[40]),
            tipo=tipo,
            detalle=texto[:240],
        )

    return ErrorSalomon(49, _causa_corta(texto, CODIGOS[49]), tipo=tipo, detalle=texto[:240])


def _causa_corta(texto: str, fallback: str, limit: int = 180) -> str:
    t = (texto or "").strip()
    if not t:
        return fallback
    # Quitar prefijos ruidosos de excepciones
    for sep in (": ", " — ", " - "):
        if sep in t and t.split(sep, 1)[0].endswith("Error"):
            t = t.split(sep, 1)[-1].strip()
            break
    t = t.replace("\n", " ").strip()
    if len(t) > limit:
        return t[: limit - 1] + "…"
    return t


def auditar_excepcion(
    exc: BaseException | None = None,
    *,
    origen: str = "chat",
    pista: str | None = None,
    codigo: int | None = None,
    causa: str | None = None,
) -> ErrorSalomon:
    """
    Clasifica el fallo, imprime el stack trace completo en consola del servidor
    y devuelve ErrorSalomon para la respuesta al usuario.
    """
    if codigo is not None and 20 <= int(codigo) <= 49:
        err = ErrorSalomon(
            codigo=int(codigo),
            causa=(causa or CODIGOS[int(codigo)])[:240],
            tipo=type(exc).__name__ if isinstance(exc, BaseException) else "",
            detalle=_texto_exc(exc)[:240],
        )
    else:
        err = clasificar(exc, pista=pista)
        if causa:
            err = ErrorSalomon(
                codigo=err.codigo,
                causa=causa[:240],
                tipo=err.tipo,
                detalle=err.detalle,
            )

    tb = traceback.format_exc()
    if exc is not None and (not tb or tb.strip() == "NoneType: None"):
        tb = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
    tipo_txt = err.tipo or (type(exc).__name__ if exc else "?")
    banner = (
        f"\n{'=' * 72}\n"
        f"[SALOMON ERROR {err.codigo}] origen={origen} rango={err.etiqueta_rango}\n"
        f"causa={err.causa}\n"
        f"tipo={tipo_txt}\n"
        f"{'-' * 72}\n"
        f"{tb.rstrip()}\n"
        f"{'=' * 72}\n"
    )
    print(banner, flush=True)
    try:
        from cognicion.registro import evento, obtener_logger

        evento(
            obtener_logger("cognicion.errores"),
            "error_auditado",
            codigo=err.codigo,
            origen=origen,
            causa=err.causa[:200],
            tipo=err.tipo,
            traceback=tb[-4000:],
        )
    except Exception:
        pass
    return err


def respuesta_error(
    fuente: BaseException | str | dict | None = None,
    *,
    codigo: int | None = None,
    causa: str | None = None,
    pista: str | None = None,
    meta: dict[str, Any] | None = None,
    auditar: bool = True,
    origen: str = "chat",
) -> tuple[str, bool, dict[str, Any]]:
    """
    Empaqueta fallo para el cerebro/chat:
      (texto_usuario, exito=False, metadata_con_codigo)
    Si auditar=True y fuente es excepción, imprime stack trace completo.
    """
    if auditar and isinstance(fuente, BaseException):
        err = auditar_excepcion(
            fuente,
            origen=origen,
            pista=pista,
            codigo=codigo,
            causa=causa,
        )
    elif codigo is not None and 20 <= int(codigo) <= 49:
        err = ErrorSalomon(
            codigo=int(codigo),
            causa=(causa or CODIGOS[int(codigo)])[:240],
            tipo=type(fuente).__name__ if isinstance(fuente, BaseException) else "",
            detalle=_texto_exc(fuente)[:240],
        )
    else:
        err = clasificar(fuente, pista=pista)
        if causa:
            err = ErrorSalomon(
                codigo=err.codigo,
                causa=causa[:240],
                tipo=err.tipo,
                detalle=err.detalle,
            )
    out_meta = adjuntar_meta(meta, err)
    return err.mensaje_usuario(), False, out_meta


def seguro(
    fn: Callable[[], T],
    *,
    fallback: T,
    etiqueta: str = "operacion",
) -> tuple[T, dict[str, Any] | None]:
    """Ejecuta fn; ante excepción devuelve fallback + meta de error (nunca raise)."""
    try:
        return fn(), None
    except Exception as exc:
        err = clasificar(exc, pista=etiqueta)
        return fallback, {
            "etiqueta": etiqueta,
            **err.to_meta(),
            "error": type(exc).__name__,
            "detalle": str(exc)[:240],
            "traceback_tail": traceback.format_exc()[-500:],
        }


def meta_error_api(exc: BaseException, *, codigo: str = "error_interno") -> dict[str, Any]:
    err = clasificar(exc)
    return {
        "ok": False,
        "error": codigo,
        "tipo": type(exc).__name__,
        "detalle": str(exc)[:240],
        **err.to_meta(),
    }
