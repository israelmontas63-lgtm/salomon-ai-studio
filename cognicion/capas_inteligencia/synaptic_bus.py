# -*- coding: utf-8 -*-
"""
Bus sináptico — únicos canales autorizados entre capas.
Ninguna capa puede mutar estado nativo de otra fuera de estos contratos.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

from typing import Any

# Sinapsis autorizadas: (origen, destino, canal, contrato)
AUTHORIZED_SYNAPSES: list[dict[str, Any]] = [
    {
        "from": 4,
        "to": 1,
        "channel": "voice_triggered_vision",
        "methods": [
            "engageAnalyticalStreaming",
            "disengageVisualMode",
            "lookNow",
        ],
        "payload": {"mensaje": str, "session_id": (str, type(None))},
    },
    {
        "from": 1,
        "to": 3,
        "channel": "vision_context_block",
        "methods": ["analizar_imagen"],
        "payload": {"imagen_base64": str, "imagen_mime": str},
        "note": "Solo texto de análisis entra al razonamiento; no escribe SQLite.",
    },
    {
        "from": 4,
        "to": 2,
        "channel": "persist_turn",
        "methods": ["guardar_mensaje", "_persistir_turno"],
        "payload": {"session_id": str, "rol": str, "contenido": str},
    },
    {
        "from": 2,
        "to": 3,
        "channel": "memory_immediate",
        "methods": ["memoria_inmediata", "ultimos_mensajes"],
        "payload": {"session_id": str, "limite": int},
    },
    {
        "from": 3,
        "to": 7,
        "channel": "draft_for_supervision",
        "methods": ["apply_supervision"],
        "payload": {"draft": str, "user_message": str},
    },
    {
        "from": 7,
        "to": 4,
        "channel": "emit_sanitized",
        "methods": ["sanitizar_salida_chat"],
        "payload": {"texto": str},
    },
    {
        "from": 8,
        "to": 3,
        "channel": "supervisor_web_intelligence",
        "methods": ["supervise_turn", "fetch_web_intelligence"],
        "payload": {"mensaje": str, "session_id": (str, type(None))},
        "note": "Supervisor inyecta bloque web; no escribe SQLite ni cierra camara.",
    },
]


def cement_session_id(value: Any) -> str | None:
    """Cemento: session_id solo str no vacío o None."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("session_id debe ser str|None")
    sid = value.strip()
    return sid or None


def cement_imagen_payload(
    imagen_base64: Any,
    imagen_mime: Any = "image/jpeg",
) -> dict[str, Any]:
    """Cemento: payload visual tipado antes de cruzar a Capa 1/3."""
    if imagen_base64 is None:
        return {"ok": False, "imagen_base64": None, "imagen_mime": None}
    if not isinstance(imagen_base64, str):
        raise TypeError("imagen_base64 debe ser str")
    raw = imagen_base64.strip()
    mime = imagen_mime if isinstance(imagen_mime, str) and imagen_mime else "image/jpeg"
    if not raw:
        return {"ok": False, "imagen_base64": None, "imagen_mime": mime}
    return {"ok": True, "imagen_base64": raw, "imagen_mime": mime}


def cement_turn_roles(rol: Any) -> str:
    if rol not in ("usuario", "asistente"):
        raise ValueError("rol inválido para persistencia")
    return rol


def list_synapses() -> list[dict[str, Any]]:
    return [dict(s) for s in AUTHORIZED_SYNAPSES]


def synapse_allowed(from_layer: int, to_layer: int, channel: str) -> bool:
    for s in AUTHORIZED_SYNAPSES:
        if (
            s["from"] == from_layer
            and s["to"] == to_layer
            and s["channel"] == channel
        ):
            return True
    return False
