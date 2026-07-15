"""
Grafo LangGraph de Salomón — orquesta multi-agente + razonamiento + especialistas.
"""

from __future__ import annotations

from typing import Any

from cognicion.grafo.estado import EstadoSalomon
from cognicion.grafo.nodos import (
    enrutar_despues_coordinador,
    enrutar_despues_orquestador,
    enrutar_despues_razonamiento,
    nodo_busqueda,
    nodo_contenido,
    nodo_coordinador,
    nodo_hablar,
    nodo_imagen,
    nodo_orquestador,
    nodo_razonamiento,
    nodo_tecnico,
    nodo_video,
)

_grafo_compilado = None

_RUTAS_AGENTE = {
    "hablar": "hablar",
    "contenido": "contenido",
    "tecnico": "tecnico",
    "imagen": "imagen",
    "video": "video",
    "busqueda": "busqueda",
    "orquestador": "orquestador",
}


def crear_grafo_salomon():
    """Construye y compila el StateGraph (lazy)."""
    from langgraph.graph import END, StateGraph

    g = StateGraph(EstadoSalomon)
    g.add_node("coordinador", nodo_coordinador)
    g.add_node("orquestador", nodo_orquestador)
    g.add_node("razonamiento", nodo_razonamiento)
    g.add_node("busqueda", nodo_busqueda)
    g.add_node("hablar", nodo_hablar)
    g.add_node("contenido", nodo_contenido)
    g.add_node("tecnico", nodo_tecnico)
    g.add_node("imagen", nodo_imagen)
    g.add_node("video", nodo_video)

    g.set_entry_point("coordinador")
    g.add_conditional_edges(
        "coordinador",
        enrutar_despues_coordinador,
        {"razonamiento": "razonamiento", **_RUTAS_AGENTE},
    )
    g.add_conditional_edges(
        "orquestador",
        enrutar_despues_orquestador,
        {"razonamiento": "razonamiento"},
    )
    g.add_conditional_edges(
        "razonamiento",
        enrutar_despues_razonamiento,
        {**_RUTAS_AGENTE, "fin": END},
    )
    for nombre in ("hablar", "contenido", "tecnico", "imagen", "video", "busqueda"):
        g.add_edge(nombre, END)

    return g.compile()


def obtener_grafo(*, forzar_recrear: bool = False):
    global _grafo_compilado
    if forzar_recrear or _grafo_compilado is None:
        _grafo_compilado = crear_grafo_salomon()
    return _grafo_compilado


def ejecutar_grafo(
    mensaje: str,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    profundizar: bool = False,
    media_path: str | None = None,
    media_ops: dict[str, Any] | None = None,
    forzar_busqueda: bool = False,
    forzar_orquesta: bool = False,
) -> EstadoSalomon:
    """Ejecuta un turno del grafo multiagente."""
    grafo = obtener_grafo()
    meta = dict(metadata or {})
    if profundizar:
        meta["profundizar"] = True
    if forzar_busqueda:
        meta["forzar_busqueda"] = True
        meta.setdefault("ruta_forzada", "busqueda")
    if forzar_orquesta:
        meta["forzar_orquesta"] = True
        meta["ruta_forzada"] = "orquestador"
    if media_path:
        meta["media_path"] = media_path
    if media_ops:
        meta["media_ops"] = media_ops
    inicial: EstadoSalomon = {
        "mensaje": mensaje,
        "session_id": session_id,
        "metadata": meta,
        "media_path": media_path,
        "media_ops": media_ops or {},
        "necesita_busqueda": bool(forzar_busqueda),
        "necesita_orquesta": bool(forzar_orquesta),
        "error": None,
    }
    return grafo.invoke(inicial)
