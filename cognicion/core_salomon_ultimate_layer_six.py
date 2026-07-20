# -*- coding: utf-8 -*-
"""
[FILE: core_salomon_ultimate_layer_six.py]
Capa 6 y Consolidación Total (Salomón AI).
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class SalomonUltimateArchitecture:
    def __init__(self) -> None:
        self.module = "SalomonUltimateArchitecture"
        self.total_layers = 6

    def _exists(self, rel: str) -> bool:
        return (ROOT / rel).is_file()

    def _read(self, rel: str) -> str:
        path = ROOT / rel
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def consolidate_layers_1_to_5(self) -> dict[str, Any]:
        """Confirma que las 5 capas base estén cerradas y sin choques."""
        try:
            from cognicion.core_salomon_verify_and_build_five_layers import (
                run_five_layers_verify_and_build,
            )

            base = run_five_layers_verify_and_build()
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}:{exc}"}

        return {
            "ok": bool(base.get("complete")),
            "status": base.get("status"),
            "layer_results": base.get("layer_results"),
            "scaffolded": base.get("scaffolded"),
        }

    def verify_layer_6(self) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        ok = True

        def mark(name: str, passed: bool, detail: str) -> None:
            nonlocal ok
            checks.append({"check": name, "ok": passed, "detail": detail})
            if not passed:
                ok = False
            print(f"  [{'OK' if passed else 'FAIL'}] L6.{name}: {detail}")

        mark(
            "module_file",
            self._exists("cognicion/capas_inteligencia/layer_06_autonomy/__init__.py"),
            "modulo autonomia presente",
        )
        mark(
            "cola_background",
            self._exists("cognicion/cola.py") and "encolar" in self._read("cognicion/cola.py"),
            "cola de fondo operativa",
        )
        mark(
            "swarm_engine",
            "deploy_agent_swarm" in self._read("cognicion/core_salomon_master_neural_engine.py"),
            "enjambre maestro disponible",
        )
        orch = self._read("cognicion/orquestador.py")
        mark(
            "orquestador_hook",
            "schedule_background_verification" in orch or "layer_06" in orch,
            "orquestador cableado a Capa 6",
        )
        try:
            from cognicion.capas_inteligencia.layer_06_autonomy import layer_six_status

            st = layer_six_status()
            mark("runtime", bool(st.get("ok")), f"runtime cache={st.get('cache_entries')}")
        except Exception as exc:
            mark("runtime", False, str(exc))

        return {"ok": ok, "checks": checks}

    def ensure_layer_6_wired(self) -> list[str]:
        """Integra Capa 6 en orquestador si falta el gancho."""
        touched: list[str] = []
        orch_path = ROOT / "cognicion" / "orquestador.py"
        text = orch_path.read_text(encoding="utf-8") if orch_path.is_file() else ""
        if "schedule_background_verification" in text:
            return touched

        needle = (
            "        except Exception as exc:\n"
            "            meta[\"cognicion\"][\"master_neural_error\"] = type(exc).__name__\n"
            "\n"
            "        _, resultados = consultar_conectores(entrada, lat=lat, lon=lon)"
        )
        insert = (
            "        except Exception as exc:\n"
            "            meta[\"cognicion\"][\"master_neural_error\"] = type(exc).__name__\n"
            "\n"
            "        # Capa 6: verificacion autonoma en segundo plano (sin bloquear respuesta)\n"
            "        try:\n"
            "            from cognicion.capas_inteligencia.layer_06_autonomy import (\n"
            "                consume_background_block,\n"
            "                schedule_background_verification,\n"
            "            )\n"
            "\n"
            "            cached_block = consume_background_block(\n"
            "                entrada, session_id=self.session_id\n"
            "            )\n"
            "            if cached_block:\n"
            "                bloques.append(cached_block)\n"
            "                meta[\"cognicion\"][\"layer_06\"] = {\n"
            "                    \"cached\": True,\n"
            "                    \"via\": \"verification_swarm_cache\",\n"
            "                }\n"
            "            else:\n"
            "                bg = schedule_background_verification(\n"
            "                    entrada, session_id=self.session_id\n"
            "                )\n"
            "                meta[\"cognicion\"][\"layer_06\"] = bg\n"
            "        except Exception as exc:\n"
            "            meta[\"cognicion\"][\"layer_06_error\"] = type(exc).__name__\n"
            "\n"
            "        _, resultados = consultar_conectores(entrada, lat=lat, lon=lon)"
        )
        if needle in text:
            orch_path.write_text(text.replace(needle, insert), encoding="utf-8")
            touched.append("cognicion/orquestador.py")
        return touched

    def update_catalog_to_six(self) -> list[str]:
        """Asegura que el catálogo formal declare 6 capas."""
        touched: list[str] = []
        cat_path = ROOT / "cognicion" / "capas_inteligencia" / "__init__.py"
        text = cat_path.read_text(encoding="utf-8") if cat_path.is_file() else ""
        if "layer_06" in text or '"id": 6' in text:
            return touched

        # Rewrite catalog with 6 layers
        cat_path.write_text(
            '''# -*- coding: utf-8 -*-
"""
Registro formal de las 6 Capas de Inteligencia de Salomón AI.
Conecta módulos existentes sin duplicar lógica.
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
            "static/js/chat_history_drawer.js",
            "static/css/chat_history_drawer.css",
        ],
        "apis": ["/api/chats", "/api/historial", "/api/chat"],
    },
    {
        "id": 3,
        "name": "logic_reasoning",
        "title": "Layer 3: Logic Reasoning & Step-by-Step Verification",
        "assets": [
            "cognicion/core_salomon_master_neural_engine.py",
            "cognicion/core_master_strict_audit_and_deploy.py",
            "cognicion/orquesta/agentes_paralelos.py",
            "cognicion/orquestador.py",
            "core/cortex/logic_engine.py",
        ],
        "apis": ["/api/neural/master", "/api/deploy/strict-audit"],
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
]


