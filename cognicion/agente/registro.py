"""
Registro multiagente — agentes especializados colaborativos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from cognicion.registro import evento, obtener_logger

_log = obtener_logger("agentes")


@dataclass
class AgenteRegistrado:
    id: str
    nombre: str
    rol: str
    descripcion: str
    activo: bool = True
    prioridad: int = 50
    metadata: dict[str, Any] = field(default_factory=dict)


_EJECUTORES: dict[str, Callable[..., Any]] = {}
_AGENTES: dict[str, AgenteRegistrado] = {}


def registrar_agente(
    agente: AgenteRegistrado,
    ejecutor: Callable[..., Any] | None = None,
) -> None:
    _AGENTES[agente.id] = agente
    if ejecutor is not None:
        _EJECUTORES[agente.id] = ejecutor
    evento(_log, "agente_registrado", id=agente.id, rol=agente.rol)


def listar_agentes(activos_only: bool = True) -> list[AgenteRegistrado]:
    items = list(_AGENTES.values())
    if activos_only:
        items = [a for a in items if a.activo]
    return sorted(items, key=lambda a: a.prioridad)


def obtener_agente(agente_id: str) -> AgenteRegistrado | None:
    return _AGENTES.get(agente_id)


def ejecutar_agente(agente_id: str, **kwargs: Any) -> Any | None:
    ejecutor = _EJECUTORES.get(agente_id)
    if ejecutor is None:
        return None
    return ejecutor(**kwargs)


def _registrar_agentes_internos() -> None:
    if _AGENTES:
        return

    from cognicion.agente.autonomo import AgenteAutonomo

    corrector = AgenteAutonomo()

    registrar_agente(
        AgenteRegistrado(
            id="corrector",
            nombre="Agente Corrector",
            rol="codigo",
            descripcion="Aplica parches seguros en archivos del proyecto",
            prioridad=10,
        ),
        ejecutor=corrector.corregir,
    )
    registrar_agente(
        AgenteRegistrado(
            id="investigador",
            nombre="Agente Investigador",
            rol="conocimiento",
            descripcion="Consulta RAG y conectores (Fase 5)",
            prioridad=20,
            activo=False,
        ),
    )
    registrar_agente(
        AgenteRegistrado(
            id="supervisor",
            nombre="Supervisor Multiagente",
            rol="orquestacion",
            descripcion="Delega subtareas entre agentes (Fase 5)",
            prioridad=5,
            activo=False,
        ),
    )


_registrar_agentes_internos()
