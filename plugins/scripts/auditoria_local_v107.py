# -*- coding: utf-8 -*-
"""Auditoría local Cursor↔Salomón — sin tocar Render."""
from __future__ import annotations

import hashlib
import importlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPORT: dict = {"ok": True, "hallazgos": [], "reparaciones": [], "checks": []}


def check(name: str, ok: bool, detalle: str = "") -> None:
    REPORT["checks"].append({"check": name, "ok": ok, "detalle": detalle})
    if not ok:
        REPORT["ok"] = False
        REPORT["hallazgos"].append(f"{name}: {detalle}")


def main() -> int:
    # 1) Imports críticos
    mods = [
        "app",
        "cerebro",
        "cognicion.salida_limpia",
        "cognicion.memoria.memory_controller",
        "cognicion.auditoria_cruzada",
        "SystemGuard",
    ]
    for m in mods:
        try:
            importlib.import_module(m)
            check(f"import:{m}", True)
        except Exception as exc:
            check(f"import:{m}", False, f"{type(exc).__name__}: {exc}")

    # 2) Paridad public/dist
    pairs = [
        ("studio/public/salomon-update.js", "studio/dist/salomon-update.js"),
        ("studio/public/drawers.js", "studio/dist/drawers.js"),
        ("studio/public/salomon-ui-shield.css", "studio/dist/salomon-ui-shield.css"),
        ("studio/public/index.html", "studio/dist/index.html"),
    ]
    for a, b in pairs:
        pa, pb = ROOT / a, ROOT / b
        same = pa.is_file() and pb.is_file() and pa.read_bytes() == pb.read_bytes()
        check(f"parity:{a}", same, "DIFF" if not same else "sync")

    # 3) Refs index.html
    html = (ROOT / "studio/dist/index.html").read_text(encoding="utf-8")
    refs = re.findall(r"""(?:src|href)=["']([^"']+)["']""", html)
    missing = []
    for r in refs:
        if r.startswith("http") or r.startswith("data:"):
            continue
        rel = r.split("?")[0].lstrip("/")
        if not (ROOT / "studio/dist" / rel).exists() and not (ROOT / rel).exists():
            missing.append(r)
    check("index_refs", not missing, ",".join(missing[:8]) or "all present")

    # 4) Fixes v107 reales
    upd = (ROOT / "studio/dist/salomon-update.js").read_text(encoding="utf-8")
    check("utf8_version_badge", "Versión:" in upd and "Ãƒ" not in upd)
    check("actualizar_no_header", "mountInHeader" not in upd)
    check("actualizar_menu_h", "ensureUpdateInToolsMenu" in upd)
    bundle = (ROOT / "studio/dist/assets/index-BdcDx9nN.js").read_text(encoding="utf-8")
    check("bundle_actualizar", "Actualizar" in bundle)
    consts = (ROOT / "studio/src/data/constants.js").read_text(encoding="utf-8")
    check("src_actualizar", '"Actualizar"' in consts)

    # 5) Sanitizer
    from cognicion.salida_limpia import sanitizar_salida_chat

    leak = (
        "Hola Israel.\n\n[Memoria vectorial — contexto relevante]\n"
        "1. secreto (relevancia: 0.148)\nInstrucción: usa esto"
    )
    clean = sanitizar_salida_chat(leak)
    check(
        "sanitizer_rag",
        "relevancia" not in clean and "Memoria vectorial" not in clean and "Hola Israel" in clean,
        repr(clean[:80]),
    )

    # 6) Memoria sin historial duplicado en contexto
    from cognicion.memoria.memory_controller import MemoryController

    ctrl = MemoryController("audit-local-v107")
    ctx, meta = ctrl.contexto_para_turno("hola auditoría")
    check(
        "memoria_sin_inmediata_duplicada",
        "[Memoria inmediata" not in (ctx or ""),
        str(meta)[:120],
    )

    # 7) Auditoría cruzada Salomón
    from cognicion.auditoria_cruzada import ejecutar_auditoria_cruzada

    cruz = ejecutar_auditoria_cruzada()
    check("auditoria_cruzada", bool(cruz.get("ok")), cruz.get("estado", ""))

    # 8) Ledger drift
    import SystemGuard

    drifts = SystemGuard.verificar_contra_ledger()
    check(
        "ledger_sin_drift",
        bool(drifts.get("ok")) and not drifts.get("drift"),
        json.dumps(drifts, ensure_ascii=False)[:300],
    )

    # 9) App routes wired
    from app import app

    paths = {getattr(r, "path", None) for r in app.routes}
    for need in (
        "/api/salud",
        "/api/conectividad",
        "/api/auditoria/cruzada",
        "/api/pwa/estado",
        "/api/chat",
    ):
        check(f"route:{need}", need in paths)

    print(json.dumps(REPORT, ensure_ascii=False, indent=2))
    return 0 if REPORT["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
