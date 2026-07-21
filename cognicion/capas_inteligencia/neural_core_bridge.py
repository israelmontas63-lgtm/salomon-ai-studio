# -*- coding: utf-8 -*-
"""
Puente neuronal: mapeo estricto de las 7 capas al núcleo cognitivo.
Sella fronteras para evitar choques de conocimiento entre módulos.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

# Orden estricto de armonización → núcleo (cerebro / MotorCognicion)
NEURAL_CORE_MAP: list[dict[str, Any]] = [
    {
        "id": 1,
        "name": "perception_multimodal",
        "core_hooks": [
            "static/js/camera_logic.js",
            "static/js/vision_engine.js",
            "core/brain_connector/bridge.py",
        ],
        "bridge_markers": ["getUserMedia", "setZoom", "autoFocusFromText"],
        "must_not_own": ["apply_supervision", "schedule_background_verification"],
    },
    {
        "id": 2,
        "name": "persistent_memory",
        "core_hooks": [
            "persistencia/sesiones.py",
            "cognicion/memoria/memory_controller.py",
            "cognicion/capas_inteligencia/layer_02_memory/__init__.py",
            "static/js/chat_history_drawer.js",
        ],
        "bridge_markers": [
            "listar_sesiones",
            "MemoryController",
            "/api/chats",
            "journal_mode=WAL",
            "cache_push_message",
        ],
        "must_not_own": ["apply_supervision", "deploy_agent_swarm", "getUserMedia"],
    },
    {
        "id": 3,
        "name": "logic_reasoning",
        "core_hooks": [
            "cognicion/core_salomon_master_neural_engine.py",
            "cognicion/orquesta/agentes_paralelos.py",
            "cognicion/capas_inteligencia/layer_03_reasoning/__init__.py",
            "cognicion/orquestador.py",
        ],
        "bridge_markers": [
            "enrich_turn",
            "deploy_agent_swarm",
            "run_logical_swarm",
            "ConsensusMatrix",
            "cascade_reason",
        ],
        "must_not_own": ["apply_supervision", "getUserMedia", "closeCamera"],
    },
    {
        "id": 4,
        "name": "nlp_voice",
        "core_hooks": [
            "cerebro.py",
            "cognicion/llm.py",
            "static/js/voice_layer.js",
        ],
        "bridge_markers": ["procesar_entrada", "SalomonVoiceLayer"],
        "must_not_own": ["schedule_background_verification"],
    },
    {
        "id": 5,
        "name": "pwa_ui_automation",
        "core_hooks": [
            "static/js/update_manager.js",
            "static/js/realtime_notification_badge.js",
            "static/js/service-worker.js",
        ],
        "bridge_markers": ["version.json", "SalomonDeployBadge", "skipWaiting"],
        "must_not_own": ["apply_supervision", "enrich_turn"],
    },
    {
        "id": 6,
        "name": "autonomy_verification_swarm",
        "core_hooks": [
            "cognicion/capas_inteligencia/layer_06_autonomy/__init__.py",
            "cognicion/cola.py",
            "cognicion/orquestador.py",
        ],
        "bridge_markers": [
            "schedule_background_verification",
            "layer_06",
        ],
        "must_not_own": ["apply_supervision"],
    },
    {
        "id": 7,
        "name": "metacognition_supervision",
        "core_hooks": [
            "cognicion/capas_inteligencia/layer_07_metacognition/__init__.py",
            "cognicion/law_of_one.py",
            "cerebro.py",
            "cognicion/salida_limpia.py",
        ],
        "bridge_markers": [
            "apply_supervision",
            "self_reflection_loop",
            "CALIBRATION",
            "apply_unity_lens",
            "cross_law_of_one",
        ],
        "must_not_own": [
            "deploy_agent_swarm(",
            "schedule_background_verification(",
            "enrich_turn(",
        ],
    },
]


def _exists(rel: str) -> bool:
    return (ROOT / rel).is_file()


def _read(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def verify_layer_bridge(layer: dict[str, Any]) -> dict[str, Any]:
    lid = layer["id"]
    hooks_ok = all(_exists(h) for h in layer["core_hooks"])
    # Al menos un marcador presente en el núcleo / hooks
    joined = "\n".join(_read(h) for h in layer["core_hooks"])
    # También mirar cerebro + orquestador como núcleo
    joined += "\n" + _read("cerebro.py") + "\n" + _read("cognicion/orquestador.py")
    markers = layer.get("bridge_markers") or []
    markers_ok = all(m in joined for m in markers) if markers else True

    collision = False
    for forbidden in layer.get("must_not_own") or []:
        # Solo en el módulo principal de la capa (primer hook tipicamente)
        primary = layer["core_hooks"][0]
        body = _read(primary)
        if forbidden in body and lid != 7:
            # Capas 1-6 no deben poseer la puerta L7
            if forbidden in ("apply_supervision",) and "layer_07" not in primary:
                collision = True
        if lid == 7 and forbidden in body:
            collision = True

    ok = hooks_ok and markers_ok and not collision
    return {
        "id": lid,
        "name": layer["name"],
        "ok": ok,
        "hooks_ok": hooks_ok,
        "markers_ok": markers_ok,
        "collision": collision,
    }


def harmonize_all_layers() -> dict[str, Any]:
    """Verifica conexión en orden estricto 1→7 al núcleo."""
    results = [verify_layer_bridge(layer) for layer in NEURAL_CORE_MAP]
    # Puente L4↔L7: cerebro debe llamar apply_supervision
    cerebro = _read("cerebro.py")
    l7_in_core = "apply_supervision" in cerebro and "layer_07" in cerebro
    # Puente L3/L6 en orquestador
    orch = _read("cognicion/orquestador.py")
    l3_l6 = "enrich_turn" in orch and "schedule_background_verification" in orch
    sealed = l7_in_core and l3_l6 and all(r["ok"] for r in results)
    return {
        "ok": sealed,
        "order": [r["id"] for r in results],
        "layer_bridges": results,
        "core_links": {
            "cerebro_l7": l7_in_core,
            "orquestador_l3_l6": l3_l6,
        },
        "sealed": sealed,
        "via": "neural_core_bridge",
    }
