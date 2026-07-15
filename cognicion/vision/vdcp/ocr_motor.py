"""Etapa 3 — Motor de lectura de alta resolución (OCR solo en fóvea)."""

from __future__ import annotations

import re
from typing import Any

import numpy as np


def _estimado_pt(altura_px: int, factor_zoom: float, dpi_ref: float = 96.0) -> float:
    """Estima tamaño tipográfico aproximado en puntos."""
    h_orig = altura_px / max(factor_zoom, 1e-6)
    # 1 pt ≈ 1/72 inch; px = pt * dpi / 72
    pt = h_orig * 72.0 / dpi_ref
    return round(max(4.0, min(pt, 120.0)), 1)


_PADDLE = None


def _ocr_paddle(bgr: np.ndarray) -> list[dict[str, Any]]:
    global _PADDLE
    try:
        from paddleocr import PaddleOCR
    except Exception:
        return []
    try:
        if _PADDLE is None:
            _PADDLE = PaddleOCR(use_angle_cls=True, lang="es", show_log=False)
        result = _PADDLE.ocr(bgr, cls=True)
    except Exception:
        try:
            ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
            result = ocr.ocr(bgr, cls=True)
        except Exception:
            return []
    lines: list[dict[str, Any]] = []
    for block in result or []:
        for row in block or []:
            if not row or len(row) < 2:
                continue
            txt, conf = row[1][0], float(row[1][1])
            if txt and str(txt).strip():
                lines.append(
                    {"texto": str(txt).strip(), "confianza": conf, "motor": "paddleocr"}
                )
    return lines


def _configurar_tesseract() -> bool:
    """Apunta pytesseract al binario de Tesseract si existe."""
    try:
        import pytesseract
    except Exception:
        return False
    import os
    from pathlib import Path

    candidatos: list[str] = []
    try:
        import settings as st

        cmd = getattr(st, "TESSERACT_CMD", "") or ""
        if cmd:
            candidatos.append(cmd)
    except Exception:
        pass
    env = os.getenv("TESSERACT_CMD", "").strip()
    if env:
        candidatos.append(env)
    candidatos.extend(
        [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            str(Path.home() / "AppData/Local/Programs/Tesseract-OCR/tesseract.exe"),
            "tesseract",
        ]
    )
    for c in candidatos:
        p = Path(c) if c != "tesseract" else None
        if p is not None and not p.is_file():
            continue
        try:
            pytesseract.pytesseract.tesseract_cmd = c
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            continue
    return False


def _ocr_tesseract(bgr: np.ndarray, gray: np.ndarray | None = None) -> list[dict[str, Any]]:
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return []
    if not _configurar_tesseract():
        return []
    import cv2

    img = gray if gray is not None else cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    pil = Image.fromarray(img)
    configs = [
        "--oem 3 --psm 6",   # bloque uniforme
        "--oem 3 --psm 11",  # sparse text (pies de página)
        "--oem 3 --psm 7",   # línea única (señales)
    ]
    mejores: list[dict[str, Any]] = []
    for cfg in configs:
        try:
            data = pytesseract.image_to_data(
                pil, lang="spa+eng", config=cfg, output_type=pytesseract.Output.DICT
            )
        except Exception:
            try:
                data = pytesseract.image_to_data(
                    pil, config=cfg, output_type=pytesseract.Output.DICT
                )
            except Exception:
                continue
        n = len(data.get("text") or [])
        for i in range(n):
            t = (data["text"][i] or "").strip()
            if not t:
                continue
            conf = float(data["conf"][i])
            if conf < 0:
                continue
            mejores.append(
                {
                    "texto": t,
                    "confianza": conf / 100.0,
                    "motor": "tesseract_v5",
                    "psm": cfg,
                }
            )
        if mejores:
            break
    # Fusionar tokens de una pasada en líneas
    if not mejores:
        try:
            txt = pytesseract.image_to_string(pil, config=configs[0]).strip()
            if txt:
                return [{"texto": txt, "confianza": 0.55, "motor": "tesseract_v5"}]
        except Exception:
            pass
    return mejores


