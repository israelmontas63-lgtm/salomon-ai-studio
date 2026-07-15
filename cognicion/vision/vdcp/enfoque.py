"""Control de Enfoque Adaptativo — nitidez por contraste (cristalino virtual)."""

from __future__ import annotations

from typing import Any

import numpy as np


def _varianza_laplaciana(gray: np.ndarray) -> float:
    import cv2

    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _score_legibilidad(gray: np.ndarray) -> float:
    """Prioriza contraste de caracteres, no solo detección de bordes."""
    import cv2

    lap = _varianza_laplaciana(gray)
    # Contraste RMS
    mean, std = cv2.meanStdDev(gray)
    contraste = float(std[0][0])
    # Histograma: peaking en negros/blancos ayuda OCR
    hist = cv2.calcHist([gray], [0], None, [32], [0, 256]).flatten()
    hist = hist / max(hist.sum(), 1)
    entropia = -float(np.sum(hist * np.log2(hist + 1e-9)))
    return lap * 0.55 + contraste * 2.2 + (8.0 - min(entropia, 8.0)) * 3.0


def enfoque_por_contraste(bgr: np.ndarray, pasadas: int = 4) -> dict[str, Any]:
    """
    Simula acomodación del cristalino: prueba filtros de nitidez/CLAHE
    y elige el que maximiza legibilidad de caracteres.
    """
    import cv2

    if bgr is None or bgr.size == 0:
        return {"imagen": bgr, "score": 0.0, "filtro": "vacio"}

    gray0 = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    candidatos: list[tuple[str, np.ndarray, float]] = []

    # Identidad
    candidatos.append(("identidad", bgr, _score_legibilidad(gray0)))

    # CLAHE (contraste local)
    clahe = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8))
    g1 = clahe.apply(gray0)
    b1 = cv2.cvtColor(g1, cv2.COLOR_GRAY2BGR)
    candidatos.append(("clahe", b1, _score_legibilidad(g1)))

    # Unsharp mask
    blur = cv2.GaussianBlur(bgr, (0, 0), 1.2)
    sharp = cv2.addWeighted(bgr, 1.55, blur, -0.55, 0)
    g2 = cv2.cvtColor(sharp, cv2.COLOR_BGR2GRAY)
    candidatos.append(("unsharp", sharp, _score_legibilidad(g2)))

    # Denoise + sharpen (desenfoque de movimiento leve)
    den = cv2.fastNlMeansDenoisingColored(bgr, None, 4, 4, 7, 21)
    blur2 = cv2.GaussianBlur(den, (0, 0), 0.9)
    sharp2 = cv2.addWeighted(den, 1.4, blur2, -0.4, 0)
    # Kernel de enfoque
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    sharp2 = cv2.filter2D(sharp2, -1, kernel)
    g3 = cv2.cvtColor(sharp2, cv2.COLOR_BGR2GRAY)
    candidatos.append(("denoise_sharpen", sharp2, _score_legibilidad(g3)))

    # Binarización adaptativa (solo para score; OCR a veces prefiere gray)
    bin_img = cv2.adaptiveThreshold(
        g1, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
    )
    candidatos.append(
        ("adaptative_bin", cv2.cvtColor(bin_img, cv2.COLOR_GRAY2BGR), _score_legibilidad(bin_img))
    )

    # Iterar unsharp suave sobre el mejor CLAHE
    mejor_nombre, mejor_img, mejor_score = max(candidatos, key=lambda t: t[2])
    actual = mejor_img
    for i in range(max(0, pasadas - 1)):
        blur = cv2.GaussianBlur(actual, (0, 0), 0.8)
        trial = cv2.addWeighted(actual, 1.25, blur, -0.25, 0)
        gt = cv2.cvtColor(trial, cv2.COLOR_BGR2GRAY)
        sc = _score_legibilidad(gt)
        if sc > mejor_score:
            mejor_score = sc
            mejor_img = trial
            mejor_nombre = f"{mejor_nombre}+acomodacion_{i+1}"
            actual = trial
        else:
            break

    gray_f = cv2.cvtColor(mejor_img, cv2.COLOR_BGR2GRAY)
    return {
        "imagen": mejor_img,
        "gris": gray_f,
        "score": round(mejor_score, 2),
        "laplaciano": round(_varianza_laplaciana(gray_f), 2),
        "filtro": mejor_nombre,
    }
