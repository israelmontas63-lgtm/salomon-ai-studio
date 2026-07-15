"""VDCP — carga diferida del pipeline (no exige numpy al importar el paquete)."""

from __future__ import annotations

__all__ = ["ejecutar_vdcp", "estado_vdcp"]


def __getattr__(name: str):
    if name in ("ejecutar_vdcp", "estado_vdcp"):
        from cognicion.vision.vdcp.pipeline import estado_vdcp, ejecutar_vdcp

        return ejecutar_vdcp if name == "ejecutar_vdcp" else estado_vdcp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
