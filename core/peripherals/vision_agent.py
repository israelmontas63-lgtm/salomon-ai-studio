# -*- coding: utf-8 -*-
"""VisionAgent (server mirror)."""

from __future__ import annotations

from typing import Any


class VisionAgent:
    _active = False

    @classmethod
    def activate(cls) -> bool:
        cls._active = True
        return True

    @classmethod
    def estado(cls) -> dict[str, Any]:
        from config.vision_integration import vision_status

        st = vision_status()
        return {
            "activa": bool(cls._active or st.get("activa")),
            "in_input_flow": True,
            **st,
        }
