"""
Registro multiagente — agentes especializados colaborativos (v80).
Ejecutores lazy: no cargan media/código pesado hasta la primera llamada.
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

    def _exec_coder(**kwargs: Any):
        from cognicion.agente.coder import ejecutar_coder

        return ejecutar_coder(
            kwargs.get("tarea") or kwargs.get("mensaje") or "",
            error_consola=kwargs.get("error_consola"),
            solo_razonamiento=bool(kwargs.get("solo_razonamiento", False)),
        )

    def _exec_visual(**kwargs: Any):
        from cognicion.agente.visual import ejecutar_visual

        return ejecutar_visual(
            kwargs.get("prompt") or kwargs.get("mensaje") or kwargs.get("tarea") or "",
            modo=kwargs.get("modo") or "auto",
        )

    def _exec_guard(**kwargs: Any):
        from cognicion.agente.guard import ejecutar_guard

        return ejecutar_guard(kwargs.get("accion") or "integridad", **kwargs)

    def _exec_coordinador(**kwargs: Any):
        from cognicion.agente.coordinador import coordinar

        return coordinar(
            kwargs.get("mensaje") or kwargs.get("tarea") or "",
            **{k: v for k, v in kwargs.items() if k not in {"mensaje", "tarea"}},
        )

    def _exec_corrector(**kwargs: Any):
        # Compat: corrector legacy → Agent_Coder (parche)
        from cognicion.agente.coder import ejecutar_coder

        return ejecutar_coder(
            kwargs.get("tarea") or "",
            error_consola=kwargs.get("error"),
            solo_razonamiento=False,
        )

    registrar_agente(
        AgenteRegistrado(
            id="coordinador",
            nombre="Coordinador Multi-Agente",
            rol="orquestacion",
            descripcion="Zero-overlap: despacha Coder / Visual / Guard (lazy Render)",
            prioridad=1,
            metadata={"protocolo": "MULTI_AGENT_DEPLOY", "version": "80.0.0"},
        ),
        ejecutor=_exec_coordinador,
    )
    registrar_agente(
        AgenteRegistrado(
            id="guard",
            nombre="Agent_Guard",
            rol="integridad",
            descripcion="Checksum SystemGuard + bloqueo deps pesadas Render",
            prioridad=2,
        ),
        ejecutor=_exec_guard,
    )
    registrar_agente(
        AgenteRegistrado(
            id="coder",
            nombre="Agent_Coder",
            rol="codigo",
            descripcion="Lógica Python/JS exclusiva",
            prioridad=10,
        ),
        ejecutor=_exec_coder,
    )
    registrar_agente(
        AgenteRegistrado(
            id="visual",
            nombre="Agent_Visual",
            rol="vision_media",
            descripcion="Búsqueda y generación visual vía APIs env",
            prioridad=15,
        ),
        ejecutor=_exec_visual,
    )
    registrar_agente(
        AgenteRegistrado(
            id="corrector",
            nombre="Agente Corrector",
            rol="codigo",
            descripcion="Alias legacy → Agent_Coder",
            prioridad=11,
            metadata={"alias_de": "coder"},
        ),
        ejecutor=_exec_corrector,
    )
    registrar_agente(
        AgenteRegistrado(
            id="investigador",
            nombre="Agente Investigador",
            rol="conocimiento",
            descripcion="Consulta RAG y conectores (legacy)",
            prioridad=20,
            activo=False,
        ),
    )
    registrar_agente(
        AgenteRegistrado(
            id="supervisor",
            nombre="Supervisor Multiagente",
            rol="orquestacion",
            descripcion="Reemplazado por Coordinador v80",
            prioridad=5,
            activo=False,
        ),
    )


_registrar_agentes_internos()
