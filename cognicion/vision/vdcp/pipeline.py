"""
Pipeline VDCP completo — orquestación Colsub.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Any

try:
    import numpy as np
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Falta numpy. En Render Shell ejecuta: pip install numpy && python -c \"import numpy; print(numpy.__file__)\""
    ) from exc

from cognicion.vision.vdcp.adquisicion import adquisicion_global
from cognicion.vision.vdcp.enfoque import enfoque_por_contraste
from cognicion.vision.vdcp.foveacion import fovear_region
from cognicion.vision.vdcp.ocr_motor import leer_fovea


def _cargar_bgr(
    imagen_base64: str | None = None,
    ruta: str | Path | None = None,
    imagen_bytes: bytes | None = None,
) -> np.ndarray:
    import cv2

    raw: bytes | None = None
    if imagen_bytes:
        raw = imagen_bytes
    elif imagen_base64:
        raw = base64.b64decode(imagen_base64)
    elif ruta:
        img = cv2.imread(str(ruta))
        if img is None:
            raise ValueError("imagen_no_legible")
        return img
    if not raw:
        raise ValueError("imagen_vacia")
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("decode_fallido")
    return img


def _narrativa_roi(det: dict[str, Any]) -> str:
    tipo = det.get("tipo") or "objeto"
    escala = det.get("escala") or "medio"
    texto = (det.get("lectura") or {}).get("texto") or ""
    conf = float((det.get("lectura") or {}).get("confianza") or 0)
    pt = (det.get("lectura") or {}).get("tamano_estimado_pt")
    pct = int(round(conf * 100))
    if texto:
        return (
            f"He detectado un(a) {tipo} ({escala}) y he foveado para leer "
            f"el texto «{texto}» (micro≈{pt}pt) con un {pct}% de confianza."
            if escala == "micro"
            else (
                f"He detectado un(a) {tipo} ({escala}) y he foveado para leer "
                f"el texto «{texto}» (~{pt}pt) con un {pct}% de confianza."
            )
        )
    return (
        f"He detectado un(a) {tipo} ({escala}) y foveé la región, "
        f"pero no extraje texto legible (confianza {pct}%)."
    )


def ejecutar_vdcp(
    *,
    imagen_base64: str | None = None,
    ruta: str | Path | None = None,
    imagen_bytes: bytes | None = None,
    max_foveas: int | None = None,
    ocr_preferido: str | None = None,
) -> dict[str, Any]:
    """
    Ejecuta las 3 etapas y devuelve estructura consolidada para Colsub.
    Prioriza legibilidad de caracteres sobre mera detección.
    """
    t0 = time.perf_counter()
    try:
        import settings as st

        max_f = max_foveas or int(getattr(st, "VDCP_MAX_FOVEAS", 12))
        ocr_pref = ocr_preferido or getattr(st, "VDCP_OCR_ENGINE", "") or None
    except Exception:
        max_f = max_foveas or 12
        ocr_pref = ocr_preferido

    try:
        bgr = _cargar_bgr(imagen_base64, ruta, imagen_bytes)
    except Exception as exc:
        return {
            "exito": False,
            "pipeline": "VDCP",
            "error": str(exc),
            "hallazgos": [],
            "narrativa_consolidada": "No pude adquirir la imagen para VDCP.",
        }

    # Etapa 1
    escena = adquisicion_global(bgr)
    rois = list(escena.get("rois") or [])

    # Si no hay ROI, fovear centro + bandas (libro: título arriba, pie abajo)
    if not rois:
        h, w = bgr.shape[:2]
        rois = [
            {
                "id": "auto_titulo",
                "tipo": "senal",
                "bbox": [int(w * 0.05), int(h * 0.04), int(w * 0.9), int(h * 0.18)],
                "confianza": 0.4,
                "escala": "grande",
                "motor": "fallback_layout",
            },
            {
                "id": "auto_cuerpo",
                "tipo": "documento",
                "bbox": [int(w * 0.08), int(h * 0.22), int(w * 0.84), int(h * 0.55)],
                "confianza": 0.35,
                "escala": "medio",
                "motor": "fallback_layout",
            },
            {
                "id": "auto_pie",
                "tipo": "texto",
                "bbox": [int(w * 0.1), int(h * 0.88), int(w * 0.8), int(h * 0.08)],
                "confianza": 0.35,
                "escala": "micro",
                "motor": "fallback_layout",
            },
        ]

    # Priorizar: señales/documentos + textos (incl. micro)
    def _prio(r: dict[str, Any]) -> tuple:
        tipo = r.get("tipo")
        esc = r.get("escala")
        return (
            0 if tipo in ("senal", "documento") else 1 if tipo == "texto" else 2,
            0 if esc == "micro" else 1,
            -float(r.get("confianza") or 0),
        )

    rois_ord = sorted(rois, key=_prio)[:max_f]
    hallazgos: list[dict[str, Any]] = []

    for roi in rois_ord:
        bbox = roi.get("bbox") or [0, 0, 10, 10]
        escala = str(roi.get("escala") or "medio")
        # Etapa 2
        fov = fovear_region(bgr, bbox, escala=escala)
        crop = fov["imagen"]
        # Enfoque adaptativo
        enf = enfoque_por_contraste(crop)
        # Etapa 3 — OCR solo en fóvea enfocada
        lectura = leer_fovea(
            enf["imagen"],
            gray=enf.get("gris"),
            altura_roi_px=int(bbox[3]),
            factor_zoom=float(fov.get("factor_zoom") or 1),
            preferir=ocr_pref,
        )
        det = {
            "id": roi.get("id"),
            "tipo": roi.get("tipo"),
            "escala": escala,
            "bbox": bbox,
            "confianza_deteccion": roi.get("confianza"),
            "motor_deteccion": roi.get("motor"),
            "foveado": True,
            "factor_zoom": fov.get("factor_zoom"),
            "modo_fovea": fov.get("modo"),
            "enfoque": {
                "filtro": enf.get("filtro"),
                "score_legibilidad": enf.get("score"),
                "laplaciano": enf.get("laplaciano"),
            },
            "lectura": {
                "texto": lectura.get("texto"),
                "confianza": lectura.get("confianza"),
                "motor": lectura.get("motor"),
                "tamano_estimado_pt": lectura.get("tamano_estimado_pt"),
                "legible": lectura.get("legible"),
            },
        }
        det["narrativa"] = _narrativa_roi(det)
        hallazgos.append(det)

    # Deduplicar lecturas casi idénticas
    vistos: set[str] = set()
    unicos: list[dict[str, Any]] = []
    for h in hallazgos:
        t = ((h.get("lectura") or {}).get("texto") or "").strip().lower()
        if t and t in vistos:
            continue
        if t:
            vistos.add(t)
        unicos.append(h)

    narrativas = [h["narrativa"] for h in unicos if h.get("narrativa")]
    textos_leidos = [
        (h.get("lectura") or {}).get("texto")
        for h in unicos
        if (h.get("lectura") or {}).get("texto")
    ]
    consolidada = " ".join(narrativas) if narrativas else (
        "Escena analizada en gran angular; no se extrajo texto foveado."
    )
    if textos_leidos:
        consolidada += " Texto consolidado: «" + " / ".join(textos_leidos[:8]) + "»."

    return {
        "exito": True,
        "pipeline": "VDCP",
        "protocolo": "fovea_3_etapas",
        "escena": {
            "ancho": escena.get("ancho"),
            "alto": escena.get("alto"),
            "motores_adquisicion": escena.get("motores"),
            "n_rois_detectados": escena.get("n_rois"),
        },
        "hallazgos": unicos,
        "textos": textos_leidos,
        "narrativa_consolidada": consolidada,
        "ms": round((time.perf_counter() - t0) * 1000, 1),
        "prioridad": "legibilidad_caracteres",
    }


def estado_vdcp() -> dict[str, Any]:
    yolo = False
    yolo_weights = None
    paddle = False
    tess = False
    tess_cmd = None
    try:
        import ultralytics  # noqa: F401

        yolo = True
        try:
            import settings as st

            yolo_weights = str(getattr(st, "VDCP_YOLO_WEIGHTS", "") or "")
        except Exception:
            pass
    except Exception:
        pass
    try:
        import paddleocr  # noqa: F401

        paddle = True
    except Exception:
        pass
    try:
        import pytesseract
        from cognicion.vision.vdcp.ocr_motor import _configurar_tesseract

        if _configurar_tesseract():
            tess = True
            tess_cmd = str(pytesseract.pytesseract.tesseract_cmd)
    except Exception:
        tess = False
    try:
        import pytesseract  # noqa: F401

        pytesseract_pkg = True
    except Exception:
        pytesseract_pkg = False
    try:
        import easyocr  # noqa: F401

        easy = True
    except Exception:
        easy = False
    gemini = False
    try:
        from cognicion.llm import llm_disponible

        gemini = bool(llm_disponible())
    except Exception:
        pass
    return {
        "pipeline": "VDCP",
        "etapas": [
            "adquisicion_global",
            "foveacion_selectiva",
            "ocr_alta_resolucion",
        ],
        "motores": {
            "yolo": yolo,
            "yolo_weights": yolo_weights,
            "opencv_angular": True,
            "proyeccion_lineas": True,
            "paddleocr": paddle,
            "tesseract": tess,
            "tesseract_cmd": tess_cmd,
            "pytesseract": pytesseract_pkg,
            "easyocr": easy,
            "gemini_foveal": gemini,
            "enfoque_contraste": True,
        },
        "listo": True,
    }
