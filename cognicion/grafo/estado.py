"""Estado tipado del grafo multiagente de Salomón."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


RutaAgente = Literal[
    "hablar",
    "contenido",
    "tecnico",
    "imagen",
    "video",
    "busqueda",
    "orquestador",
    "fin",
]
ModoRazonamiento = Literal["rapido", "profundo"]


class EstadoSalomon(TypedDict, total=False):
    """Estado compartido entre nodos del grafo."""

    mensaje: str
    session_id: str | None
    intencion: str
    ruta: RutaAgente
    modo_razonamiento: ModoRazonamiento
    hechos_personales: str
    razonamiento: dict[str, Any]
    necesita_busqueda: bool
    necesita_orquesta: bool
    consulta_busqueda: str
    resultado_busqueda: dict[str, Any]
    hallazgos_agentes: dict[str, Any]
    sintesis_lista: bool
    respuesta: str
    borrador_guion: str
    resultado_tecnico: str
    resultado_imagen: dict[str, Any]
    resultado_video: dict[str, Any]
    media_path: str | None
    media_ops: dict[str, Any]
    metadata: dict[str, Any]
    error: str | None
