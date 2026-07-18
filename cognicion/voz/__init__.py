# -*- coding: utf-8 -*-
"""Motor de voz de alta gama — Cartesia Sonic-3.5 (carga perezosa)."""

from __future__ import annotations

from typing import Any

__all__ = ["ResultadoTTS", "hablar_salomon", "texto_a_voz_cartesia", "cartesia_configurado"]


def __getattr__(name: str) -> Any:
    if name == "ResultadoTTS":
        from cognicion.voz.tipos import ResultadoTTS

        return ResultadoTTS
    if name in ("hablar_salomon", "texto_a_voz_cartesia", "cartesia_configurado"):
        import cognicion.voz.cartesia_tts as _mod

        return getattr(_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
