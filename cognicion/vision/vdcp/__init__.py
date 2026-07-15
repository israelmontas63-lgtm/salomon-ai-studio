"""
VDCP — Visión Dinámica de Campo Profundo (Colsub).

Pipeline de 3 etapas (fóvea humana):
1. Adquisición global (gran angular / YOLO-like)
2. Foveación selectiva (zoom lógico sin pérdida)
3. OCR de alta resolución solo en regiones foveadas
"""

from cognicion.vision.vdcp.pipeline import ejecutar_vdcp, estado_vdcp

__all__ = ["ejecutar_vdcp", "estado_vdcp"]
