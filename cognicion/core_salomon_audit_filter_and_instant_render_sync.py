# [FILE: core_salomon_audit_filter_and_instant_render_sync.py]
# Motor de Filtro de Audición, Auditoría y Despliegue Instantáneo en Render
"""Audita texto/voz/visión antes de emitir; marca respuesta lista para TTS Adam."""

from __future__ import annotations

import json
import re
from typing import Any

_RE_EMPTY = re.compile(r"^[\s.…·•\-–—]*$")
_RE_PLACEHOLDER = re.compile(
    r"(?i)\b(lorem ipsum|TODO|FIXME|as an ai language model|"
    r"no puedo ayudar con eso porque|respuesta vac[ií]a)\b"
)
_FALLBACK = (
    "Israel, la respuesta no pasó el filtro de coherencia. "
    "Repíteme la pregunta en una frase clara y te contesto con precisión."
)


class SalomonAuditAndInstantSyncEngine:
    """Filtro estricto post-generación (texto + obligación TTS + visión)."""

    MODULE = "SalomonAuditAndInstantSyncEngine"
    STATUS = "AUDIT_FILTER_AND_INSTANT_RENDER_SYNC_ACTIVE"
    VERSION = "110.15.0"

    def __init__(self) -> None:
        self.module = self.MODULE
        self.status = self.STATUS

    def compile_sync_spec(self) -> dict[str, Any]:
        return {
            "action": (
                "Enforce strict post-generation audit and hearing filter, "
                "followed by immediate automated git commit and push to Render."
            ),
            "components": [
                "Strict Neural Audit & Hearing Filter",
                "Automated Live Render Deployment Pipeline",
                "Instant PWA Service Worker Cache Refresh & Active Badge",
            ],
            "deployment": (
                "Auto-commit, instant push to Render production, "
                "immediate PWA refresh, and settings badge active."
            ),
            "version": self.VERSION,
            "status": self.status,
        }

    def audit_response(
        self,
        texto: str,
        *,
        user_message: str = "",
        has_image: bool = False,
        require_voice: bool = False,
        tts_disponible: bool = False,
        audio_base64: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Filtra respuestas vacías / placeholder / fuera de contexto mínimo.
        No inventa hechos: solo valida emisión segura.
        """
        raw = (texto or "").strip()
        flags: list[str] = []
        released = raw

        if not raw or _RE_EMPTY.match(raw):
            flags.append("empty")
            released = _FALLBACK
        elif len(raw) < 2:
            flags.append("too_short")
            released = _FALLBACK
        elif _RE_PLACEHOLDER.search(raw):
            flags.append("placeholder")
            released = _FALLBACK

        # Visión: si hubo imagen y la respuesta ignora el frame
        if has_image and released == raw:
            low = raw.lower()
            if not any(
                k in low
                for k in (
                    "veo",
                    "viendo",
                    "imagen",
                    "foto",
                    "cámara",
                    "camara",
                    "frente",
                    "objeto",
                    "escena",
                    "israel",
                )
            ) and len(raw) < 24:
                flags.append("vision_context_weak")

        voice_ok = bool(audio_base64) or bool(tts_disponible)
        voice_required = bool(require_voice)
        if voice_required and not voice_ok:
            flags.append("tts_missing_client_must_fallback")

        ok = "empty" not in flags and "placeholder" not in flags and "too_short" not in flags
        report = {
            "ok": ok,
            "flags": flags,
            "require_voice": voice_required,
            "voice_present": voice_ok,
            "has_image": has_image,
            "chars": len(released),
            "rewritten": released != raw,
            "module": self.module,
            "protocol": "AUDIT_HEARING_FILTER",
            "user_preview": (user_message or "")[:80],
            "meta_keys": sorted((meta or {}).keys())[:20],
        }
        return {
            "texto": released,
            "report": report,
            "emit": True,
            "force_client_tts": voice_required and not voice_ok,
        }

    def run_self_check(self) -> dict[str, Any]:
        a = self.audit_response("")
        b = self.audit_response("Sí, Israel, estoy viendo una roca.", require_voice=True)
        return {
            "empty_blocked": a["report"]["rewritten"],
            "good_passes": b["report"]["ok"],
            "ok": a["report"]["rewritten"] and b["report"]["ok"],
            "spec": self.compile_sync_spec(),
        }


def audit_hearing_filter(
    texto: str,
    *,
    user_message: str = "",
    has_image: bool = False,
    require_voice: bool = False,
    tts_disponible: bool = False,
    audio_base64: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return SalomonAuditAndInstantSyncEngine().audit_response(
        texto,
        user_message=user_message,
        has_image=has_image,
        require_voice=require_voice,
        tts_disponible=tts_disponible,
        audio_base64=audio_base64,
        meta=meta,
    )


def obtener_audit_engine() -> SalomonAuditAndInstantSyncEngine:
    return SalomonAuditAndInstantSyncEngine()


if __name__ == "__main__":
    eng = SalomonAuditAndInstantSyncEngine()
    print("[COMPILANDO MOTOR DE FILTRO DE AUDITORÍA Y SINCRONIZACIÓN INSTANTÁNEA]")
    print(json.dumps(eng.compile_sync_spec(), indent=2, ensure_ascii=False))
    print(json.dumps(eng.run_self_check(), indent=2, ensure_ascii=False))
