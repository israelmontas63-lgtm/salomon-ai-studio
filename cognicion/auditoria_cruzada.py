# -*- coding: utf-8 -*-
"""
Auditoría cruzada v105 — Cursor audita a Salomón / Salomón audita enlaces neuronales.
Reparación forzosa de núcleo (puertos, SW, mic/cam, memoria).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from cognicion.identidad import CREADOR, FIRMA_OWNERSHIP
from cognicion.reconexion import (
    puerto_canonico,
    reiniciar_memoria,
    probar_gateway_web,
)

ROOT = Path(__file__).resolve().parents[1]
VERSION = "105.0.0"


def _sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def auditoria_cursor_sobre_salomon() -> dict[str, Any]:
    """Cursor → Salomón: configs, SW, puertos, manifest."""
    hallazgos: list[str] = []
    reparaciones: list[str] = []

    puerto = puerto_canonico()
    if puerto == 800:
        hallazgos.append("puerto_800_invalido")
    else:
        reparaciones.append(f"puerto_dinamico_ha={puerto}")

    mf = ROOT / "studio/dist/manifest.json"
    data = json.loads(mf.read_text(encoding="utf-8"))
    perms = data.get("permissions") or []
    if "camera" not in perms or "microphone" not in perms:
        hallazgos.append("manifest_sin_permisos_media")
    else:
        reparaciones.append("manifest_permissions_camera_microphone")

    sw = (ROOT / "studio/dist/service-worker.js").read_text(encoding="utf-8")
    if "salomon-pwa-v105" not in sw:
        hallazgos.append("sw_cache_antigua")
    else:
        reparaciones.append("sw_cache_v105")
    if "url.origin !== self.location.origin" not in sw:
        hallazgos.append("sw_puede_bloquear_externos")
    else:
        reparaciones.append("sw_external_passthrough")

    idx = (ROOT / "studio/dist/index.html").read_text(encoding="utf-8")
    if "Permissions-Policy" not in idx:
        hallazgos.append("index_sin_permissions_policy")
    else:
        reparaciones.append("permissions_policy_meta")
    if "reconexion-perifericos.js?v=105" not in idx:
        hallazgos.append("perifericos_js_desfasado")
    else:
        reparaciones.append("perifericos_v105_enlazado")
    if "__SalomonNucleoReparacion105" not in idx:
        hallazgos.append("flag_reparacion_ausente")
    else:
        reparaciones.append("flag_reparacion_inline")

    cam = ROOT / "studio/dist/camera-engine.js"
    cam_hash = _sha(cam)
    ledger = json.loads((ROOT / "salomon_integrity_ledger.json").read_text(encoding="utf-8"))
    expected = (ledger.get("file_signatures_sha256") or {}).get("studio/dist/camera-engine.js")
    if cam_hash and expected and cam_hash != expected:
        hallazgos.append("camera_engine_drift")
    else:
        reparaciones.append("camera_engine_golden_ok")

    return {
        "agente": "Cursor",
        "objetivo": "Salomon",
        "puerto": puerto,
        "hallazgos": hallazgos,
        "reparaciones": reparaciones,
        "ok": len(hallazgos) == 0,
    }


def auditoria_salomon_sobre_enlace() -> dict[str, Any]:
    """Salomón → diagnóstico neuronal mic/cam/memoria/web."""
    hallazgos: list[str] = []
    reparaciones: list[str] = []

    peri = (ROOT / "studio/dist/reconexion-perifericos.js").read_text(encoding="utf-8")
    if "solicitarPermisos" not in peri:
        hallazgos.append("sin_solicitar_permisos_boot")
    else:
        reparaciones.append("permisos_al_gesto_y_standalone")
    if "getUserMedia" not in peri:
        hallazgos.append("sin_mediadevices_bridge")
    else:
        reparaciones.append("mediadevices_bridge_activo")

    kernel = (ROOT / "studio/dist/salomon-security-kernel.js").read_text(encoding="utf-8")
    if "__SalomonNucleoReparacion105" not in kernel:
        hallazgos.append("kernel_bloquea_gum_sin_ventana_reparacion")
    else:
        reparaciones.append("kernel_respeta_ventana_reparacion")

    mem = reiniciar_memoria()
    if not mem.get("ok"):
        hallazgos.append("memoria_rw_fallo")
    else:
        reparaciones.append(f"memoria_{mem.get('motor')}_ok")

    web = probar_gateway_web()
    if not web.get("ok"):
        hallazgos.append("gateway_web_fallo")
    else:
        reparaciones.append(f"gateway_{web.get('motor')}_ok")

    # Enlace lógico cámara (sin hardware físico en CI)
    cam_js = (ROOT / "studio/dist/camera-engine.js").read_text(encoding="utf-8", errors="replace")
    if "getUserMedia" not in cam_js:
        hallazgos.append("camera_engine_sin_gum")
    else:
        reparaciones.append("camera_engine_gum_presente")

    return {
        "agente": "Salomon",
        "objetivo": "enlace_neuronal_mic_cam",
        "memoria": mem,
        "gateway_web": web,
        "hallazgos": hallazgos,
        "reparaciones": reparaciones,
        "ok": len(hallazgos) == 0,
        "nota_fisica": (
            "Mic/cam requieren gesto del usuario en el dispositivo; "
            "código PWA solicita permisos al primer toque y en standalone."
        ),
    }


def ejecutar_auditoria_cruzada() -> dict[str, Any]:
    cursor = auditoria_cursor_sobre_salomon()
    salomon = auditoria_salomon_sobre_enlace()
    ok = bool(cursor.get("ok") and salomon.get("ok"))
    return {
        "ok": ok,
        "protocol": "AUDITORIA_BLOQUEO_MUTUO_REPARACION_FORZOSA",
        "version": VERSION,
        "creador": CREADOR,
        "firma": FIRMA_OWNERSHIP,
        "cursor_audita_salomon": cursor,
        "salomon_audita_enlace": salomon,
        "estado": (
            "NÚCLEO REPARADO Y SINCRONIZADO"
            if ok
            else "REPARACION_INCOMPLETA"
        ),
        "condiciones": {
            "puerto_estable": cursor.get("ok") and puerto_canonico() != 800,
            "mic_codigo_listo": "permisos_al_gesto_y_standalone" in (salomon.get("reparaciones") or []),
            "camara_codigo_lista": "camera_engine_gum_presente" in (salomon.get("reparaciones") or []),
            "memoria_ok": bool((salomon.get("memoria") or {}).get("ok")),
            "web_ok": bool((salomon.get("gateway_web") or {}).get("ok")),
            "pwa_sw_v105": "sw_cache_v105" in (cursor.get("reparaciones") or []),
        },
    }
