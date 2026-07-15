"""
Detección de intrusiones — rate limit, auth fallida, IPs bloqueadas.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import RLock

from cognicion.seguridad.tipos import (
    AccionSeguridad,
    Actor,
    EventoSeguridad,
    RolAcceso,
    Severidad,
    TipoAmenaza,
)
from cognicion.seguridad.utilidades import contiene_patron_sospechoso, ruta_sensible

_VENTANA_SEG = 60
_MAX_PETICIONES = 120
_MAX_AUTH_FALLIDAS = 8
_BLOQUEO_SEG = 300


@dataclass
class EstadoIP:
    peticiones: list[float] = field(default_factory=list)
    auth_fallidas: int = 0
    bloqueada_hasta: float = 0.0


class DetectorIntrusion:
    """Monitor en memoria — defensa reactiva sin acciones ofensivas."""

    def __init__(self) -> None:
        self._ips: dict[str, EstadoIP] = defaultdict(EstadoIP)
        self._lock = RLock()
        self._eventos: list[EventoSeguridad] = []

    def _limpiar_ventana(self, estado: EstadoIP, ahora: float) -> None:
        estado.peticiones = [t for t in estado.peticiones if ahora - t < _VENTANA_SEG]

    def ip_bloqueada(self, ip: str) -> bool:
        with self._lock:
            estado = self._ips[ip]
            return estado.bloqueada_hasta > time.monotonic()

    def evaluar_peticion(
        self,
        path: str,
        metodo: str,
        ip: str,
        query: str = "",
        body_preview: str = "",
    ) -> EventoSeguridad | None:
        ahora = time.monotonic()
        texto_completo = f"{path}?{query} {body_preview}"

        if ruta_sensible(path):
            return self._registrar(
                TipoAmenaza.RUTA_SOSPECHOSA,
                Severidad.ALTA,
                AccionSeguridad.BLOQUEAR,
                f"Acceso a ruta sensible: {path}",
                ip=ip,
                recurso=path,
            )

        if contiene_patron_sospechoso(texto_completo):
            return self._registrar(
                TipoAmenaza.PATRON_INYECCION,
                Severidad.ALTA,
                AccionSeguridad.BLOQUEAR,
                "Patrón sospechoso detectado",
                ip=ip,
                recurso=path,
            )

        with self._lock:
            estado = self._ips[ip]
            if estado.bloqueada_hasta > ahora:
                return self._registrar(
                    TipoAmenaza.IP_BLOQUEADA,
                    Severidad.MEDIA,
                    AccionSeguridad.BLOQUEAR,
                    "IP temporalmente bloqueada",
                    ip=ip,
                    recurso=path,
                )

            self._limpiar_ventana(estado, ahora)
            estado.peticiones.append(ahora)

            if len(estado.peticiones) > _MAX_PETICIONES:
                estado.bloqueada_hasta = ahora + _BLOQUEO_SEG
                return self._registrar(
                    TipoAmenaza.RATE_LIMIT,
                    Severidad.MEDIA,
                    AccionSeguridad.LIMITAR,
                    f"Rate limit excedido ({len(estado.peticiones)}/{_MAX_PETICIONES})",
                    ip=ip,
                    recurso=path,
                )

        return None

    def registrar_auth_fallida(self, ip: str, path: str) -> EventoSeguridad:
        ahora = time.monotonic()
        with self._lock:
            estado = self._ips[ip]
            estado.auth_fallidas += 1
            if estado.auth_fallidas >= _MAX_AUTH_FALLIDAS:
                estado.bloqueada_hasta = ahora + _BLOQUEO_SEG
                accion = AccionSeguridad.BLOQUEAR
                severidad = Severidad.ALTA
            else:
                accion = AccionSeguridad.LIMITAR
                severidad = Severidad.MEDIA

        return self._registrar(
            TipoAmenaza.AUTH_FALLIDA,
            severidad,
            accion,
            f"Autenticación fallida ({estado.auth_fallidas})",
            ip=ip,
            recurso=path,
        )

    def _registrar(
        self,
        tipo: TipoAmenaza,
        severidad: Severidad,
        accion: AccionSeguridad,
        detalle: str,
        ip: str = "",
        recurso: str = "",
    ) -> EventoSeguridad:
        evento = EventoSeguridad(
            tipo=tipo,
            severidad=severidad,
            accion=accion,
            detalle=detalle,
            actor=Actor(rol=RolAcceso.ANON, identificador=ip, ip=ip),
            recurso=recurso,
        )
        with self._lock:
            self._eventos.append(evento)
            if len(self._eventos) > 500:
                self._eventos = self._eventos[-500:]
        return evento

    def ultimos_eventos(self, limite: int = 20) -> list[dict]:
        with self._lock:
            items = self._eventos[-limite:]
        return [
            {
                "tipo": e.tipo.value,
                "severidad": e.severidad.value,
                "accion": e.accion.value,
                "detalle": e.detalle,
                "recurso": e.recurso,
                "timestamp": e.timestamp,
                "ip": e.actor.ip if e.actor else "",
            }
            for e in items
        ]

    def ips_bloqueadas(self) -> int:
        ahora = time.monotonic()
        with self._lock:
            return sum(1 for e in self._ips.values() if e.bloqueada_hasta > ahora)


_detector: DetectorIntrusion | None = None


def obtener_detector() -> DetectorIntrusion:
    global _detector
    if _detector is None:
        _detector = DetectorIntrusion()
    return _detector
