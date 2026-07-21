# -*- coding: utf-8 -*-
"""
Agente de búsqueda web — Tavily (primario) + Wikipedia / DuckDuckGo / noticias.

Failover con backoff exponencial y circuit breaker. Extracción semántica de
consulta, anti-alucinación / anti-cuota en resúmenes, tipado estricto.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import math
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Final

import httpx

from settings import TAVILY_API_KEY

_MARCADORES_LIMITE: Final[tuple[str, ...]] = (
    "límite de uso",
    "limite de uso",
    "límite de cuota",
    "limite de cuota",
    "quota",
    "gemini está en su límite",
    "motor en la nube está en su límite",
    "motor en la nube esta en su limite",
    "servicio de ia en la nube está en límite",
    "intenta de nuevo en unos minutos",
    "inténtalo otra vez en unos minutos",
    "cuando se restablezca la cuota",
    "servicio de gemini",
    "resource exhausted",
    "rate limit",
    "429",
    "too many requests",
    "insufficient_quota",
)

# Prefijos conversacionales → aislar la entidad de búsqueda real
_RE_PREFIJO_BUSQUEDA = re.compile(
    r"(?is)^\s*(?:"
    r"(?:salom[oó]n[,:]?\s*)?"
    r"(?:por\s+favor[,:]?\s*)?"
    r"(?:me\s+puedes\s+|puedes\s+|podr[ií]as\s+)?"
    r"(?:buscar?|search|investiga(?:r)?|encuentra|dame\s+info(?:rmaci[oó]n)?)\s*"
    r"(?:en\s+(?:internet|la\s+web|google|tavily)\s*)?"
    r"(?:sobre|acerca\s+de|de|del|de\s+la|de\s+los|de\s+las)?\s*"
    r"|busca\s+en\s+la\s+web\s+sobre\s+"
    r"|search\s*:\s*"
    r")"
)

_RE_RUIDO_FINAL = re.compile(
    r"(?is)\s*(?:,?\s*)?(?:por\s+favor|gracias|ok|vale|ahora|"
    r"y\s+dime|y\s+expl[ií]came|con\s+detalle)\s*[.!?]*\s*$"
)

_RE_SOLO_PUNTUACION = re.compile(r"^[\W_]+$", re.UNICODE)

_TAVILY_TIMEOUT_S: Final[float] = 8.0
_TAVILY_MAX_RETRIES: Final[int] = 2
_TAVILY_BACKOFF_BASE_S: Final[float] = 0.35


@dataclass(slots=True)
class CircuitBreaker:
    """Circuito de aislamiento por motor — evita martillar APIs caídas."""

    name: str
    failure_threshold: int = 3
    recovery_timeout_s: float = 45.0
    _failures: int = 0
    _opened_at: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def allow(self) -> bool:
        with self._lock:
            if self._failures < self.failure_threshold:
                return True
            if (time.monotonic() - self._opened_at) >= self.recovery_timeout_s:
                # Half-open: permitir un intento de prueba
                return True
            return False

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = 0.0

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._opened_at = time.monotonic()

    def status(self) -> dict[str, Any]:
        with self._lock:
            open_ = self._failures >= self.failure_threshold and (
                (time.monotonic() - self._opened_at) < self.recovery_timeout_s
            )
            return {
                "name": self.name,
                "open": open_,
                "failures": self._failures,
                "recovery_timeout_s": self.recovery_timeout_s,
            }


_breaker_tavily = CircuitBreaker("tavily")
_breaker_respaldo = CircuitBreaker("respaldo", failure_threshold=4, recovery_timeout_s=30.0)


def _finite_float(value: Any, default: float = 0.0) -> float:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(num) or math.isinf(num):
        return default
    return round(num, 3)


def _json_safe(obj: Any) -> Any:
    """Árbol JSON-serializable (PWA / Flask / FastAPI)."""
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        return _finite_float(obj)
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, (bytes, bytearray)):
        return bytes(obj).decode("utf-8", errors="replace")
    return str(obj)


def _texto_util(texto: Any, *, limite: int = 400) -> str:
    t = (texto if isinstance(texto, str) else str(texto or "")).strip()
    if not t or _RE_SOLO_PUNTUACION.match(t):
        return ""
    if respuesta_parece_limite_o_vacia(t):
        return ""
    return t[:limite]


def necesita_busqueda_web(
    mensaje: str,
    *,
    llm_limitado: bool = False,
    respuesta_previa: str | None = None,
    forzar: bool = False,
) -> bool:
    """Web solo vía Memory Cortex (frase canónica o forzar+agente autorizado)."""
    from config.memory_cortex import autoriza_web, es_saludo_o_charla_simple

    _ = (llm_limitado, respuesta_previa)
    if es_saludo_o_charla_simple(mensaje):
        return False
    if forzar:
        return bool(autoriza_web(mensaje, origen="agente"))
    return bool(autoriza_web(mensaje, origen="usuario"))


def respuesta_parece_limite_o_vacia(texto: str) -> bool:
    t = (texto or "").strip().lower()
    if not t:
        return True
    if any(m in t for m in _MARCADORES_LIMITE):
        return True
    if "no tengo información" in t or "no tengo datos" in t:
        return True
    return False


def extraer_consulta(mensaje: str) -> str:
    """
    Aísla la entidad de búsqueda real de comandos conversacionales.
    Ej.: «Busca en la web sobre el clima en Madrid, por favor» → «el clima en Madrid»
    """
    raw = (mensaje or "").strip()
    if not raw:
        return ""

    t = _RE_PREFIJO_BUSQUEDA.sub("", raw).strip()
    t = _RE_RUIDO_FINAL.sub("", t).strip(" .:¿?¡!,;\"'«»")
    # Si quedó vacío tras limpiar, usar mensaje original truncado
    if not t or len(t) < 2:
        t = raw
    # Colapsar espacios
    t = re.sub(r"\s+", " ", t).strip()
    return t[:240]


def _normalizar_resultado(item: dict[str, Any]) -> dict[str, str] | None:
    titulo = _texto_util(item.get("titulo"), limite=160)
    snippet = _texto_util(item.get("snippet"), limite=400)
    url = item.get("url") if isinstance(item.get("url"), str) else ""
    url = (url or "").strip()[:500]
    if not titulo and not snippet:
        return None
    return {
        "titulo": titulo or snippet[:80],
        "url": url,
        "snippet": snippet or titulo,
    }


def _buscar_tavily(consulta: str, max_results: int = 5) -> dict[str, Any] | None:
    if not TAVILY_API_KEY:
        return None
    if not _breaker_tavily.allow():
        return {
            "motor": "tavily",
            "error": "circuit_open",
            "consulta": consulta,
            "circuit": _breaker_tavily.status(),
        }

    last_err = "unknown"
    for attempt in range(_TAVILY_MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=_TAVILY_TIMEOUT_S) as client:
                r = client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": TAVILY_API_KEY,
                        "query": consulta,
                        "search_depth": "basic",
                        "include_answer": True,
                        "max_results": max_results,
                    },
                )
                if r.status_code in (429, 503, 502):
                    last_err = f"http_{r.status_code}"
                    _breaker_tavily.record_failure()
                    if attempt < _TAVILY_MAX_RETRIES:
                        time.sleep(_TAVILY_BACKOFF_BASE_S * (2**attempt))
                        continue
                    return {
                        "motor": "tavily",
                        "error": last_err,
                        "consulta": consulta,
                    }
                r.raise_for_status()
                payload = r.json()
                data = payload if isinstance(payload, dict) else {}

            resultados: list[dict[str, str]] = []
            for item in data.get("results") or []:
                if not isinstance(item, dict):
                    continue
                norm = _normalizar_resultado(
                    {
                        "titulo": item.get("title") or "",
                        "url": item.get("url") or "",
                        "snippet": (item.get("content") or "")[:400],
                    }
                )
                if norm:
                    resultados.append(norm)

            answer = _texto_util(data.get("answer") or "", limite=1200)
            if not answer and not resultados:
                _breaker_tavily.record_failure()
                return {
                    "motor": "tavily",
                    "error": "sin_contenido_util",
                    "consulta": consulta,
                    "resultados": [],
                }

            _breaker_tavily.record_success()
            return {
                "motor": "tavily",
                "consulta": consulta,
                "respuesta_directa": answer,
                "resultados": resultados,
            }
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError) as exc:
            last_err = type(exc).__name__
            _breaker_tavily.record_failure()
            if attempt < _TAVILY_MAX_RETRIES:
                time.sleep(_TAVILY_BACKOFF_BASE_S * (2**attempt))
                continue
            return {"motor": "tavily", "error": last_err, "consulta": consulta}
        except Exception as exc:
            last_err = type(exc).__name__
            _breaker_tavily.record_failure()
            return {"motor": "tavily", "error": last_err, "consulta": consulta}

    return {"motor": "tavily", "error": last_err, "consulta": consulta}


def _buscar_respaldo(consulta: str) -> dict[str, Any]:
    if not _breaker_respaldo.allow():
        return {
            "motor": "respaldo",
            "consulta": consulta,
            "respuesta_directa": "",
            "resultados": [],
            "error": "circuit_open",
            "circuit": _breaker_respaldo.status(),
        }

    from cognicion.conectores import (
        consultar_busqueda_web,
        consultar_noticias,
        consultar_wikipedia,
    )

    resultados: list[dict[str, str]] = []
    respuesta_directa = ""
    motor = "duckduckgo"
    fallos = 0

    # Wikipedia — fail-soft
    try:
        wiki = consultar_wikipedia(consulta)
        if wiki and wiki.contexto and "no encontr" not in (wiki.contexto or "").lower():
            motor = "wikipedia"
            cuerpo = wiki.contexto
            if "Instrucción:" in cuerpo:
                cuerpo = cuerpo.split("Instrucción:")[0].strip()
            lineas = [
                ln
                for ln in cuerpo.splitlines()
                if ln.strip()
                and not ln.strip().startswith("[")
                and not respuesta_parece_limite_o_vacia(ln)
            ]
            respuesta_directa = _texto_util("\n".join(lineas), limite=1500)
            if respuesta_directa:
                norm = _normalizar_resultado(
                    {
                        "titulo": f"Wikipedia: {consulta[:80]}",
                        "url": "",
                        "snippet": respuesta_directa[:400],
                    }
                )
                if norm:
                    resultados.append(norm)
    except Exception:
        fallos += 1

    # DuckDuckGo / búsqueda instantánea
    try:
        busq = consultar_busqueda_web(consulta)
        if (
            busq
            and busq.contexto
            and "sin resumen instantáneo" not in (busq.contexto or "").lower()
        ):
            cuerpo = busq.contexto
            if "Instrucción:" in cuerpo:
                cuerpo = cuerpo.split("Instrucción:")[0].strip()
            cuerpo_util = _texto_util(cuerpo, limite=1500)
            if cuerpo_util:
                if not respuesta_directa:
                    respuesta_directa = cuerpo_util
                    motor = "duckduckgo"
                meta_url = ""
                if isinstance(busq.metadata, dict):
                    meta_url = str(busq.metadata.get("busqueda_fuente") or "")
                norm = _normalizar_resultado(
                    {
                        "titulo": f"Web: {consulta[:60]}",
                        "url": meta_url,
                        "snippet": cuerpo_util[:400],
                    }
                )
                if norm:
                    resultados.append(norm)
    except Exception:
        fallos += 1

    # Noticias
    try:
        noticias = consultar_noticias(consulta, max_items=4)
        if (
            noticias
            and noticias.contexto
            and "sin titulares" not in (noticias.contexto or "").lower()
        ):
            if motor == "duckduckgo":
                motor = "duckduckgo+noticias"
            elif motor == "wikipedia":
                motor = "wikipedia+noticias"
            for linea in (noticias.contexto or "").splitlines():
                if re.match(r"^\d+\.", linea.strip()):
                    frag = _texto_util(linea.strip(), limite=300)
                    if not frag:
                        continue
                    norm = _normalizar_resultado(
                        {"titulo": frag[:160], "url": "", "snippet": frag}
                    )
                    if norm:
                        resultados.append(norm)
    except Exception:
        fallos += 1

    if respuesta_directa or resultados:
        _breaker_respaldo.record_success()
    else:
        _breaker_respaldo.record_failure()

    # Deduplicar snippets casi idénticos
    vistos: set[str] = set()
    limpios: list[dict[str, str]] = []
    for item in resultados:
        clave = re.sub(r"\s+", " ", (item.get("snippet") or "")[:100].lower())
        if clave in vistos:
            continue
        vistos.add(clave)
        limpios.append(item)

    return {
        "motor": motor,
        "consulta": consulta,
        "respuesta_directa": respuesta_directa,
        "resultados": limpios[:6],
        "error": None if (respuesta_directa or limpios) else "sin_resultados",
        "fallos_conectores": fallos,
    }


def buscar_web(consulta: str) -> dict[str, Any]:
    """
    Cascada síncrona: Tavily (reintentos + breaker) → respaldo Wikipedia/DDG/noticias.
    Timeouts cortos para no bloquear el hilo Flask/FastAPI.
    """
    t0 = time.perf_counter()
    q = extraer_consulta(consulta)
    if not q:
        return _json_safe(
            {
                "exito": False,
                "error": "consulta_vacia",
                "consulta": "",
                "resultados": [],
                "respuesta_directa": "",
                "motor": None,
                "elapsed_ms": 0.0,
            }
        )

    tavily = _buscar_tavily(q)
    if tavily and not tavily.get("error") and (
        tavily.get("respuesta_directa") or tavily.get("resultados")
    ):
        pack = {"exito": True, **tavily}
        pack["elapsed_ms"] = _finite_float((time.perf_counter() - t0) * 1000)
        return _json_safe(pack)

    respaldo = _buscar_respaldo(q)
    if tavily and tavily.get("error"):
        respaldo["aviso_tavily"] = tavily["error"]
    respaldo["exito"] = bool(
        respaldo.get("respuesta_directa") or respaldo.get("resultados")
    )
    respaldo["elapsed_ms"] = _finite_float((time.perf_counter() - t0) * 1000)
    return _json_safe(respaldo)


def resumir_estilo_salomon(
    consulta: str,
    datos: dict[str, Any],
    *,
    hechos_personales: str = "",
    intentar_llm: bool = False,
) -> str:
    """Resume hallazgos con tono elegante; bloquea cuotas y fragmentos vacíos."""
    _ = hechos_personales
    q = (consulta or "").strip() or "tu consulta"
    if not isinstance(datos, dict):
        datos = {}

    hallazgos: list[str] = []
    directa = _texto_util(datos.get("respuesta_directa"), limite=1200)
    if directa:
        hallazgos.append(directa)

    for item in datos.get("resultados") or []:
        if not isinstance(item, dict):
            continue
        tit = _texto_util(item.get("titulo"), limite=120)
        sn = _texto_util(item.get("snippet"), limite=280)
        url = item.get("url") if isinstance(item.get("url"), str) else ""
        if not tit and not sn:
            continue
        linea = f"- {tit or 'Fuente'}: {sn}".strip(": ")
        if url and url.startswith("http"):
            linea += f" ({url})"
        if not respuesta_parece_limite_o_vacia(linea):
            hallazgos.append(linea)

    bloque = "\n".join(hallazgos)[:3500]

    if intentar_llm and bloque:
        try:
            from cognicion.llm import generar_texto, llm_disponible

            if llm_disponible():
                prompt = f"""Eres Salomón. Estilo: elegante, claro, negro y oro. Español natural.
