# -*- coding: utf-8 -*-
"""
SystemGuard — Cerebro Inmune de Salomón Viviente (v40.0.0)

Software vivo: integridad por checksum, alerta de desmembramiento,
autoreparación desde Golden Snapshot.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
LEDGER_PATH = ROOT / "salomon_integrity_ledger.json"
ATTEMPTS_PATH = ROOT / "salomon_integrity_attempts.jsonl"
SNAPSHOT_DIR = ROOT / "golden_snapshots" / "salud_activa"
MANIFEST_PATH = SNAPSHOT_DIR / "manifest.json"

# Archivos críticos del mapa inmune
CRITICAL_MAP = {
    "app.py": "app.py",
    "CameraEngine": "studio/dist/camera-engine.js",
    "StreamingUI": "studio/dist/camera-v13.js",
    "CameraCSS": "studio/dist/camera-v13.css",
    "UI_Layout": "studio/dist/index.html",
    "SecurityKernel": "studio/dist/salomon-security-kernel.js",
    "MediaStreamManager": "studio/src/features/camera_v13/MediaStreamManager.js",
}


class IntegrityViolation(Exception):
    """INTEGRITY_VIOLATION — modificación no autorizada / desmembramiento."""

    def __init__(self, archivo: str, detalle: str = ""):
        self.archivo = archivo
        self.detalle = detalle
        msg = (
            f"INTEGRITY_VIOLATION: Intento de desmembramiento detectado en [{archivo}]. "
            f"Bloqueando modificación. {detalle}"
        )
        super().__init__(msg)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _append_alert(payload: dict[str, Any]) -> None:
    payload = {**payload, "at": _utc_now()}
    with ATTEMPTS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    # Log visible para Israel / Render
    print(
        f"[SystemGuard] Intento de desmembramiento detectado en [{payload.get('archivo')}]. "
        f"Bloqueando modificación. ({payload.get('detalle')})",
        flush=True,
    )


def load_ledger() -> dict[str, Any]:
    if not LEDGER_PATH.exists():
        return {}
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def mapear_integridad() -> dict[str, Any]:
    """Primer / periódico mapeo de integridad de archivos críticos."""
    mapping: dict[str, Any] = {"at": _utc_now(), "files": {}}
    for label, rel in CRITICAL_MAP.items():
        path = ROOT / rel
        if not path.exists():
            mapping["files"][label] = {"path": rel, "status": "MISSING", "sha256": None}
            continue
        mapping["files"][label] = {
            "path": rel,
            "status": "PRESENT",
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
    return mapping


def crear_snapshot_salud(force: bool = False) -> dict[str, Any]:
    """Copia de seguridad limpia (Golden Backup) para autoreparación."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    if MANIFEST_PATH.exists() and not force:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    files_meta: dict[str, Any] = {}
    for label, rel in CRITICAL_MAP.items():
        src = ROOT / rel
        if not src.exists():
            continue
        dest = SNAPSHOT_DIR / Path(rel).name
        # Evitar colisiones de nombre
        if label == "CameraEngine":
            dest = SNAPSHOT_DIR / "camera-engine.js"
        elif label == "StreamingUI":
            dest = SNAPSHOT_DIR / "camera-v13.js"
        elif label == "CameraCSS":
            dest = SNAPSHOT_DIR / "camera-v13.css"
        elif label == "UI_Layout":
            dest = SNAPSHOT_DIR / "index.html"
        elif label == "SecurityKernel":
            dest = SNAPSHOT_DIR / "salomon-security-kernel.js"
        elif label == "MediaStreamManager":
            dest = SNAPSHOT_DIR / "MediaStreamManager.js"
        elif label == "app.py":
            dest = SNAPSHOT_DIR / "app.py"
        shutil.copy2(src, dest)
        files_meta[label] = {
            "source": rel,
            "snapshot": str(dest.relative_to(ROOT)).replace("\\", "/"),
            "sha256": _sha256(src),
        }

    manifest = {
        "id": "salud_activa",
        "created_at": _utc_now(),
        "protocol": "SALOMON_VIVIENTE",
        "version": "40.0.0",
        "files": files_meta,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def verificar_contra_ledger(raise_on_drift: bool = False) -> dict[str, Any]:
    """Compara archivos vivos vs firmas del ledger (Golden Snapshot lógico)."""
    ledger = load_ledger()
    sigs = ledger.get("file_signatures_sha256") or {}
    report: dict[str, Any] = {
        "ok": True,
        "drift": [],
        "checked": 0,
        "protocol": ledger.get("protocol"),
    }
    for label, rel in CRITICAL_MAP.items():
        path = ROOT / rel
        expected = sigs.get(rel)
        if not path.exists():
            report["ok"] = False
            report["drift"].append({"label": label, "path": rel, "reason": "MISSING"})
            _append_alert(
                {
                    "level": "INTEGRITY_VIOLATION",
                    "archivo": rel,
                    "detalle": "MISSING",
                    "label": label,
                }
            )
            continue
        actual = _sha256(path)
        report["checked"] += 1
        if expected and actual != expected:
            report["ok"] = False
            report["drift"].append(
                {
                    "label": label,
                    "path": rel,
                    "reason": "CHECKSUM_DRIFT",
                    "expected": expected,
                    "actual": actual,
                }
            )
            _append_alert(
                {
                    "level": "INTEGRITY_VIOLATION",
                    "archivo": rel,
                    "detalle": "CHECKSUM_DRIFT",
                    "label": label,
                }
            )
            if raise_on_drift:
                raise IntegrityViolation(rel, "CHECKSUM_DRIFT")
    return report


def auto_reparar(drift_paths: list[str] | None = None) -> dict[str, Any]:
    """
    Self-healing: restaura desde Golden Snapshot.
    Notifica: Detecté un error, me he reparado a mí mismo.
    """
    if not MANIFEST_PATH.exists():
        crear_snapshot_salud(force=True)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    restored: list[str] = []
    for label, meta in (manifest.get("files") or {}).items():
        src_rel = meta.get("source")
        snap_rel = meta.get("snapshot")
        if not src_rel or not snap_rel:
            continue
        if drift_paths and src_rel not in drift_paths and label not in drift_paths:
            continue
        snap = ROOT / snap_rel
        target = ROOT / src_rel
        if not snap.exists():
            continue
        # Solo restaurar si el vivo difiere del snapshot
        if target.exists() and _sha256(target) == _sha256(snap):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snap, target)
        restored.append(src_rel)

    result = {
        "healed": bool(restored),
        "restored": restored,
        "message": (
            "Detecté un error, me he reparado a mí mismo. Informe de diagnóstico adjunto."
            if restored
            else "Sin drift reparable; snapshot intacto."
        ),
        "at": _utc_now(),
    }
    if restored:
        print(f"[SystemGuard] {result['message']} restored={restored}", flush=True)
        _append_alert(
            {
                "level": "SELF_HEAL",
                "archivo": ",".join(restored),
                "detalle": result["message"],
            }
        )
    return result


