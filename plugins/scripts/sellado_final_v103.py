# -*- coding: utf-8 -*-
"""Sellado final v103 — auditoría pre-despliegue Render."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    sys.path.insert(0, str(ROOT))
    # 1) Preflight extendido
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "preflight_audit_v98.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
    )
    out = proc.stdout or ""
    i = out.find("{")
    preflight = json.loads(out[i:]) if i >= 0 else {"ok": False, "error": "no_json"}

    # 2) Simulación Render Free
    render_ok = True
    render_detalle: list[str] = []
    try:
        import gunicorn  # noqa: F401
        import uvicorn  # noqa: F401

        render_detalle.append("gunicorn+uvicorn import OK")
    except Exception as exc:
        render_ok = False
        render_detalle.append(f"gunicorn/uvicorn FAIL: {exc}")

    try:
        from cognicion.eficiencia import estado_eficiencia

        eff = estado_eficiencia()
        if not eff.get("listo_free_tier"):
            render_ok = False
            render_detalle.append("free_tier no listo")
        else:
            render_detalle.append(f"free_tier caps={eff.get('colsub_caps')}")
    except Exception as exc:
        render_ok = False
        render_detalle.append(f"eficiencia FAIL: {exc}")

    try:
        import app as appmod

        paths = {getattr(r, "path", None) for r in appmod.app.routes}
        for need in (
            "/api/salud",
            "/api/identidad",
            "/api/inmune",
            "/manifest.json",
            "/service-worker.js",
            "/camera-engine.js",
        ):
            if need not in paths:
                render_ok = False
                render_detalle.append(f"ruta faltante {need}")
        render_detalle.append("app routes OK")
    except Exception as exc:
        render_ok = False
        render_detalle.append(f"app import FAIL: {exc}")

    # 3) PWA files
    sw = (ROOT / "studio/dist/service-worker.js").read_text(encoding="utf-8")
    pwa_ok = "salomon-pwa-v103" in sw and "/api/inmune" in sw
    cam = ROOT / "studio/dist/camera-engine.js"
    cam_ok = cam.is_file() and cam.stat().st_size > 1000

    import SystemGuard as sg

    ledger = sg.verificar_contra_ledger(False)

    ok = bool(preflight.get("ok")) and render_ok and pwa_ok and cam_ok and bool(ledger.get("ok"))
    report = {
        "ok": ok,
        "protocol": "SELLADO_FINAL_DESPLIEGUE_SEGURO",
        "version": "103.0.0",
        "estado": (
            "SELLADO Y LISTO PARA DESPLIEGUE - INTEGRIDAD 100%"
            if ok
            else "BLOQUEADO - REPARAR ANTES DE PUSH"
        ),
        "preflight_ok": preflight.get("ok"),
        "preflight_fails": [c["check"] for c in preflight.get("checks", []) if not c.get("ok")],
        "render_sim": {"ok": render_ok, "detalle": render_detalle},
        "pwa": {"cache": "salomon-pwa-v103", "ok": pwa_ok},
        "camera_engine": {"ok": cam_ok, "immutable": True},
        "ledger_ok": ledger.get("ok"),
        "push_autorizado": False,
        "nota": "Push a origin/main solo con AUTORIZADO explícito de Israel.",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
