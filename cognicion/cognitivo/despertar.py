# -*- coding: utf-8 -*-
"""Orquestación del Despertar — ciclo pre-tarea + registro episódico."""

from __future__ import annotations

from typing import Any

from cognicion.cognitivo.aprendizaje import registrar_incidente
from cognicion.cognitivo.claridad import filtrar_claridad
from cognicion.cognitivo.consolidacion import consolidar_aprendizaje
from cognicion.cognitivo.episodica import (
    FRASE_APRENDIZAJE,
    es_correccion_usuario,
    guardar_episodio,
    recuperar_lecciones,
)
from cognicion.cognitivo.razonamiento_critico import evaluar_pre_tarea

PROTOCOLO = "CEREBRO_COGNITIVO_DUAL"
VERSION = "1.0.0"


def estado_cognitivo_dual() -> dict[str, Any]:
    from cognicion.memoria.vectorial import obtener_memoria

    mem = obtener_memoria()
    return {
        "protocolo": PROTOCOLO,
        "version": VERSION,
        "capas": {
            "cognitiva": ["claridad", "razonamiento_critico"],
            "memoria": ["episodica", "consolidacion"],
        },
        "frase_aprendizaje": FRASE_APRENDIZAJE,
        "memoria_motor": getattr(mem, "motor", "unknown"),
        "memoria_activa": bool(getattr(mem, "activa", False)),
        "systemguard": "respetado",
    }


def ciclo_pre_tarea(mensaje: str, *, session_id: str | None = None) -> dict[str, Any]:
    """Claridad → lecciones → razonamiento crítico."""
    claridad = filtrar_claridad(mensaje)
    foco = claridad.get("enfocado") or mensaje
    lecciones = recuperar_lecciones(foco, n=4, session_id=session_id)
    critico = evaluar_pre_tarea(foco, lecciones_previas=lecciones)

    bloque_interno = ""
    if claridad.get("intencion_central"):
        bloque_interno = (
            "[Filtro de Claridad — uso interno]\n"
            f"Intención central: {claridad['intencion_central']}\n"
            f"Deseo: {claridad['deseo']}\n"
            f"{claridad.get('solucion_directa')}\n"
        )
    if lecciones:
        bloque_interno += (
            "[Lecciones episódicas — uso interno]\n"
            + "\n".join(f"- {x}" for x in lecciones[:3])
            + "\n"
        )
    if critico.get("correccion_proceso"):
        bloque_interno += (
            f"[Razonamiento crítico]\n{critico['correccion_proceso']}\n"
        )

    return {
        "ok": True,
        "protocolo": PROTOCOLO,
        "claridad": claridad,
        "critico": critico,
        "lecciones": lecciones,
        "bloque_interno": bloque_interno.strip(),
        "mensaje_enfocado": foco,
        "es_correccion": es_correccion_usuario(mensaje),
    }


def registrar_correccion(
    mensaje_israel: str,
    *,
    session_id: str | None = None,
    causa_raiz: str = "",
) -> dict[str, Any]:
    return registrar_incidente(
        "Corrección recibida de Israel durante el turno",
        causa_raiz=causa_raiz,
        session_id=session_id,
        correccion_israel=mensaje_israel,
    )


def registrar_exito(
    resumen: str,
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    return guardar_episodio(
        f"Éxito: {resumen.strip()[:1500]}",
        tipo="exito",
        session_id=session_id,
    )


def consolidar_sesion(
    session_id: str | None = None,
    *,
    notas: str = "",
) -> dict[str, Any]:
    return consolidar_aprendizaje(session_id, notas=notas)
