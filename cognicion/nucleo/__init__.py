"""Kernel central del OS de Salomón."""

from cognicion.nucleo.contratos import ComponenteOS, MotorOS
from cognicion.nucleo.eventos import BusEventos
from cognicion.nucleo.kernel import NucleoSalomon, obtener_nucleo, reiniciar_nucleo

__all__ = [
    "BusEventos",
    "ComponenteOS",
    "MotorOS",
    "NucleoSalomon",
    "obtener_nucleo",
    "reiniciar_nucleo",
]