NO menciones límites de uso, cuotas ni fallos de API.
NO inventes hechos ausentes en los hallazgos.
Presenta lo encontrado en la web de forma útil y breve.

Consulta del usuario: {q}

Hallazgos:
{bloque}

Estructura:
1) Apertura corta (1 frase)
2) Lo esencial (3–6 frases o bullets cortos)
3) Cierre con una pregunta suave
Sin meta-comentarios."""
                texto = (generar_texto(prompt) or "").strip()
                if texto and not respuesta_parece_limite_o_vacia(texto):
                    return texto
        except Exception:
            pass

    lineas: list[str] = [
        "Consulté fuentes en vivo para darte una respuesta útil.",
        "",
    ]
    if directa:
        lineas.append(directa[:900])
        lineas.append("")
    elif hallazgos:
        lineas.append("Esto es lo más relevante:")
        for item in (datos.get("resultados") or [])[:4]:
            if not isinstance(item, dict):
                continue
            tit = _texto_util(item.get("titulo"), limite=120)
            sn = _texto_util(item.get("snippet"), limite=180)
            if not tit and not sn:
                continue
            lineas.append(f"• {tit or sn[:120]}")
            if tit and sn and sn[:80].lower() not in tit.lower():
                lineas.append(f"  {sn}")
        lineas.append("")
    else:
        lineas.append(
            f"No hallé un resumen sólido para «{q}». "
            "Puedes afinar la pregunta y lo intento de nuevo."
        )
        lineas.append("")

    motor = datos.get("motor")
    if isinstance(motor, str) and motor and datos.get("exito"):
        lineas.append(
            f"Fuente operativa: {motor}. ¿Quieres que profundice en algún punto?"
        )
    else:
        lineas.append("¿Quieres que profundice o reformulemos la búsqueda?")

    texto = "\n".join(lineas).strip()
    if respuesta_parece_limite_o_vacia(texto):
        return (
            f"Israel, la búsqueda sobre «{q}» no devolvió contenido usable. "
            "Reformula en una frase concreta y lo retomo."
        )
    return texto


def responder_con_busqueda(
    mensaje: str,
    *,
    hechos_personales: str = "",
) -> dict[str, Any]:
    """Pipeline completo: buscar → resumir estilo Salomón (JSON limpio)."""
    consulta = extraer_consulta(mensaje)
    datos = buscar_web(mensaje)
    texto = resumir_estilo_salomon(
        consulta,
        datos if isinstance(datos, dict) else {},
        hechos_personales=hechos_personales,
    )
    return _json_safe(
        {
            "exito": bool(isinstance(datos, dict) and datos.get("exito")),
            "texto": texto,
            "consulta": consulta,
            "busqueda": datos if isinstance(datos, dict) else {},
            "motor": (datos.get("motor") if isinstance(datos, dict) else None),
            "circuit_breakers": {
                "tavily": _breaker_tavily.status(),
                "respaldo": _breaker_respaldo.status(),
            },
        }
    )


def estado_circuit_breakers() -> dict[str, Any]:
    return _json_safe(
        {
            "tavily": _breaker_tavily.status(),
            "respaldo": _breaker_respaldo.status(),
        }
    )
