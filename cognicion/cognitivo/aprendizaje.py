# -*- coding: utf-8 -*-
"""Ciclo de aprendizaje — incidente → causa raíz → conocimiento."""

from __future__ import annotations

from typing import Any

from cognicion.cognitivo.episodica import FRASE_APRENDIZAJE, guardar_episodio


def registrar_incidente(
    descripcion: str,
    *,
    causa_raiz: str = "",
    session_id: str | None = None,
    correccion_israel: str = "",
) -> dict[str, Any]:
    desc = (descripcion or "").strip()
    causa = (causa_raiz or "").strip() or _inferir_causa(desc, correccion_israel)
    texto = (
        f"Incidente: {desc}\n"
        f"Corrección de Israel: {correccion_israel.strip()[:500]}\n"
        f"{FRASE_APRENDIZAJE}"
    )
    ep = guardar_episodio(
        texto,
        tipo="incidente",
        session_id=session_id,
        causa_raiz=causa,
        meta={"aprendizaje": True},
    )
    return {
        **ep,
        "frase": FRASE_APRENDIZAJE,
        "causa_raiz": causa,
        "mensaje_israel": (
            f"{FRASE_APRENDIZAJE} "
            f"Causa raíz registrada: {causa[:180]}"
        ),
    }


def _inferir_causa(desc: str, correccion: str) -> str:
    blob = f"{desc} {correccion}".lower()
    if "api" in blob or "clave" in blob or "key" in blob:
        return "falla_de_credencial_o_proveedor"
    if "memoria" in blob or "olvido" in blob:
        return "contexto_insuficiente"
    if "camara" in blob or "camera" in blob:
        return "nucleo_protegido_o_permiso"
    if "tono" in blob or "saludo" in blob:
        return "desajuste_de_estilo"
    if correccion.strip():
        return "desvio_respecto_a_instruccion_de_israel"
    return "error_de_proceso_no_especificado"
