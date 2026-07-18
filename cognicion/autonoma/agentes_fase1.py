# -*- coding: utf-8 -*-
"""
Fase 1 — dos sub-agentes en paralelo:
  • búsqueda  → conocimiento universal (web + Wikipedia/Wikidata)
  • síntesis   → lenguaje natural fluido para Israel
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from cognicion.orquesta.agentes_paralelos import (
    consolidar_hallazgos_texto,
    desplegar_agentes_paralelos,
    sintetizar_orquesta,
)


ProgressFn = Callable[[str, dict[str, Any]], None]


def _emit(on_progress: ProgressFn | None, etapa: str, **extra: Any) -> None:
    if on_progress:
        on_progress(etapa, extra)


def agente_busqueda(
    consulta: str,
    *,
    on_progress: ProgressFn | None = None,
) -> dict[str, Any]:
    """Consulta fuentes universales en paralelo (web + académico)."""
    _emit(on_progress, "buscando", mensaje="Estoy buscando en fuentes abiertas…")
    pack = desplegar_agentes_paralelos(
        consulta,
        agentes=["web", "academico"],
        max_workers=2,
    )
    _emit(
        on_progress,
        "busqueda_lista",
        mensaje="Ya tengo hallazgos. Paso a sintetizar…",
        agentes_ok=pack.get("agentes_ok") or [],
        total_hallazgos=pack.get("total_hallazgos") or 0,
    )
    return pack


def agente_sintesis(
    consulta: str,
    pack_busqueda: dict[str, Any],
    *,
    vision_texto: str = "",
    on_progress: ProgressFn | None = None,
) -> str:
    """Traduce hallazgos (+ visión opcional) a prosa natural."""
    _emit(on_progress, "sintetizando", mensaje="Estoy pensando la respuesta…")
    hechos = ""
    if vision_texto:
        hechos = f"[Lo que vi]\n{vision_texto[:1800]}"
    texto = sintetizar_orquesta(
        consulta,
        pack_busqueda,
        hechos_personales=hechos,
        intentar_llm=True,
    )
    if vision_texto and "Lo que vi" not in texto and vision_texto.strip():
        texto = (
            f"Israel, miré la imagen y esto es lo esencial:\n{vision_texto[:900]}\n\n"
            f"{texto}"
        )
    _emit(on_progress, "sintesis_lista", mensaje="Síntesis lista.")
    return texto


def correr_busqueda_y_sintesis_paralelo(
    consulta: str,
    *,
    vision_texto: str = "",
    on_progress: ProgressFn | None = None,
) -> dict[str, Any]:
    """
    Orquestación Fase 1:
    - Lanza búsqueda de inmediato.
    - Mientras llega, emite estados en vivo.
    - Síntesis arranca en cuanto hay pack (pipeline corto, 2 agentes).
    """
    _emit(on_progress, "pensando", mensaje="Estoy pensando…")

    pack: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(agente_busqueda, consulta, on_progress=on_progress)
        # Estado paralelo visible mientras el worker corre
        _emit(
            on_progress,
            "paralelo",
            mensaje="Búsqueda en marcha; preparo la síntesis…",
        )
        pack = fut.result()

    texto = agente_sintesis(
        consulta,
        pack,
        vision_texto=vision_texto,
        on_progress=on_progress,
    )
    cuerpo = consolidar_hallazgos_texto(pack)
    return {
        "texto": texto,
        "pack_busqueda": pack,
        "hallazgos_texto": cuerpo,
        "agentes": ["busqueda", "sintesis"],
        "fase": "1",
    }
