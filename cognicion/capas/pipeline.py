# -*- coding: utf-8 -*-
"""
Pipeline de respuesta — extensión por Protocol + fallback LLM.

Iteración fail-soft sobre manejadores registrados (snapshot thread-safe),
trazabilidad de latencia por capa y tipado estricto.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from cognicion.llm import chat_con_historial

_registry_lock = threading.RLock()


@dataclass(slots=True)
class ResultadoPipeline:
    texto: str
    metadata: dict[str, Any] = field(default_factory=dict)
    capa: str = "llm"

    def to_dict(self) -> dict[str, Any]:
        return {
            "texto": self.texto,
            "metadata": dict(self.metadata or {}),
            "capa": self.capa,
        }


@runtime_checkable
class ManejadorRespuesta(Protocol):
    def __call__(
        self,
        mensaje: str,
        historial: list[dict],
        system_instruction: str,
        *,
        model_name: str | None = None,
        contexto: dict[str, Any] | None = None,
    ) -> ResultadoPipeline | None: ...


# Lista ordenada: (prioridad ascendente, nombre, manejador)
_manejadores: list[tuple[int, str, ManejadorRespuesta]] = []


def registrar_manejador(
    nombre: str,
    manejador: ManejadorRespuesta,
    *,
    prioridad: int = 100,
) -> None:
    """Registra o reemplaza un manejador por nombre (hot-plug seguro)."""
    if not nombre or not callable(manejador):
        return
    pri = int(prioridad)
    with _registry_lock:
        _manejadores[:] = [m for m in _manejadores if m[1] != nombre]
        _manejadores.append((pri, nombre, manejador))
        _manejadores.sort(key=lambda item: (item[0], item[1]))


def desregistrar_manejador(nombre: str) -> bool:
    with _registry_lock:
        before = len(_manejadores)
        _manejadores[:] = [m for m in _manejadores if m[1] != nombre]
        return len(_manejadores) < before


def listar_manejadores() -> list[str]:
    with _registry_lock:
        return [nombre for _, nombre, _ in _manejadores]


def _snapshot_manejadores() -> list[tuple[int, str, ManejadorRespuesta]]:
    with _registry_lock:
        return list(_manejadores)


def generar_respuesta(
    mensaje: str,
    historial: list[dict],
    system_instruction: str,
    *,
    model_name: str | None = None,
    contexto: dict[str, Any] | None = None,
) -> ResultadoPipeline:
    """
    Intenta manejadores registrados por plugins; fallback al LLM estándar.
    Fail-soft: un manejador roto no bloquea el hilo ni el resto del pipeline.
    """
    ctx: dict[str, Any] = dict(contexto or {})
    latencias: list[dict[str, Any]] = []
    errores: list[dict[str, str]] = list(ctx.get("errores_capas") or [])

    # Snapshot: hot-plug concurrente no altera la iteración en curso
    handlers = _snapshot_manejadores()

    for _pri, nombre, manejador in handlers:
        t0 = time.perf_counter()
        try:
            resultado = manejador(
                mensaje,
                historial,
                system_instruction,
                model_name=model_name,
                contexto=ctx,
            )
            ms = round((time.perf_counter() - t0) * 1000, 2)
            latencias.append({"capa": nombre, "ms": ms, "hit": bool(resultado and resultado.texto)})
            if resultado is not None and (resultado.texto or "").strip():
                meta = dict(resultado.metadata or {})
                meta.setdefault("capa", nombre)
                meta["latencias_capas"] = latencias
                if errores:
                    meta["errores_capas"] = errores
                return ResultadoPipeline(
                    texto=resultado.texto,
                    metadata=meta,
                    capa=resultado.capa or nombre,
                )
        except Exception as exc:
            ms = round((time.perf_counter() - t0) * 1000, 2)
            latencias.append({"capa": nombre, "ms": ms, "hit": False, "error": type(exc).__name__})
            errores.append({nombre: type(exc).__name__})
            # No re-raise — fail-soft hacia el siguiente manejador / LLM

    t_llm = time.perf_counter()
    try:
        texto = chat_con_historial(
            mensaje,
            historial,
            system_instruction,
            model_name=model_name,
        )
    except Exception as exc:
        errores.append({"llm": type(exc).__name__})
        texto = (
            "Israel, el núcleo de respuesta no pudo completar este turno. "
            "Reintenta en un momento."
        )
    latencias.append(
        {
            "capa": "llm",
            "ms": round((time.perf_counter() - t_llm) * 1000, 2),
            "hit": bool((texto or "").strip()),
        }
    )

    meta_fb: dict[str, Any] = {
        "fallback": True,
        "latencias_capas": latencias,
    }
    if errores:
        meta_fb["errores_capas"] = errores
        ctx["errores_capas"] = errores

    return ResultadoPipeline(
        texto=texto or "",
        capa="llm",
        metadata=meta_fb,
    )
