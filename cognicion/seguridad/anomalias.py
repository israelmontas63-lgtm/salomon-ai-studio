"""
Detección de anomalías — aprende línea base y alerta desviaciones.
"""

from __future__ import annotations

import statistics
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import RLock

from cognicion.seguridad.tipos import (
    AccionSeguridad,
    AlertaSeguridad,
    EventoSeguridad,
    Severidad,
    TipoAmenaza,
)

_VENTANA_MUESTRAS = 200
_UMBRAL_DESVIACION = 2.5
_MIN_MUESTRAS = 15


@dataclass
class MetricaRuta:
    latencias: deque[float] = field(default_factory=lambda: deque(maxlen=_VENTANA_MUESTRAS))
    errores: deque[int] = field(default_factory=lambda: deque(maxlen=_VENTANA_MUESTRAS))
    contador: int = 0


class DetectorAnomalias:
    """Aprende comportamiento normal por ruta y detecta outliers."""

    def __init__(self) -> None:
        self._metricas: dict[str, MetricaRuta] = defaultdict(MetricaRuta)
        self._alertas: list[AlertaSeguridad] = []
        self._lock = RLock()

    def registrar_observacion(
        self,
        ruta: str,
        duracion_ms: float,
        status: int,
    ) -> AlertaSeguridad | None:
        es_error = status >= 400
        with self._lock:
            m = self._metricas[ruta]
            m.latencias.append(duracion_ms)
            m.errores.append(1 if es_error else 0)
            m.contador += 1

            if m.contador < _MIN_MUESTRAS:
                return None

            alerta = self._evaluar(ruta, m, duracion_ms, es_error)
            if alerta:
                self._alertas.append(alerta)
                if len(self._alertas) > 200:
                    self._alertas = self._alertas[-200:]
            return alerta

    def _evaluar(
        self,
        ruta: str,
        m: MetricaRuta,
        duracion_ms: float,
        es_error: bool,
    ) -> AlertaSeguridad | None:
        latencias = list(m.latencias)
        if len(latencias) < _MIN_MUESTRAS:
            return None

        media = statistics.mean(latencias)
        try:
            desv = statistics.stdev(latencias) or 1.0
        except statistics.StatisticsError:
            desv = 1.0

        z_score = abs(duracion_ms - media) / desv
        tasa_error = sum(m.errores) / len(m.errores)

        anomalia = False
        detalle = ""

        if z_score > _UMBRAL_DESVIACION and duracion_ms > media:
            anomalia = True
            detalle = f"Latencia anómala {duracion_ms:.0f}ms (media {media:.0f}ms, z={z_score:.1f})"
        elif tasa_error > 0.4 and es_error:
            anomalia = True
            detalle = f"Tasa de error elevada en {ruta}: {tasa_error:.0%}"

        if not anomalia:
            return None

        evento = EventoSeguridad(
            tipo=TipoAmenaza.ANOMALIA,
            severidad=Severidad.MEDIA if z_score < 4 else Severidad.ALTA,
            accion=AccionSeguridad.NOTIFICAR,
            detalle=detalle,
            recurso=ruta,
            metadata={"z_score": round(z_score, 2), "tasa_error": round(tasa_error, 2)},
        )
        return AlertaSeguridad(id=str(uuid.uuid4()), evento=evento)

    def linea_base(self) -> dict[str, dict]:
        resultado = {}
        with self._lock:
            for ruta, m in self._metricas.items():
                if len(m.latencias) < 5:
                    continue
                latencias = list(m.latencias)
                resultado[ruta] = {
                    "muestras": m.contador,
                    "latencia_media_ms": round(statistics.mean(latencias), 1),
                    "tasa_error": round(sum(m.errores) / len(m.errores), 3),
                }
        return resultado

    def alertas_activas(self, limite: int = 20) -> list[dict]:
        with self._lock:
            items = [a for a in self._alertas if not a.resuelta][-limite:]
        return [
            {
                "id": a.id,
                "tipo": a.evento.tipo.value,
                "severidad": a.evento.severidad.value,
                "detalle": a.evento.detalle,
                "recurso": a.evento.recurso,
                "timestamp": a.evento.timestamp,
            }
            for a in items
        ]


_detector_anom: DetectorAnomalias | None = None


def obtener_detector_anomalias() -> DetectorAnomalias:
    global _detector_anom
    if _detector_anom is None:
        _detector_anom = DetectorAnomalias()
    return _detector_anom
