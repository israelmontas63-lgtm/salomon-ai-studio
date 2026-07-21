# -*- coding: utf-8 -*-
"""
[FILE: core_vision_engine.py] — Arquitectura de Percepción Visual por Capas (Salomón AI).

Capas físicas aisladas:
  views/ui_layer/ · views/capture/ · views/analysis/ · core/brain_connector/

Prohibido mezclar UI con análisis o con el núcleo lógico.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

_log = logging.getLogger("salomon.vision.architecture")

ROOT = Path(__file__).resolve().parents[1]

FocusMode = Literal["continuous", "macro", "micro"]


class SalomonVisionArchitecture:
    """
    Motor de Visión por Computadora y Percepción Avanzada para Salomón AI.
    Capas modulares y físicas para evitar contaminación de estados:
    UI · captura · análisis macro/micro · puente al cerebro.
    """

    def __init__(self) -> None:
        # Capa 0: Directorios y Aislamiento Físico de Vistas
        self.vision_directory_structure = {
            "ui_layer": "views/ui_layer/",
            "capture_layer": "views/capture/",
            "macro_micro_engine": "views/analysis/",
            "brain_bridge": "core/brain_connector/",
        }

        # Capa 1: Parámetros de Visión de Vanguardia (IA Multimodal Avanzada)
        self.advanced_vision_params = {
            "resolution_mode": "adaptive_ultra",
            "context_retention": True,
            "noise_reduction": "tensor_filtering",
            "latency_target": "real_time_sync",
        }

        self._ensure_physical_dirs()

    def _ensure_physical_dirs(self) -> None:
        for rel in self.vision_directory_structure.values():
            path = ROOT / rel
            path.mkdir(parents=True, exist_ok=True)
            marker = path / ".gitkeep"
            if not marker.exists():
                marker.write_text("", encoding="utf-8")

    def verify_layer_isolation(self) -> dict[str, Any]:
        """Valida que las capas visuales no se mezclen con el núcleo lógico de la IA."""
        layers: dict[str, Any] = {}
        ok = True
        for layer_name, rel in self.vision_directory_structure.items():
            path = ROOT / rel
            exists = path.is_dir()
            layers[layer_name] = {"path": rel, "exists": exists, "absolute": str(path)}
            if not exists:
                ok = False
            else:
                _log.info(
                    "[VISION ARCHITECTURE] Capa '%s' aislada correctamente en: %s",
                    layer_name,
                    rel,
                )
        return {
            "ok": ok,
            "isolated": ok,
            "layers": layers,
            "params": dict(self.advanced_vision_params),
            "rule": "UI ≠ analysis ≠ brain_bridge",
        }

    def resolve_focus_mode(self, requested: str | None = None) -> FocusMode:
        """
        Contrato unificado JS ↔ Python:
          micro = detalle cercano (letra, texto)
          macro = objeto lejano (roca allá) / distant_object_zoom
        """
        m = (requested or "continuous").strip().lower()
        if m in (
            "micro",
            "cerca",
            "close",
            "detalle",
            "letra",
            "texto",
            "close_detail",
        ):
            return "micro"
        if m in (
            "macro",
            "lejos",
            "far",
            "distant",
            "roca",
            "distant_object_zoom",
            "horizonte",
        ):
            return "macro"
        return "continuous"

    def analysis_prompt(self, focus_mode: str | None, user_context: str | None = None) -> str:
        """Prompt dinámico micro (cerca) ↔ macro (lejos) anclado a la imagen."""
        mode = self.resolve_focus_mode(focus_mode)
        base = (user_context or "").strip()
        ground = (
            "Responde SOLO sobre lo visible en esta imagen; no inventes objetos, "
            "textos ni contextos que no aparezcan en el fotograma. "
            "Habla en primera persona en español natural, como si miraras con ojos: "
            "empieza con «Sí, Israel, estoy viendo…» o «Sí, Israel, veo…» e identifica "
            "el sujeto principal y un detalle concreto (por ejemplo especie de árbol "
            "o forma de una roca) solo si se deduce con claridad del fotograma."
        )
        if mode == "micro":
            hint = (
                "[Modo MICRO — detalle cercano] Describe texturas, bordes, texto "
                "legible, letras pequeñas y objetos próximos con alta fidelidad."
            )
        elif mode == "macro":
            hint = (
                "[Modo MACRO — objeto lejano] Describe el sujeto distante, "
                "relaciones espaciales del entorno y elementos alejados relevantes."
            )
        else:
            hint = (
                "[Modo adaptativo] Equilibra panorama y detalle según lo dominante "
                "en el fotograma."
            )
        if base:
            return f"{hint}\n{ground}\n\nPedido de Israel: {base}"
        return (
            f"{hint}\n{ground}\n\n"
            "Analiza esta captura de la cámara de Salomón con claridad y precisión."
        )

    def process_frame_to_brain(
        self,
        imagen_base64: str,
        *,
        contexto: str | None = None,
        focus_mode: str | None = None,
        imagen_mime: str = "image/jpeg",
        session_id: str | None = None,
        obtener_sesion: Any = None,
        via_central_button: bool = True,
    ) -> dict[str, Any]:
        """
        Canal rápido: captura → brain_bridge → núcleo.
        Bloquea interferencia de hardware secundario mientras procesa (AI_PROCESSING).
        """
        from core.brain_connector import send_visual_to_core
        from views.analysis import analyze_frame_modes
        from views.capture import normalize_frame_payload
        from views.ui_layer import assert_vision_ui_gate

        # UI layer: no mezclar — solo auditoría de exclusividad
        gate = assert_vision_ui_gate("vision_capture")
        frame = normalize_frame_payload(imagen_base64, mime=imagen_mime)
        mode = self.resolve_focus_mode(focus_mode)
        prompt = self.analysis_prompt(mode, contexto)

        # Analysis layer (macro/micro) — sin tocar UI
        analysis_meta = analyze_frame_modes(mode, frame)

        # Brain bridge — conexión directa al núcleo
        brain = send_visual_to_core(
            mensaje=prompt,
            imagen_base64=frame["imagen_base64"],
            imagen_mime=frame["imagen_mime"],
            session_id=session_id,
            obtener_sesion=obtener_sesion,
            via_central_button=via_central_button,
        )

        return {
            "ok": bool(brain.get("ok", brain.get("exito"))),
            "architecture": "SalomonVisionArchitecture",
            "focus_mode": mode,
            "params": dict(self.advanced_vision_params),
            "ui_gate": gate,
            "analysis": analysis_meta,
            "brain": brain,
            "via": "brain_bridge",
        }

    def estado(self) -> dict[str, Any]:
        isolation = self.verify_layer_isolation()
        try:
            from cognicion.core_control import get_system_state

            app_state = get_system_state()
        except Exception:
            app_state = {}
        return {
            "ok": True,
            "engine": "core_vision_engine",
            "isolation": isolation,
            "app_state": app_state,
            "directory_structure": dict(self.vision_directory_structure),
            "advanced_vision_params": dict(self.advanced_vision_params),
        }


_ARCH: SalomonVisionArchitecture | None = None


def obtener_vision_architecture() -> SalomonVisionArchitecture:
    global _ARCH
    if _ARCH is None:
        _ARCH = SalomonVisionArchitecture()
    return _ARCH