def assert_writable(rel_path: str, autorizado: bool = False) -> None:
    """
    Negación de escritura sobre Core sin autorización explícita de Israel.
    Llamar desde herramientas / hooks antes de mutar.
    """
    norm = rel_path.replace("\\", "/")
    critical = set(CRITICAL_MAP.values())
    if norm in critical or any(norm.endswith(c.split("/")[-1]) and c in critical for c in critical):
        if not autorizado:
            _append_alert(
                {
                    "level": "INTEGRITY_VIOLATION",
                    "archivo": norm,
                    "detalle": "WRITE_DENIED_NO_AUTORIZADO",
                }
            )
            raise IntegrityViolation(
                norm,
                "Sin AUTORIZADO de Israel. Bloqueando modificación.",
            )


def boot_guard(auto_heal: bool = True) -> dict[str, Any]:
    """Arranque inmune: snapshot si falta + verificación + heal opcional."""
    crear_snapshot_salud(force=False)
    mapping = mapear_integridad()
    report = verificar_contra_ledger(raise_on_drift=False)
    heal = None
    if not report["ok"] and auto_heal:
        paths = [d["path"] for d in report["drift"] if d.get("path")]
        # Autoreparar assets de cámara/UI/kernel; app.py drift exige AUTORIZADO humano
        safe = [
            p
            for p in paths
            if "camera" in p.replace("\\", "/")
            or p.endswith("index.html")
            or p.endswith("salomon-security-kernel.js")
        ]
        if safe:
            heal = auto_reparar(safe)
            report = verificar_contra_ledger(raise_on_drift=False)
    return {
        "viviente": True,
        "protocol": "SALOMON_VIVIENTE",
        "version": "40.0.0",
        "mapping": mapping,
        "integrity": report,
        "heal": heal,
    }


if __name__ == "__main__":
    crear_snapshot_salud(force=True)
    out = boot_guard(auto_heal=True)
    print(json.dumps({
        "protocol": out["protocol"],
        "version": out["version"],
        "integrity_ok": out["integrity"]["ok"],
        "checked": out["integrity"]["checked"],
        "drift": out["integrity"]["drift"],
        "files": {k: v.get("sha256", "")[:16] for k, v in out["mapping"]["files"].items()},
        "heal": out.get("heal"),
    }, ensure_ascii=False, indent=2))
