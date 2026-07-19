# -*- coding: utf-8 -*-
"""Configuración de núcleo perceptivo — voz, visión, Memory Cortex + providers."""

from __future__ import annotations

from config.memory_cortex import cortex_status
from config.providers import estado_proveedores
from config.vision_integration import vision_status
from config.voice_parameters import voice_status


def estado_nucleo_perceptivo() -> dict:
    """Confirmación operativa pedida por Israel."""
    voz = voice_status()
    vision = vision_status()
    cortex = cortex_status()
    proveedores = estado_proveedores()
    # En modo neuronal (web_agentes) externo_bloqueado=False es CORRECTO, no un fallo.
    cortex_ok = bool(cortex.get("modo")) and (
        bool(cortex.get("externo_bloqueado")) or bool(cortex.get("web_agentes"))
    )
    ok = bool(
        voz.get("sincronizado")
        and vision.get("activa")
        and cortex_ok
        and proveedores.get("llm_disponible")
    )
    if ok and cortex.get("web_agentes"):
        frase = (
            "Núcleo perceptivo neuronal OK — voz sincronizada, visión activa, "
            "LLM listo, agentes web autorizados"
        )
    elif ok:
        frase = "Visión activa, Módulo de Voz sincronizado, Contexto externo bloqueado"
    else:
        frase = "Núcleo perceptivo incompleto — revisar config/"
    return {
        "ok": ok,
        "confirmacion": frase,
        "voz": voz,
        "vision": vision,
        "cortex": cortex,
        "identidad_primaria": "Israel Monta",
        "proveedores": proveedores,
    }
