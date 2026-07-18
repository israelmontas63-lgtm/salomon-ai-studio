"""Visión — análisis de capturas y VDCP (carga diferida)."""

from cognicion.vision.analizador import ResultadoVision, analizar_escena, analizar_imagen

__all__ = [
    "ResultadoVision",
    "analizar_escena",
    "analizar_imagen",
    "ejecutar_vdcp",
    "estado_vdcp",
]


def __getattr__(name: str):
    """Carga VDCP solo cuando se usa (evita exigir numpy al arrancar la API)."""
    if name in ("ejecutar_vdcp", "estado_vdcp"):
        from cognicion.vision.vdcp import estado_vdcp, ejecutar_vdcp

        return ejecutar_vdcp if name == "ejecutar_vdcp" else estado_vdcp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