def _ocr_gemini_foveal(bgr: np.ndarray) -> list[dict[str, Any]]:
    """Respaldo multimodal: OCR solo sobre el recorte foveado."""
    try:
        import cv2
        from cognicion.llm import analizar_imagen_gemini, llm_disponible
        from cognicion.config import GEMINI_VISION_MODEL
    except Exception:
        return []
    if not llm_disponible():
        return []
    ok, buf = cv2.imencode(".png", bgr)
    if not ok:
        return []
    prompt = (
        "Eres un motor OCR de alta precisión. Transcribe TODO el texto visible "
        "en esta región foveada, respetando mayúsculas y números. "
        "Si hay título grande y nota pequeña, incluye ambos. "
        "Responde SOLO el texto transcrito, sin comentarios."
    )
    try:
        texto = analizar_imagen_gemini(
            prompt,
            buf.tobytes(),
            mime_type="image/png",
            model_name=GEMINI_VISION_MODEL,
        )
    except Exception:
        return []
    if not texto or not str(texto).strip():
        return []
    limpio = re.sub(r"\s+", " ", str(texto)).strip()
    # Rechazar respuestas de chat/fallback que no son OCR
    ban = (
        "no disponible",
        "describe la imagen",
        "sin motor",
        "no puedo",
        "como modelo",
        "análisis visual",
        "analisis visual",
    )
    low = limpio.lower()
    if any(b in low for b in ban) or len(limpio) > 500:
        return []
    return [{"texto": limpio, "confianza": 0.82, "motor": "gemini_foveal"}]


def _ocr_easyocr(bgr: np.ndarray) -> list[dict[str, Any]]:
    try:
        import easyocr
    except Exception:
        return []
    global _EASYOCR
    try:
        if _EASYOCR is None:
            _EASYOCR = easyocr.Reader(["es", "en"], gpu=False, verbose=False)
        result = _EASYOCR.readtext(bgr)
    except Exception:
        return []
    lines: list[dict[str, Any]] = []
    for row in result or []:
        if len(row) < 3:
            continue
        txt, conf = str(row[1]).strip(), float(row[2])
        if txt:
            lines.append({"texto": txt, "confianza": conf, "motor": "easyocr"})
    return lines


_EASYOCR = None


def leer_fovea(
    bgr: np.ndarray,
    *,
    gray: np.ndarray | None = None,
    altura_roi_px: int = 32,
    factor_zoom: float = 1.0,
    preferir: str | None = None,
) -> dict[str, Any]:
    """
    Activa OCR solo en la región ya enfocada.
    Prioridad: PaddleOCR → Tesseract 5 → EasyOCR → Gemini foveal.
    """
    preferir = (preferir or "").lower()
    lineas: list[dict[str, Any]] = []
    motor_usado = "ninguno"

    orden = ["paddle", "tesseract", "easyocr"]
    try:
        import settings as st

        if getattr(st, "VDCP_USAR_GEMINI", False) or preferir == "gemini":
            orden.append("gemini")
    except Exception:
        pass
    if preferir in ("tesseract", "paddle", "easyocr", "gemini"):
        orden = [preferir] + [m for m in orden if m != preferir]

    for m in orden:
        if m == "paddle":
            lineas = _ocr_paddle(bgr)
        elif m == "tesseract":
            lineas = _ocr_tesseract(bgr, gray)
        elif m == "easyocr":
            lineas = _ocr_easyocr(bgr)
        else:
            lineas = _ocr_gemini_foveal(bgr)
        if lineas:
            motor_usado = lineas[0].get("motor", m)
            break

    # Consolidar tokens cercanos
    textos = [L["texto"] for L in lineas if L.get("texto")]
    if len(textos) > 1 and all(len(t) < 40 for t in textos):
        texto = " ".join(textos)
        conf = float(np.mean([float(L.get("confianza") or 0) for L in lineas]))
    elif textos:
        # Preferir la línea más larga con buena confianza
        mejor = max(lineas, key=lambda L: (len(L.get("texto") or ""), L.get("confianza") or 0))
        texto = mejor["texto"]
        conf = float(mejor.get("confianza") or 0)
        # Si hay varias líneas sustanciales, unir
        sustanciales = [L["texto"] for L in lineas if len(L.get("texto") or "") >= 3]
        if len(sustanciales) >= 2:
            texto = " | ".join(dict.fromkeys(sustanciales))  # unique preserve order
            conf = float(np.mean([float(L.get("confianza") or 0) for L in lineas]))
    else:
        texto = ""
        conf = 0.0

    return {
        "texto": texto,
        "confianza": round(conf, 4),
        "motor": motor_usado,
        "lineas": lineas[:40],
        "tamano_estimado_pt": _estimado_pt(altura_roi_px, factor_zoom),
        "legible": bool(texto) and conf >= 0.35,
    }
