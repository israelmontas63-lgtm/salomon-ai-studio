# -*- coding: utf-8 -*-
"""Resella firmas del ledger + golden snapshot tras cambios UI autorizados (local)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import SystemGuard as sg  # noqa: E402


def main() -> int:
    # Actualizar golden snapshot desde el árbol vivo (incluye index.html v107)
    snap = sg.crear_snapshot_salud(force=True)
    ledger = sg.load_ledger()
    sigs = dict(ledger.get("file_signatures_sha256") or {})
    for _label, rel in sg.CRITICAL_MAP.items():
        path = ROOT / rel
        if path.is_file():
            sigs[rel] = sg._sha256(path)
    ledger["file_signatures_sha256"] = sigs
    ledger["updated_at"] = sg._utc_now()
    ledger["note"] = "resync local v107 — Actualizar menú H / UTF-8 / salida limpia"
    sg.LEDGER_PATH.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = sg.verificar_contra_ledger(False)
    print(json.dumps({"snapshot_files": len(snap.get("files") or {}), "ledger_ok": report.get("ok"), "drift": report.get("drift")}, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
