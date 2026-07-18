# -*- coding: utf-8 -*-
"""Orquestador del Cerebro Ejecutivo — una sola voz hacia Israel."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Literal

from cognicion.ejecutivo.exclusividad import exigir_contexto_israel, sello_propiedad

Modulo = Literal["mercados", "contenido", "oportunidades", "contactos", "completo"]


def estado_ejecutivo() -> dict[str, Any]:
    import os

    return sello_propiedad(
        {
            "modulos": ["mercados", "contenido", "oportunidades", "contactos"],
            "activo": os.getenv("EJECUTIVO_ENABLED", "true").strip().lower()
            in ("1", "true", "yes", "on"),
            "numverify": bool((os.getenv("NUMVERIFY_API_KEY") or "").strip()),
            "metodologia": {
                "paso_1": "SBI-PRO (puerta biométrica)",
                "paso_2": "Integración web / tendencias",
                "paso_3": "Automatización de contenido",
            },
        }
    )


def informe_ejecutivo(
    *,
    modulo: Modulo = "completo",
    consulta: str = "",
    tema: str = "",
    numero: str = "",
    plataforma: str = "shorts",
    actor: str = "Israel Montas",
) -> dict[str, Any]:
    from cognicion.ejecutivo.contactos import identificar_contacto
    from cognicion.ejecutivo.contenido import estratega_contenido
    from cognicion.ejecutivo.mercados import escanear_mercados
    from cognicion.ejecutivo.oportunidades import escanear_oportunidades

    exclusividad = exigir_contexto_israel(actor)
    base = sello_propiedad({"exclusividad_check": exclusividad})
    if not exclusividad.get("ok"):
        return {**base, "ok": False, "error": "exclusividad_denegada"}

    resultados: dict[str, Any] = {}

    def _run(nombre: str, fn) -> None:
        resultados[nombre] = fn()

    tareas: list[tuple[str, Any]] = []
    m = (modulo or "completo").lower()
    if m in ("mercados", "completo"):
        tareas.append(("mercados", lambda: escanear_mercados(consulta)))
    if m in ("contenido", "completo"):
        tareas.append(
            (
                "contenido",
                lambda: estratega_contenido(tema or consulta, plataforma=plataforma),
            )
        )
    if m in ("oportunidades", "completo"):
        tareas.append(("oportunidades", lambda: escanear_oportunidades(consulta=consulta)))
    if m == "contactos" or (m == "completo" and numero.strip()):
        tareas.append(("contactos", lambda: identificar_contacto(numero, contexto=consulta)))

    if not tareas:
        return {**base, "ok": False, "error": "modulo_desconocido", "modulo": modulo}

    # Free Tier: máximo 2 workers
    with ThreadPoolExecutor(max_workers=min(2, len(tareas))) as pool:
        futs = {pool.submit(_run, n, fn): n for n, fn in tareas}
        for fut in as_completed(futs):
            try:
                fut.result()
            except Exception as exc:
                resultados[futs[fut]] = {"ok": False, "error": str(exc)[:200]}

    return {
        **base,
        "ok": True,
        "modulo": m,
        "resultados": resultados,
    }
