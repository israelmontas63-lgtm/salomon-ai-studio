# -*- coding: utf-8 -*-
"""HistoryBuffer — delega en hilos de mente/."""

from __future__ import annotations

from typing import Any

from mente.hilos import cargar_hilo, registrar_turno


class HistoryBuffer:
    @staticmethod
    def recent(session_id: str, n: int = 12) -> list[dict[str, Any]]:
        h = cargar_hilo(session_id)
        return list(h.get("turnos") or [])[-n:]

    @staticmethod
    def push(session_id: str, rol: str, texto: str, area: str = "razonamiento") -> None:
        registrar_turno(session_id, rol=rol, texto=texto, area=area)
