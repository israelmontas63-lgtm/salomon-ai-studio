"""Acciones reales de Salomón — módulos de funcionalidad sin alterar el núcleo."""

from acciones.hablar import hablar
from acciones.reproducir import hablar_y_reproducir, limpiar_audio_viejo
from acciones.bienvenida import ciclo_bienvenida_completa, generar_frase_bienvenida

__all__ = [
    "hablar",
    "hablar_y_reproducir",
    "limpiar_audio_viejo",
    "generar_frase_bienvenida",
    "ciclo_bienvenida_completa",
]
