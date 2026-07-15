"""
Motor de Ciberseguridad de Salomón — defensa en profundidad.
"""

from cognicion.seguridad.utilidades import (
    contiene_patron_sospechoso,
    enmascarar_secreto,
    ruta_sensible,
)
from cognicion.seguridad.tipos import RolAcceso, Severidad, TipoAmenaza

__all__ = [
    "RolAcceso",
    "Severidad",
    "TipoAmenaza",
    "contiene_patron_sospechoso",
    "enmascarar_secreto",
    "ruta_sensible",
]


def obtener_motor():
    from cognicion.seguridad.motor import obtener_motor as _obtener
    return _obtener()


def reiniciar_motor():
    from cognicion.seguridad.motor import reiniciar_motor as _reiniciar
    _reiniciar()
