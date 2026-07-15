"""
Bus de eventos interno — desacopla componentes sin infraestructura externa.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable

from cognicion.registro import evento, obtener_logger

_log = obtener_logger("nucleo.eventos")
Suscriptor = Callable[[str, dict[str, Any]], None]


@dataclass
class EventoRegistrado:
    nombre: str
    payload: dict[str, Any]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class BusEventos:
    """Pub/sub síncrono en memoria."""

    def __init__(self, historial_max: int = 200) -> None:
        self._suscriptores: dict[str, list[Suscriptor]] = defaultdict(list)
        self._historial: list[EventoRegistrado] = []
        self._historial_max = historial_max
        self._lock = RLock()

    def suscribir(self, evento_nombre: str, callback: Suscriptor) -> None:
        with self._lock:
            self._suscriptores[evento_nombre].append(callback)

    def emitir(self, evento_nombre: str, **payload: Any) -> None:
        registro = EventoRegistrado(nombre=evento_nombre, payload=payload)
        with self._lock:
            self._historial.append(registro)
            if len(self._historial) > self._historial_max:
                self._historial = self._historial[-self._historial_max :]
            callbacks = list(self._suscriptores.get(evento_nombre, []))
            callbacks.extend(self._suscriptores.get("*", []))

        evento(_log, evento_nombre, **{k: v for k, v in payload.items() if k != "accion"}, **({"accion_seg": payload["accion"]} if "accion" in payload else {}))
        for callback in callbacks:
            try:
                callback(evento_nombre, payload)
            except Exception as exc:
                evento(_log, "evento_callback_error", evento=evento_nombre, error=type(exc).__name__)

    def ultimos(self, limite: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            items = self._historial[-limite:]
        return [
            {"nombre": e.nombre, "payload": e.payload, "timestamp": e.timestamp}
            for e in items
        ]

    def contadores(self) -> dict[str, int]:
        with self._lock:
            counts: dict[str, int] = defaultdict(int)
            for e in self._historial:
                counts[e.nombre] += 1
        return dict(counts)
