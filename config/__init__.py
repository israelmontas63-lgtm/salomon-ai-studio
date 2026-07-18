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
    ok = bool(voz.get("sincronizado") and vision.get("activa") and cortex.get("externo_bloqueado"))
    frase = (
        "Visión activa, Módulo de Voz sincronizado, Contexto externo bloqueado"
        if ok
        else "Núcleo perceptivo incompleto — revisar config/"
    )
    return {
        "ok": ok,
        "confirmacion": frase,
        "voz": voz,
        "vision": vision,
        "cortex": cortex,
        "identidad_primaria": "Israel Monta",
        "proveedores": estado_proveedores(),
    }
