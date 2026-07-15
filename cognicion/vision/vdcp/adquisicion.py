"""Etapa 1 — Adquisición Global (gran angular). Detección de ROIs de interés."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np


@dataclass
class ROI:
    id: str
    tipo: str  # rostro | cartel | documento | texto | objeto | senal
    bbox: tuple[int, int, int, int]  # x, y, w, h
    confianza: float
    escala: str = "medio"  # grande | medio | micro
    motor: str = "angular"
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["bbox"] = list(self.bbox)
        return d


def _clasificar_escala(h_img: int, h_roi: int) -> str:
    ratio = h_roi / max(h_img, 1)
    if ratio >= 0.18:
        return "grande"
    if ratio <= 0.045:
        return "micro"
    return "medio"


def _nms(rois: list[ROI], iou_thr: float = 0.45) -> list[ROI]:
    if not rois:
        return []
    boxes = np.array([r.bbox for r in rois], dtype=np.float32)
    scores = np.array([r.confianza for r in rois], dtype=np.float32)
    x1, y1 = boxes[:, 0], boxes[:, 1]
    x2, y2 = boxes[:, 0] + boxes[:, 2], boxes[:, 1] + boxes[:, 3]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        inds = np.where(iou <= iou_thr)[0]
        order = order[inds + 1]
    return [rois[i] for i in keep]


_YOLO_MODEL = None
_YOLO_WEIGHTS_CARGADOS: str | None = None


def _obtener_yolo():
    """Singleton YOLO — evita recargar pesos en cada frame."""
    global _YOLO_MODEL, _YOLO_WEIGHTS_CARGADOS
    try:
        from ultralytics import YOLO
        import settings as st

        weights = str(getattr(st, "VDCP_YOLO_WEIGHTS", "yolov8n.pt") or "yolov8n.pt")
        # Preferir pesos locales del proyecto
        from pathlib import Path

        p = Path(weights)
        if not p.is_file():
            try:
                import settings as st2

                alt = Path(st2.DATA_DIR) / "modelos" / "vdcp" / "yolov8n.pt"
            except Exception:
                alt = Path(__file__).resolve().parents[3] / "data" / "modelos" / "vdcp" / "yolov8n.pt"
            if alt.is_file():
                weights = str(alt)
        if _YOLO_MODEL is not None and _YOLO_WEIGHTS_CARGADOS == weights:
            return _YOLO_MODEL
        _YOLO_MODEL = YOLO(weights)
        _YOLO_WEIGHTS_CARGADOS = weights
        return _YOLO_MODEL
    except Exception:
        return None


def _detectar_yolo(bgr: np.ndarray) -> list[ROI]:
    """YOLO tipo industria (Ultralytics YOLOv8/v9 si está instalado)."""
    model = _obtener_yolo()
    if model is None:
        return []
    try:
        import settings as st

        conf = float(getattr(st, "VDCP_YOLO_CONF", 0.25))
        results = model.predict(bgr, verbose=False, conf=conf)
    except Exception:
        return []

    # Clases COCO relevantes para escena / lectura
    mapa = {
        0: "rostro",  # person → zona de interés facial/cuerpo
        73: "documento",  # book
        74: "documento",  # book alt
        39: "objeto",  # bottle etc — genérico
        67: "objeto",  # cell phone
        62: "objeto",  # tv
        63: "cartel",  # laptop as screen/sign proxy
    }
    h, w = bgr.shape[:2]
    out: list[ROI] = []
    for ri, res in enumerate(results or []):
        boxes = getattr(res, "boxes", None)
        if boxes is None:
            continue
        for j, box in enumerate(boxes):
            cls_id = int(box.cls[0]) if box.cls is not None else -1
            conf_v = float(box.conf[0]) if box.conf is not None else 0.5
            xyxy = box.xyxy[0].tolist()
            x1, y1, x2, y2 = [int(v) for v in xyxy]
            bw, bh = max(1, x2 - x1), max(1, y2 - y1)
            tipo = mapa.get(cls_id, "objeto")
            if cls_id == 0:
                # Persona: fovear rostro superior
                bh2 = max(1, int(bh * 0.35))
                tipo = "rostro"
                bh = bh2
            out.append(
                ROI(
                    id=f"yolo_{ri}_{j}",
                    tipo=tipo,
                    bbox=(x1, y1, bw, bh),
                    confianza=conf_v,
                    escala=_clasificar_escala(h, bh),
                    motor="yolo",
                    meta={"cls": cls_id, "weights": _YOLO_WEIGHTS_CARGADOS},
                )
            )
    return out


def _detectar_bandas_proyeccion(bgr: np.ndarray) -> list[ROI]:
    """Segmenta líneas de texto por proyección horizontal (libros / documentos)."""
    import cv2

    h, w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    # Texto oscuro sobre claro
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # Suavizar verticalmente poco, horizontal para unir letras
    bw = cv2.morphologyEx(
        bw, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    )
    proy = np.sum(bw > 0, axis=1)
    umbral = max(8, int(w * 0.015))
    regiones: list[tuple[int, int]] = []
    en = False
    y0 = 0
    for y, v in enumerate(proy):
        if v >= umbral and not en:
            en = True
            y0 = y
        elif v < umbral and en:
            en = False
            if y - y0 >= 6:
                regiones.append((y0, y))
    if en and h - y0 >= 6:
        regiones.append((y0, h - 1))

    # Fusionar líneas muy cercanas
    fusion: list[tuple[int, int]] = []
    for a, b in regiones:
        if fusion and a - fusion[-1][1] < 8:
            fusion[-1] = (fusion[-1][0], b)
        else:
            fusion.append((a, b))

    out: list[ROI] = []
    for i, (ya, yb) in enumerate(fusion):
        strip = bw[ya:yb, :]
        cols = np.sum(strip > 0, axis=0)
        xs = np.where(cols > 0)[0]
        if xs.size == 0:
            continue
        x0, x1 = int(xs[0]), int(xs[-1])
        bw_box, bh = max(1, x1 - x0 + 1), max(1, yb - ya)
        # Margen lateral
        pad = 4
        x0 = max(0, x0 - pad)
        ya2 = max(0, ya - 2)
        bw_box = min(w - x0, bw_box + 2 * pad)
        bh = min(h - ya2, bh + 4)
        escala = _clasificar_escala(h, bh)
        tipo = "senal" if escala == "grande" else "texto"
        dens = float(np.count_nonzero(strip)) / max(strip.size, 1)
        conf = min(0.95, 0.55 + dens)
        out.append(
            ROI(
                id=f"line_{i}",
                tipo=tipo,
                bbox=(x0, ya2, bw_box, bh),
                confianza=round(conf, 4),
                escala=escala,
                motor="proyeccion_h",
                meta={"linea": i},
            )
        )
    return out


def _detectar_texto_opencv(bgr: np.ndarray) -> list[ROI]:
    """Detector angular de bloques de texto (MSER + morfología) — prioriza legibilidad."""
    import cv2

    h, w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    # Contraste local para textos claros/oscuros
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    g = clahe.apply(gray)
    # Gradientes / bordes de caracteres
    blur = cv2.GaussianBlur(g, (3, 3), 0)
    edges = cv2.Canny(blur, 40, 140)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
    linked = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    linked = cv2.dilate(linked, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 2)), iterations=1)
    cnts, _ = cv2.findContours(linked, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rois: list[ROI] = []
    min_area = max(80, int(w * h * 0.00015))
    for i, c in enumerate(cnts):
        x, y, bw, bh = cv2.boundingRect(c)
        area = bw * bh
        if area < min_area:
            continue
        if bw < 12 or bh < 8:
            continue
        aspect = bw / max(bh, 1)
        # Filtrar ruido no textual
        if aspect < 0.8 and bh < h * 0.08:
            continue
        if bw > w * 0.98 and bh > h * 0.9:
            continue  # casi frame completo
        # Puntuación por densidad de bordes (caracteres)
        crop = edges[y : y + bh, x : x + bw]
        dens = float(np.count_nonzero(crop)) / max(area, 1)
        if dens < 0.02:
            continue
        conf = min(0.97, 0.45 + dens * 2.5 + min(aspect, 8) * 0.02)
        escala = _clasificar_escala(h, bh)
        tipo = "texto"
        if escala == "grande" and aspect > 2.5:
            tipo = "senal"
        elif aspect > 4 and bh < h * 0.06:
            tipo = "texto"  # línea / pie de página
        rois.append(
            ROI(
                id=f"txt_{i}",
                tipo=tipo,
                bbox=(x, y, bw, bh),
                confianza=round(conf, 4),
                escala=escala,
                motor="opencv_mser_like",
                meta={"densidad_bordes": round(dens, 4), "aspecto": round(aspect, 2)},
            )
        )
    return rois


def _detectar_rostros(bgr: np.ndarray) -> list[ROI]:
    import cv2

    h, _w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    try:
        face = cv2.CascadeClassifier(cascade_path)
        dets = face.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))
    except Exception:
        return []
    out: list[ROI] = []
    for i, (x, y, bw, bh) in enumerate(dets):
        out.append(
            ROI(
                id=f"face_{i}",
                tipo="rostro",
                bbox=(int(x), int(y), int(bw), int(bh)),
                confianza=0.72,
                escala=_clasificar_escala(h, int(bh)),
                motor="haar",
            )
        )
    return out


def _detectar_documento(bgr: np.ndarray) -> list[ROI]:
    """Página / cartel rectangular grande (libro abierto)."""
    import cv2

    h, w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out: list[ROI] = []
    for i, c in enumerate(cnts):
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) != 4:
            continue
        x, y, bw, bh = cv2.boundingRect(approx)
        if bw * bh < w * h * 0.15:
            continue
        out.append(
            ROI(
                id=f"doc_{i}",
                tipo="documento",
                bbox=(x, y, bw, bh),
                confianza=0.8,
                escala="grande",
                motor="quad",
            )
        )
    return out


def adquisicion_global(bgr: np.ndarray, max_rois: int = 24) -> dict[str, Any]:
    """Gran angular: YOLO (si hay) + OpenCV texto/rostros/documentos."""
    import cv2

    h, w = bgr.shape[:2]
    rois: list[ROI] = []
    motores: list[str] = []

    yolo = _detectar_yolo(bgr)
    if yolo:
        rois.extend(yolo)
        motores.append("yolo")
    bandas = _detectar_bandas_proyeccion(bgr)
    rois.extend(bandas)
    if bandas:
        motores.append("proyeccion_h")
    txt = _detectar_texto_opencv(bgr)
    rois.extend(txt)
    motores.append("opencv_texto")
    rois.extend(_detectar_rostros(bgr))
    motores.append("haar")
    docs = _detectar_documento(bgr)
    rois.extend(docs)
    if docs:
        motores.append("documento")

    # Priorizar legibilidad: boost a ROIs de texto/señal
    for r in rois:
        if r.tipo in ("texto", "senal", "documento"):
            r.confianza = min(0.99, r.confianza + 0.05)

    rois = _nms(rois)
    # Orden: texto micro primero en cola de foveación tras señales grandes
    rois.sort(
        key=lambda r: (
            0 if r.tipo in ("senal", "documento") else 1 if r.tipo == "texto" else 2,
            -r.confianza,
            r.bbox[2] * r.bbox[3],
        )
    )
    rois = rois[:max_rois]

    # Miniatura angular (baja res solo para contexto, no para OCR)
    thumb = cv2.resize(bgr, (min(640, w), max(1, int(h * min(640, w) / w))))
    return {
        "ancho": w,
        "alto": h,
        "motores": motores,
        "rois": [r.to_dict() for r in rois],
        "n_rois": len(rois),
        "thumb_shape": list(thumb.shape),
    }
