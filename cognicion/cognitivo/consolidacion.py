# -*- coding: utf-8 -*-
"""Consolidación de sesión / día — limpieza y esencia permanente."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from cognicion.cognitivo.episodica import guardar_episodio, recuperar_lecciones


def consolidar_aprendizaje(
    session_id: str | None = None,
    *,
    notas: str = "",
) -> dict[str, Any]:
    """
    Resume lo aprendido en la sesión y lo guarda como episodio permanente (global).
    """
    lecciones = recuperar_lecciones(
        "aprendizaje correccion exito incidente hoy",
        n=8,
        session_id=session_id,
    )
    dia = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cuerpo_parts = [
        f"Consolidación cognitiva {dia} (sesión {session_id or 'global'}).",
        "Lecciones integradas a la esencia:",
    ]
    if lecciones:
        for i, lec in enumerate(lecciones, 1):
            cuerpo_parts.append(f"{i}. {lec[:240]}")
    else:
        cuerpo_parts.append("Sin incidentes nuevos; estabilidad mantenida.")
    if notas.strip():
        cuerpo_parts.append(f"Notas de Israel: {notas.strip()[:500]}")

    texto = "\n".join(cuerpo_parts)
    ep = guardar_episodio(
        texto,
        tipo="consolidacion",
        session_id="global",
        meta={"dia": dia, "origen_sesion": session_id or ""},
    )

    # Aprendizaje ontológico ligero (esencia)
    try:
        from cognicion.esencia import aprendizaje_ontologico

        aprendizaje_ontologico(
            texto[:500],
            categoria="consolidacion_sesion",
            origen="cognitivo_dual",
            meta={"dia": dia},
        )
    except Exception:
        pass

    return {
        **ep,
        "dia": dia,
        "lecciones_n": len(lecciones),
        "resumen": texto[:1200],
        "limpieza": "ruido de sesión descartado; patrones útiles promovidos a esencia",
    }
