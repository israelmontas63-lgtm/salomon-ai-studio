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
        "methods": ["guardar_mensaje", "_persistir_turno", "save_message"],
        "payload": {"session_id": (str, type(None)), "rol": str, "contenido": str},
        "module": "cognicion/capas_inteligencia/layer_02_memory/__init__.py",
        "note": "session_id tipado str|None; SQLite WAL es fuente de verdad.",
    },
    {
        "from": 2,
        "to": 3,
        "channel": "memory_immediate",
        "methods": ["memoria_inmediata", "ultimos_mensajes", "load_recent"],
        "payload": {"session_id": (str, type(None)), "limite": int},
        "module": "cognicion/capas_inteligencia/layer_02_memory/__init__.py",
    },
    {
        "from": 2,
        "to": 2,
        "channel": "history_ram_fallback",
        "methods": ["cache_load_messages", "load_messages", "cache_push_message"],
        "payload": {"session_id": (str, type(None))},
        "note": "Recuperación RAM si SQLite falla o latencia alta; sin cruce de chats.",
    },
    {
        "from": 3,
        "to": 3,
        "channel": "logical_swarm_consensus",
        "methods": ["run_logical_swarm", "cascade_reason", "ConsensusMatrix"],
        "payload": {"premise": str, "session_id": (str, type(None))},
        "module": "cognicion/capas_inteligencia/layer_03_reasoning/__init__.py",
        "note": (
            "Enjambre lógico ligero + matriz de consenso por pesos. "
            "Fail-soft por nodo; no cierra cámara ni llama apply_supervision."
        ),
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
        "from": 7,
        "to": 8,
        "channel": "draft_for_asalomon",
        "methods": ["apply_asalomon_seal"],
        "payload": {"draft": str, "user_message": str},
        "module": "cognicion/capas_inteligencia/layer_08_asalomon/__init__.py",
        "note": (
            "L7 entrega borrador supervisado a Asalomón (metaconocimiento + identidad). "
            "L8 no re-lanza enjambres ni escribe SQLite."
        ),
    },
    {
        "from": 8,
        "to": 4,
        "channel": "emit_asalomon_sealed",
        "methods": ["sanitizar_salida_chat", "apply_asalomon_seal"],
        "payload": {"texto": str},
        "note": "Salida con sello de identidad Asalomón hacia NLP/voz.",
    },
    {
        "from": 7,
        "to": 7,
        "channel": "law_of_one_lens",
        "methods": [
            "apply_unity_lens",
            "evaluate_axiological_alignment",
            "apply_law_of_one_gate",
        ],
        "payload": {"response_draft": str, "user_message": str},
        "module": "cognicion/law_of_one.py",
        "note": (
            "Filtro axiologico Ley del Uno: unidad, servicio y libre albedrío. "
            "Se aplica en L7 antes de Asalomón; no escribe SQLite ni lanza enjambres."
        ),
    },
    {
        "from": 8,
        "to": 8,
        "channel": "asalomon_reasoning_forms",
        "methods": [
            "detect_reasoning_forms",
            "enrich_reasoning_hint",
            "bloque_metaconocimiento",
        ],
        "payload": {"user_message": str},
        "module": "cognicion/capas_inteligencia/layer_08_asalomon/__init__.py",
        "note": "Metaconocimiento interno: formas de razonamiento sin mutar otras capas.",
    },
    {
        "from": 0,
        "to": 3,
        "channel": "lib_support_tools",
        "methods": [
            "ejecutar_herramienta",
            "listar_herramientas",
            "consultar_clima",
            "buscar_web",
            "systemguard_verify",
            "emitir_capacidad",
        ],
        "payload": {"nombre": str, "args": dict},
        "module": "lib/neural_bridge.py",
        "note": (
            "Capa 0 = librerías internas (lib/). Soporte → razonamiento "
            "sin tocar UI ni SalomonVisionArchitecture."
        ),
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


def cement_law_of_one_payload(
    response_draft: Any,
    user_message: Any = "",
) -> dict[str, Any]:
    """Cemento tipado antes de cruzar el canal law_of_one_lens."""
    if response_draft is not None and not isinstance(response_draft, (str, bytes)):
        raise TypeError("response_draft debe ser str|bytes|None")
    if user_message is not None and not isinstance(user_message, (str, bytes)):
        raise TypeError("user_message debe ser str|bytes|None")
    draft = "" if response_draft is None else response_draft
    user = "" if user_message is None else user_message
    if isinstance(draft, bytes):
        draft = draft.decode("utf-8", errors="replace")
    if isinstance(user, bytes):
        user = user.decode("utf-8", errors="replace")
    return {
        "ok": True,
        "response_draft": draft,
        "user_message": user,
    }


def cross_law_of_one(
    response_draft: Any,
    *,
    user_message: Any = "",
) -> tuple[str, dict[str, Any]]:
    """
    Cruce autorizado L7→axioma (canal law_of_one_lens).
    Valida payload y aplica la puerta; fail-soft ante errores.
    """
    if not synapse_allowed(7, 7, "law_of_one_lens"):
        return str(response_draft or ""), {
            "ok": False,
            "error": "synapse_not_authorized",
            "via": "synaptic_bus",
        }
    try:
        pack = cement_law_of_one_payload(response_draft, user_message)
        from cognicion.law_of_one import apply_law_of_one_gate

        return apply_law_of_one_gate(
            pack["response_draft"],
            user_message=pack["user_message"],
        )
    except Exception as exc:
        return str(response_draft or ""), {
            "ok": False,
            "error": type(exc).__name__,
            "fail_soft": True,
            "via": "synaptic_bus.cross_law_of_one",
        }


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
