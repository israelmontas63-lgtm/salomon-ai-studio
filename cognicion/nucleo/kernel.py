"""
Kernel central del OS de Salomón — registro, lifecycle y mapa del sistema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from cognicion.nucleo.contratos import ComponenteOS, MotorOS
from cognicion.nucleo.eventos import BusEventos

VERSION_NUCLEO = "1.0.0"


@dataclass
class ComponenteRegistrado:
    id: str
    nombre: str
    tipo: str
    version: str = "1.0.0"
    estado: str = "activo"
    metadata: dict[str, Any] = field(default_factory=dict)


class NucleoSalomon:
    """Kernel central — punto único de verdad del estado del OS."""

    def __init__(self) -> None:
        self.version = VERSION_NUCLEO
        self.eventos = BusEventos()
        self._componentes: dict[str, ComponenteRegistrado] = {}
        self._motores: dict[str, MotorOS] = {}
        self._iniciado = False
        self._lock = RLock()

    def registrar(
        self,
        componente_id: str,
        *,
        nombre: str,
        tipo: str,
        version: str = "1.0.0",
        estado: str = "activo",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            self._componentes[componente_id] = ComponenteRegistrado(
                id=componente_id,
                nombre=nombre,
                tipo=tipo,
                version=version,
                estado=estado,
                metadata=metadata or {},
            )

    def registrar_motor(self, motor: MotorOS) -> None:
        with self._lock:
            self._motores[motor.id] = motor
        self.registrar(
            motor.id,
            nombre=motor.nombre,
            tipo="motor",
            metadata=motor.describir(),
        )

    def registrar_componente(self, componente: ComponenteOS) -> None:
        self.registrar(
            componente.id,
            nombre=componente.nombre,
            tipo="componente",
            version=componente.version,
            metadata=componente.estado(),
        )

    def iniciar(self) -> None:
        if self._iniciado:
            return
        with self._lock:
            self._registrar_motores_internos()
            self._iniciado = True
        self.eventos.emitir(
            "sistema:inicio",
            version=self.version,
            componentes=len(self._componentes),
        )

    def _registrar_motores_internos(self) -> None:
        from cognicion.nucleo.motores import registrar_motores_predeterminados

        registrar_motores_predeterminados(self)

    def mapa(self) -> dict[str, Any]:
        with self._lock:
            componentes = [
                {
                    "id": c.id,
                    "nombre": c.nombre,
                    "tipo": c.tipo,
                    "version": c.version,
                    "estado": c.estado,
                    "metadata": c.metadata,
                }
                for c in self._componentes.values()
            ]
            motores = {
                mid: {
                    "nombre": m.nombre,
                    "disponible": m.disponible(),
                    **m.describir(),
                }
                for mid, m in self._motores.items()
            }

        return {
            "version": self.version,
            "iniciado": self._iniciado,
            "componentes": sorted(componentes, key=lambda x: x["id"]),
            "motores": motores,
            "eventos_recientes": self.eventos.ultimos(10),
            "contadores_eventos": self.eventos.contadores(),
        }

    def obtener_motor(self, motor_id: str) -> MotorOS | None:
        with self._lock:
            return self._motores.get(motor_id)


_nucleo: NucleoSalomon | None = None
_nucleo_lock = RLock()


def obtener_nucleo() -> NucleoSalomon:
    global _nucleo
    with _nucleo_lock:
        if _nucleo is None:
            _nucleo = NucleoSalomon()
            _nucleo.iniciar()
        return _nucleo


def reiniciar_nucleo() -> None:
    """Solo para tests — reinicia el singleton."""
    global _nucleo
    with _nucleo_lock:
        _nucleo = None
