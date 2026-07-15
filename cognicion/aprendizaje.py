"""
Motor de aprendizaje — reflexión post-turno y actualización de memoria útil.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol


class MemoriaAprendizaje(Protocol):
    activa: bool

    def guardar_preferencia(self, texto: str) -> str | None: ...

    def guardar_aprendizaje(self, texto: str, categoria: str = "contexto") -> str | None: ...

    def guardar_proyecto(self, texto: str, nombre: str | None = None) -> str | None: ...


@dataclass
class ResultadoAprendizaje:
    procesado: bool = False
    recuerdos: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


_PATRON_PREFERENCIA = re.compile(
    r"(?:prefiero|me gusta|recuerda que|siempre usa|no uses|odio|evita)\s+(.{8,120})",
    re.IGNORECASE,
)

_PATRON_PROYECTO_NOMBRE = re.compile(
    r"(?:el proyecto se llama|este proyecto es|proyecto:?)\s+(.{3,80})",
    re.IGNORECASE,
)

_PATRON_PROYECTO_NOTA = re.compile(
    r"(?:en este proyecto|estamos trabajando en|para este proyecto|contexto del proyecto:?)\s+(.{8,200})",
    re.IGNORECASE,
)


def _extraer_preferencias(usuario: str) -> list[str]:
    hallados: list[str] = []
    for match in _PATRON_PREFERENCIA.finditer(usuario or ""):
        texto = match.group(1).strip(" .,!?:;")
        if len(texto) >= 8:
            hallados.append(texto)
    return hallados[:3]


def _extraer_proyecto(usuario: str) -> tuple[str | None, str | None]:
    """Devuelve (nombre, nota) si el mensaje define contexto de proyecto."""
    nombre: str | None = None
    nota: str | None = None

    match_nombre = _PATRON_PROYECTO_NOMBRE.search(usuario or "")
    if match_nombre:
        nombre = match_nombre.group(1).strip(" .,!?:;")[:80]

    match_nota = _PATRON_PROYECTO_NOTA.search(usuario or "")
    if match_nota:
        nota = match_nota.group(1).strip(" .,!?:;")[:200]

    return nombre, nota


def _extraer_hechos_utiles(usuario: str, asistente: str) -> list[tuple[str, str, str | None]]:
    """Devuelve tuplas (texto, categoria, nombre_proyecto_opcional)."""
    recuerdos: list[tuple[str, str, str | None]] = []

    for pref in _extraer_preferencias(usuario):
        recuerdos.append((pref, "preferencia", None))

    nombre_proj, nota_proj = _extraer_proyecto(usuario)
    if nombre_proj:
        recuerdos.append((f"Proyecto: {nombre_proj}", "proyecto", nombre_proj))
    if nota_proj:
        recuerdos.append((nota_proj, "proyecto", nombre_proj))

    if len(usuario or "") > 20 and "?" not in (usuario or ""):
        resumen = f"Contexto del usuario: {usuario[:200]}"
        if not any(r[0] == resumen for r in recuerdos):
            recuerdos.append((resumen, "contexto", None))

    if "error" in (usuario or "").lower() and len(asistente or "") > 40:
        recuerdos.append((
            f"Solución previa relacionada: {asistente[:180]}",
            "aprendizaje",
            None,
        ))

    return recuerdos[:5]


def procesar_turno(
    session_id: str,
    usuario: str,
    asistente: str,
    gestor: MemoriaAprendizaje,
    metadata_turno: dict[str, Any] | None = None,
) -> ResultadoAprendizaje:
    """
    Analiza el turno y persiste solo información útil en capas de memoria.
    """
    meta = metadata_turno or {}
    recuerdos = _extraer_hechos_utiles(usuario, asistente)

    if not gestor.activa or not recuerdos:
        return ResultadoAprendizaje(
            procesado=bool(recuerdos),
            recuerdos=[r[0] for r in recuerdos],
            metadata={"motivo": "sin_persistencia" if not recuerdos else "memoria_inactiva"},
        )

    guardados: list[str] = []
    proyecto_actualizado = False

    for texto, categoria, nombre_proj in recuerdos:
        doc_id: str | None = None
        if categoria == "preferencia":
            doc_id = gestor.guardar_preferencia(texto)
        elif categoria == "proyecto":
            doc_id = gestor.guardar_proyecto(texto, nombre=nombre_proj)
            proyecto_actualizado = True
        else:
            doc_id = gestor.guardar_aprendizaje(texto, categoria=categoria)
        if doc_id:
            guardados.append(texto)

    return ResultadoAprendizaje(
        procesado=True,
        recuerdos=guardados,
        metadata={
            "intencion": meta.get("cognicion", {}).get("intencion"),
            "aprendizajes_guardados": len(guardados),
            "proyecto_actualizado": proyecto_actualizado,
            "session_id": session_id,
        },
    )
