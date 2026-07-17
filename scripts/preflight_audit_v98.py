# -*- coding: utf-8 -*-
"""Pre-flight audit v98 — integridad, agentes, PWA, endpoints."""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
report: dict = {"ok": True, "checks": [], "fixes": []}


def check(name: str, ok: bool, detalle: str = "") -> None:
    report["checks"].append({"check": name, "ok": ok, "detalle": detalle})
    if not ok:
        report["ok"] = False


def main() -> int:
    # 1) Python AST
    errs = []
    for p in [ROOT / "app.py", ROOT / "SystemGuard.py", ROOT / "cerebro.py", ROOT / "settings.py"]:
        try:
            ast.parse(p.read_text(encoding="utf-8"))
        except Exception as exc:
            errs.append(f"{p.name}: {exc}")
    for p in (ROOT / "cognicion").rglob("*.py"):
        try:
            ast.parse(p.read_text(encoding="utf-8"))
        except Exception as exc:
            errs.append(f"{p}: {exc}")
    check("python_syntax", not errs, f"errs={len(errs)}" if errs else "0 errores")

    # 2) Manifests UTF-8 + required fields
    manifests = [
        ROOT / "studio/dist/manifest.json",
        ROOT / "studio/dist/manifest.webmanifest",
        ROOT / "studio/public/manifest.json",
        ROOT / "studio/public/manifest.webmanifest",
        ROOT / "manifest.json",
    ]
    for mf in manifests:
        raw = mf.read_bytes()
        bom = raw.startswith(b"\xef\xbb\xbf")
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            check(f"manifest:{mf.name}", False, str(exc))
            continue
        name = data.get("name") or ""
        short = data.get("short_name") or ""
        # ASCII-safe install names (evita fallos de parsers Windows/PowerShell)
        ascii_ok = all(ord(ch) < 128 for ch in name + short)
        check(
            f"manifest_parse:{mf.name}",
            not bom
            and isinstance(data, dict)
            and data.get("display") == "standalone"
            and data.get("theme_color") == "#000000"
            and ascii_ok,
            f"name={name!r} short={short!r} theme={data.get('theme_color')}",
        )

    # 3) SW policy vs visual APIs
    sw = (ROOT / "studio/dist/service-worker.js").read_text(encoding="utf-8")
    check("sw_exists", "salomon-pwa-v97" in sw or "CACHE" in sw, "cache id presente")
    check("sw_identidad_swr", "/api/identidad" in sw, "identidad en núcleo PWA")
    check("sw_policy_fn", "isApiNetworkOnly" in sw, "política API network-only activa")
    idx = sw.find('path === "/api/identidad"')
    allow = sw[idx : idx + 400] if idx >= 0 else ""
    check(
        "sw_no_cache_media_chat",
        "/api/media" not in allow and "/api/chat" not in allow,
        "media/chat fuera de allowlist SWR",
    )

    # 4) Agents dry-run
    sys.path.insert(0, str(ROOT))
    from cognicion.agente.coordinador import clasificar_rol, coordinar
    from cognicion.agente.guard import ejecutar_guard, validar_dependencia_render
    from cognicion.identidad import estado_identidad
    from cognicion.web import estado_web_architect
    from cognicion.eficiencia import estado_eficiencia
    import SystemGuard as sg

    check("rol_coder", clasificar_rol("implementa funcion python") == "coder")
    check("rol_visual", clasificar_rol("genera una imagen hd") == "visual")
    check("rol_guard", clasificar_rol("verifica integridad") == "guard")
    g = ejecutar_guard("integridad")
    check("agent_guard", bool(g.get("ok")), f"checked={g.get('checked')}")
    check("deps_torch_blocked", not validar_dependencia_render("torch")["ok"])
    c = coordinar("explica suma en python", solo_razonamiento=True)
    check("agent_coder", c.get("agente") == "Agent_Coder" and c.get("exito"))
    v = coordinar("genera una imagen de audit")
    async_ok = bool(v.get("async") or (v.get("resultado") or {}).get("async"))
    check("agent_visual_async", v.get("agente") == "Agent_Visual" and async_ok)
    rep = sg.verificar_contra_ledger(False)
    check("ledger", bool(rep.get("ok")), f"drift={rep.get('drift')}")
    idn = estado_identidad()
    check("identidad_active", bool(idn.get("active")), idn.get("creador") or "")
    web = estado_web_architect()
    check("web_architect_active", bool(web.get("active")))
    eff = estado_eficiencia()
    check(
        "free_tier_caps",
        bool(eff.get("listo_free_tier"))
        and eff.get("colsub_caps", {}).get("max_workers") == 1,
        str(eff.get("colsub_caps")),
    )

    from cognicion.evolucion import analizar_valor, estado_sce

    sce_ok = estado_sce().get("active") and estado_sce().get("version") == "100.0.0"
    check("sce_activo", bool(sce_ok), "SCE v100")
    a = analizar_valor("añadir multilingüismo y síntesis de voz TTS vía API")
    check("sce_aprueba_mejora", a.get("decision") == "aprobar", a.get("mensaje", "")[:80])
    b = analizar_valor("instalar torch y transformers en runtime")
    check("sce_bloquea_riesgo", b.get("decision") == "bloquear", b.get("mensaje", "")[:80])

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
