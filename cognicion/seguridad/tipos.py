"""Tipos y enumeraciones del motor de ciberseguridad."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RolAcceso(str, Enum):
    ANON = "anon"
    USUARIO = "usuario"
    SERVICIO = "servicio"
    ADMIN = "admin"


class Severidad(str, Enum):
    INFO = "info"
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class TipoAmenaza(str, Enum):
    AUTH_FALLIDA = "auth_fallida"
    RATE_LIMIT = "rate_limit"
    RUTA_SOSPECHOSA = "ruta_sospechosa"
    PATRON_INYECCION = "patron_inyeccion"
    IP_BLOQUEADA = "ip_bloqueada"
    ANOMALIA = "anomalia"
    ACCESO_DENEGADO = "acceso_denegado"


class AccionSeguridad(str, Enum):
    PERMITIR = "permitir"
    LIMITAR = "limitar"
    AISLAR = "aislar"
    BLOQUEAR = "bloquear"
    DEGRADAR = "degradar"
    NOTIFICAR = "notificar"


@dataclass
class Actor:
    rol: RolAcceso
    identificador: str
    ip: str = ""
    user_agent: str = ""


@dataclass
class EventoSeguridad:
    tipo: TipoAmenaza
    severidad: Severidad
    accion: AccionSeguridad
    detalle: str
    actor: Actor | None = None
    recurso: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class AlertaSeguridad:
    id: str
    evento: EventoSeguridad
    resuelta: bool = False
    notificada: bool = False
