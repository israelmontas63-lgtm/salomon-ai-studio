# -*- coding: utf-8 -*-
"""
Registro formal de las 7 Capas de Inteligencia de Salomón AI.
Conecta módulos existentes sin duplicar lógica.
Capa 7 sella la metacognición (evaluación pre-emisión) sin interferir con L3/L6.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

from typing import Any


LAYER_CATALOG: list[dict[str, Any]] = [
    {
        "id": 1,
        "name": "perception_multimodal",
        "title": "Layer 1: Multimodal Perception & Vision",
        "assets": [
            "static/js/camera_logic.js",
            "static/js/vision_engine.js",
            "static/js/vision_mode_trigger.js",
            "static/js/components/SmartButton.js",
            "core/brain_connector/bridge.py",
            "cognicion/core_vision_engine.py",
        ],
        "apis": ["/api/vision/brain-bridge", "/api/ai/central-button"],
    },
    {
        "id": 2,
        "name": "persistent_memory",
        "title": "Layer 2: Persistent Memory & Chat History Drawer",
        "assets": [
            "persistencia/sesiones.py",
            "cognicion/memoria/memory_controller.py",
            "cognicion/capas_inteligencia/layer_02_memory/__init__.py",
            "static/js/chat_history_drawer.js",
            "static/css/chat_history_drawer.css",
        ],
        "apis": ["/api/chats", "/api/historial", "/api/chat"],
        "boundaries": {
            "source_of_truth": "sqlite_wal",
            "session_id": "str | None (cemented)",
            "fallback": "ram_cache_per_session",
            "must_not": ["getUserMedia", "closeCamera", "deploy_agent_swarm"],
        },
    },
    {
        "id": 3,
        "name": "logic_reasoning",
        "title": "Layer 3: Logic Reasoning & Step-by-Step Verification",
        "assets": [
            "cognicion/core_salomon_master_neural_engine.py",
            "cognicion/core_master_strict_audit_and_deploy.py",
            "cognicion/orquesta/agentes_paralelos.py",
            "cognicion/capas_inteligencia/layer_03_reasoning/__init__.py",
            "cognicion/orquestador.py",
            "core/cortex/logic_engine.py",
        ],
        "apis": ["/api/neural/master", "/api/deploy/strict-audit"],
        "boundaries": {
            "owns": "logical_swarm_consensus_and_cascade",
            "must_not": ["getUserMedia", "closeCamera", "apply_supervision"],
        },
    },
    {
        "id": 4,
        "name": "nlp_voice",
        "title": "Layer 4: Natural Language & Fluid Speech Processing",
        "assets": [
            "cerebro.py",
            "cognicion/llm.py",
            "cognicion/voz/cartesia_tts.py",
            "static/js/voice_layer.js",
            "static/js/components/SmartButton.js",
            "static/js/script.js",
        ],
        "apis": ["/api/chat", "/api/tts", "/api/stt"],
    },
    {
        "id": 5,
        "name": "pwa_ui_automation",
        "title": "Layer 5: PWA Automation & UI Hot-Loader",
        "assets": [
            "static/js/update_manager.js",
            "static/js/realtime_notification_badge.js",
            "static/js/settings_manager.js",
            "static/js/service-worker.js",
            "static/js/pwa-register.js",
            "static/css/boton.css",
        ],
        "apis": ["/api/version", "/api/deploy/stream"],
    },
    {
        "id": 6,
        "name": "autonomy_verification_swarm",
        "title": "Layer 6: Autonomous Background Tasks & Parallel Verification Swarm",
        "assets": [
            "cognicion/capas_inteligencia/layer_06_autonomy/__init__.py",
            "cognicion/cola.py",
            "cognicion/core_salomon_master_neural_engine.py",
            "cognicion/orquesta/agentes_paralelos.py",
            "cognicion/orquestador.py",
        ],
        "apis": ["/api/intelligence/layers", "/api/neural/master"],
    },
    {
        "id": 7,
        "name": "metacognition_supervision",
        "title": "Layer 7: Metacognition & Pre-Emit Supervision",
        "assets": [
            "cognicion/capas_inteligencia/layer_07_metacognition/__init__.py",
            "cognicion/capas_inteligencia/neural_core_bridge.py",
            "cerebro.py",
            "cognicion/salida_limpia.py",
        ],
        "apis": ["/api/intelligence/layers"],
        "boundaries": {
            "owns": "post_llm_draft_scoring_and_emit_gate",
            "must_not": [
                "deploy_agent_swarm",
                "schedule_background_verification",
                "enrich_turn",
            ],
        },
    },
]


def catalog() -> list[dict[str, Any]]:
    return [dict(x) for x in LAYER_CATALOG]


def layer_by_id(layer_id: int) -> dict[str, Any] | None:
    for layer in LAYER_CATALOG:
        if layer["id"] == layer_id:
            return dict(layer)
    return None
