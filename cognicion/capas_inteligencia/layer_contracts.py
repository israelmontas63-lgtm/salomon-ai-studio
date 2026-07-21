# -*- coding: utf-8 -*-
"""
Contratos estrictos entre las 7 capas — aislamiento neuronal (cero efecto dominó).
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

# Cada capa solo puede poseer estos símbolos; no puede tocar los forbidden de otras.
LAYER_CONTRACTS: list[dict[str, Any]] = [
    {
        "id": 1,
        "name": "perception_multimodal",
        "owns": [
            "static/js/camera_logic.js",
            "static/js/vision_engine.js",
            "views/capture/__init__.py",
        ],
        "must_not_contain": {
            # Visión no escribe SQLite ni borra sesiones
            "static/js/vision_engine.js": [
                "DELETE FROM mensajes",
                "DROP TABLE",
                "sesiones.db",
            ],
            "static/js/camera_logic.js": [
                "DELETE FROM mensajes",
                "guardar_mensaje(",
            ],
        },
        "must_contain": {
            "static/js/vision_engine.js": [
                "analyticalStreaming",
                "standby",
                "engageAnalyticalStreaming",
                "disengageVisualMode",
            ],
        },
    },
    {
        "id": 2,
        "name": "persistent_memory",
        "owns": [
            "persistencia/sesiones.py",
            "cognicion/memoria/memory_controller.py",
            "cognicion/capas_inteligencia/layer_02_memory/__init__.py",
        ],
        "must_contain": {
            "persistencia/sesiones.py": [
                "guardar_mensaje",
                "cargar_mensajes",
                "journal_mode=WAL",
                "BEGIN IMMEDIATE",
                "cement_session_id",
            ],
            "cognicion/capas_inteligencia/layer_02_memory/__init__.py": [
                "cache_push_message",
                "load_messages",
                "save_message",
                "verify_sqlite_wal",
            ],
            "app.py": [
                "cargar_mensajes",
                "SQLite = fuente de verdad",
            ],
        },
        "must_not_contain": {
            # Memoria no controla hardware de cámara
            "persistencia/sesiones.py": [
                "getUserMedia",
                "closeCamera",
                "elevenlabs",
            ],
        },
    },
    {
        "id": 4,
        "name": "nlp_voice",
        "owns": [
            "static/js/voice_layer.js",
            "config/providers.py",
        ],
        "must_contain": {
            "static/js/voice_layer.js": ["playBase64", "SalomonVoiceLayer"],
            "settings.py": ["ELEVENLABS_VOICE_ADAM", "ELEVENLABS_VOICE_ID"],
            "cognicion/capas_inteligencia/synaptic_bus.py": [
                "voice_triggered_vision",
                "AUTHORIZED_SYNAPSES",
            ],
        },
        "must_not_contain": {
            # Voz no toca esquema SQLite
            "static/js/voice_layer.js": [
                "DELETE FROM",
                "sesiones.db",
                "guardar_mensaje",
            ],
        },
    },
    {
        "id": 3,
        "name": "logic_reasoning",
        "owns": [
            "cognicion/orquestador.py",
            "cognicion/core_salomon_master_neural_engine.py",
            "cognicion/capas_inteligencia/layer_03_reasoning/__init__.py",
            "cognicion/orquesta/agentes_paralelos.py",
        ],
        "must_contain": {
            "cognicion/orquestador.py": ["if imagen_base64:", "enrich_turn", "cascade_reason"],
            "cognicion/capas_inteligencia/layer_03_reasoning/__init__.py": [
                "run_logical_swarm",
                "ConsensusMatrix",
                "cascade_reason",
            ],
        },
        "must_not_contain": {
            # Razonamiento no cierra la cámara del cliente
            "cognicion/orquestador.py": ["closeCamera(", "getUserMedia"],
            "cognicion/capas_inteligencia/layer_03_reasoning/__init__.py": [
                "closeCamera(",
                "getUserMedia(",
                "apply_supervision(",
            ],
        },
    },
    {
        "id": 7,
        "name": "metacognition_supervision",
        "owns": [
            "cognicion/capas_inteligencia/layer_07_metacognition/__init__.py",
        ],
        "must_not_contain": {
            "cognicion/capas_inteligencia/layer_07_metacognition/__init__.py": [
                "deploy_agent_swarm(",
                "schedule_background_verification(",
                "enrich_turn(",
            ],
        },
    },
]


def _read(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def verify_contracts() -> dict[str, Any]:
    """Valida contratos. Si falla → bloquear despliegue."""
    findings: list[dict[str, Any]] = []
    ok = True

    for layer in LAYER_CONTRACTS:
        for rel, needles in (layer.get("must_contain") or {}).items():
            body = _read(rel)
            for needle in needles:
                passed = needle in body
                findings.append(
                    {
                        "layer": layer["id"],
                        "kind": "must_contain",
                        "file": rel,
                        "needle": needle,
                        "ok": passed,
                    }
                )
                if not passed:
                    ok = False

        for rel, forbidden in (layer.get("must_not_contain") or {}).items():
            body = _read(rel)
            for needle in forbidden:
                # Violación si aparece como llamada/SQL real
                passed = needle not in body
                findings.append(
                    {
                        "layer": layer["id"],
                        "kind": "must_not_contain",
                        "file": rel,
                        "needle": needle,
                        "ok": passed,
                    }
                )
                if not passed:
                    ok = False

    # Puente session_id: cliente debe sincronizar
    lock = _read("static/js/ai_state_lock.js")
    drawer = _read("static/js/chat_history_drawer.js")
    session_ok = "setSessionId" in lock and "setSessionId" in drawer
    findings.append(
        {
            "layer": 2,
            "kind": "session_sync",
            "file": "ai_state_lock+drawer",
            "needle": "setSessionId",
            "ok": session_ok,
        }
    )
    if not session_ok:
        ok = False

    return {
        "ok": ok,
        "blocked": not ok,
        "findings": findings,
        "via": "layer_contracts",
    }