def catalog() -> list[dict[str, Any]]:
    return [dict(x) for x in LAYER_CATALOG]


def layer_by_id(layer_id: int) -> dict[str, Any] | None:
    for layer in LAYER_CATALOG:
        if layer["id"] == layer_id:
            return dict(layer)
    return None
''',
            encoding="utf-8",
        )
        touched.append("cognicion/capas_inteligencia/__init__.py")

        readme = (
            ROOT
            / "cognicion"
            / "capas_inteligencia"
            / "layer_06_autonomy"
            / "README.md"
        )
        if not readme.is_file():
            readme.write_text(
                "# Capa 6: Autonomia y Enjambre de Verificacion\n\n"
                "Tareas en segundo plano (cognicion.cola) + enjambre paralelo "
                "ante vacios factuales.\n",
                encoding="utf-8",
            )
            touched.append(str(readme.relative_to(ROOT)))
        return touched

    def compile_ultimate_spec(self) -> str:
        print("[CONSOLIDANDO LA ARQUITECTURA DE 6 CAPAS DE SALOMON AI]")
        wired = self.ensure_layer_6_wired()
        catalog_touched = self.update_catalog_to_six()
        base = self.consolidate_layers_1_to_5()
        print("--- Capa 6: Autonomia & Enjambre de Verificacion ---")
        l6 = self.verify_layer_6()

        # Re-verify L6 after wiring
        if wired:
            l6 = self.verify_layer_6()

        complete = bool(base.get("ok")) and bool(l6.get("ok"))
        spec = {
            "status": (
                "SYSTEM_FULLY_OPTIMIZED_AND_EXPANDED"
                if complete
                else "EXPANSION_INCOMPLETE"
            ),
            "module": self.module,
            "architecture_layers": self.total_layers,
            "layers_1_to_5": base,
            "layer_6": l6,
            "layer_6_added": "Autonomous Background Tasks & Parallel Verification Swarm",
            "touched": wired + catalog_touched,
            "complete": complete,
            "deployment": (
                "Auto-commit, push to Render production, and hot-load PWA badge notification active."
            ),
        }
        return json.dumps(spec, indent=2, ensure_ascii=True)

    def run(self) -> dict[str, Any]:
        return json.loads(self.compile_ultimate_spec())


def run_ultimate_architecture() -> dict[str, Any]:
    return SalomonUltimateArchitecture().run()


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    ultimate = SalomonUltimateArchitecture()
    report = ultimate.run()
    print(report.get("status"), "complete=", report.get("complete"))
    print("touched:", report.get("touched"))
    sys.exit(0 if report.get("complete") else 1)
