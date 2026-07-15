"""
Adaptadores que registran los motores existentes en el kernel OS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cognicion.nucleo.kernel import NucleoSalomon


@dataclass(frozen=True)
class MotorAdaptador:
    id: str
    nombre: str
    _disponible: bool
    _descripcion: dict[str, Any]

    def disponible(self) -> bool:
        return self._disponible

    def describir(self) -> dict[str, Any]:
        return self._descripcion


def registrar_motores_predeterminados(nucleo: NucleoSalomon) -> None:
    from cognicion.llm import llm_disponible, obtener_proveedor, proveedor_respaldo_disponible
    from cognicion.conectores import listar_conectores
    from cognicion.agente.registro import listar_agentes
    from cognicion.mcp.cliente import estado_mcp
    import herramientas

    nucleo.registrar_motor(
        MotorAdaptador(
            id="motor:memoria",
            nombre="Motor de Memoria",
            _disponible=True,
            _descripcion={
                "capas": 7,
                "tecnologia": "ChromaDB + SQLite",
                "estado_detalle": "/api/cognicion/estado",
            },
        )
    )
    nucleo.registrar_motor(
        MotorAdaptador(
            id="motor:conocimiento",
            nombre="Motor de Conocimiento",
            _disponible=True,
            _descripcion={
                "conectores": listar_conectores(),
                "rag": True,
            },
        )
    )
    nucleo.registrar_motor(
        MotorAdaptador(
            id="motor:razonamiento",
            nombre="Motor de Razonamiento",
            _disponible=True,
            _descripcion={"modos": ["intencion", "chain_of_thought"]},
        )
    )
    nucleo.registrar_motor(
        MotorAdaptador(
            id="motor:aprendizaje",
            nombre="Motor de Aprendizaje Continuo",
            _disponible=True,
            _descripcion={"async": True, "capas_destino": ["preferencias", "proyecto", "aprendizaje"]},
        )
    )
    nucleo.registrar_motor(
        MotorAdaptador(
            id="motor:modelos",
            nombre="Gestor de Modelos IA",
            _disponible=llm_disponible(),
            _descripcion={
                "proveedor_activo": obtener_proveedor().nombre,
                "respaldo": proveedor_respaldo_disponible(),
                "routing_por_tarea": True,
            },
        )
    )
    nucleo.registrar_motor(
        MotorAdaptador(
            id="motor:agentes",
            nombre="Sistema de Agentes",
            _disponible=True,
            _descripcion={"agentes": [a.id for a in listar_agentes()]},
        )
    )
    nucleo.registrar_motor(
        MotorAdaptador(
            id="motor:herramientas",
            nombre="Sistema de Herramientas",
            _disponible=True,
            _descripcion={"total": len(herramientas.listar_herramientas())},
        )
    )
    nucleo.registrar_motor(
        MotorAdaptador(
            id="motor:mcp",
            nombre="Cliente MCP",
            _disponible=estado_mcp()["habilitado"],
            _descripcion=estado_mcp(),
        )
    )
    nucleo.registrar_motor(
        MotorAdaptador(
            id="motor:ciberseguridad",
            nombre="Motor de Ciberseguridad",
            _disponible=True,
            _descripcion={
                "capas": 10,
                "ofensivo": False,
                "modulos": [
                    "intrusion", "identidad", "secretos", "auditoria",
                    "anomalias", "sandbox", "monitoreo", "recuperacion",
                ],
                "api": "/api/seguridad/estado",
            },
        )
    )

    nucleo.registrar(
        "orquestador",
        nombre="Orquestador Inteligente",
        tipo="nucleo",
        metadata={"modulo": "cognicion.orquestador.MotorCognicion"},
    )
    nucleo.registrar(
        "skills",
        nombre="Sistema de Skills/Plugins",
        tipo="extension",
        metadata={"modulo": "cognicion.skills"},
    )
