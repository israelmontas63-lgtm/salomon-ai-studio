# -*- coding: utf-8 -*-
"""
Agent_Visual — búsqueda y generación visual exclusiva (APIs vía env).
Lazy: importa media/visión solo al ejecutar.
"""

from __future__ import annotations

from typing import Any

from cognicion.agente.guard import liberar_memoria_suave


def ejecutar_visual(
    prompt: str,
    *,
    modo: str = "auto",
) -> dict[str, Any]:
    """
    modo: auto | generar | buscar
    APIs solo por variables de entorno (FLUX_*, OPENAI_*, etc.).
    """
    texto = (prompt or "").strip()
    if not texto:
        return {"exito": False, "agente": "Agent_Visual", "error": "prompt_vacio"}

    modo_l = (modo or "auto").lower()
    try:
        if modo_l == "buscar" or (
            modo_l == "auto"
            and __import__(
                "cognicion.vision.busqueda_visual", fromlist=["es_busqueda_visual"]
            ).es_busqueda_visual(texto)
        ):
            from cognicion.vision.busqueda_visual import recuperar_o_generar

            out = recuperar_o_generar(texto)
            liberar_memoria_suave()
            return {"exito": bool(out.get("exito")), "agente": "Agent_Visual", "modo": "buscar", **out}

        from cognicion.media.media_engine import bridge_colsub_media

        hint = "video_gen" if "video" in texto.lower() else "imagen_hd"
        pack = bridge_colsub_media(texto, hint=hint)
        liberar_memoria_suave()
        return {
            "exito": bool(pack.get("exito")),
            "agente": "Agent_Visual",
            "modo": "generar",
            "pack": pack,
        }
    except Exception as exc:
        liberar_memoria_suave()
        return {
            "exito": False,
            "agente": "Agent_Visual",
            "error": f"{type(exc).__name__}: {exc}",
        }
