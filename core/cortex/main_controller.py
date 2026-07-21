# -*- coding: utf-8 -*-
"""MainController — fachada Python del kernel (saludo + lock + mente)."""

from __future__ import annotations

from typing import Any


class MainController:
    @staticmethod
    def initializeGreeting(modo: str = "enérgetico") -> dict[str, Any]:
        from mente.protocolo_inicio import protocolo_inicio

        out = protocolo_inicio("kernel-boot")
        out["modo"] = modo
        return out

    @staticmethod
    def init() -> dict[str, Any]:
        from core.cortex.logic_engine import LogicEngine
        from core.peripherals.vision_agent import VisionAgent
        from core.peripherals.voice_core import VoiceCore
        from mente.arquitectura import asegurar_estructura

        asegurar_estructura()
        VoiceCore.enableNoiseGate(True)
        VisionAgent.activate()
        LogicEngine.lockLocalAgents()
        # Enlaza librerías internas (lib/) al kernel
        try:
            from lib import conectar_nucleo

            lib_st = conectar_nucleo()
        except Exception:
            lib_st = {"conectado": False}
        greet = MainController.initializeGreeting("enérgetico")
        return {
            "ok": True,
            "conexion": "COMPLETADA",
            "mensaje": "Conexión cerebral completada — kernel /core hard-linked.",
            "greeting": greet.get("frase"),
            "logic": LogicEngine.estado(),
            "voice": VoiceCore.estado(),
            "vision": VisionAgent.estado(),
            "lib": lib_st,
        }

    @staticmethod
    def estado() -> dict[str, Any]:
        try:
            from mente.conexion import conexion_cerebral_estado
            from core.cortex.logic_engine import LogicEngine
            from core.peripherals.voice_core import VoiceCore
            from core.peripherals.vision_agent import VisionAgent

            mente = conexion_cerebral_estado()
            return {
                "ok": bool(mente.get("ok")),
                "kernel": "/core",
                "mente": mente,
                "logic": LogicEngine.estado(),
                "voice": VoiceCore.estado(),
                "vision": VisionAgent.estado(),
            }
        except Exception as exc:
            return {"ok": False, "error": type(exc).__name__}
