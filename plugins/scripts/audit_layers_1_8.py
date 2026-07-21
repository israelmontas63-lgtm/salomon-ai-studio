# -*- coding: utf-8 -*-
"""Auditoría puntual capas 1-8 — no forma parte del runtime."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

errors: list[str] = []


def main() -> int:
    print("=== AUDIT CAPAS 1-8 ===")

    from cognicion.capas_inteligencia import catalog
    from cognicion.capas_inteligencia.layer_contracts import verify_contracts
    from cognicion.capas_inteligencia.neural_core_bridge import harmonize_all_layers
    from cognicion.capas_inteligencia.synaptic_bus import (
        AUTHORIZED_SYNAPSES,
        synapse_allowed,
    )

    cats = catalog()
    ids = [c["id"] for c in cats]
    print("catalog_ids", ids)
    if ids != list(range(1, 9)):
        errors.append(f"catalog ids != 1..8: {ids}")

    h = harmonize_all_layers()
    print("harmonize_sealed", h.get("sealed"), h.get("core_links"))
    for r in h.get("layer_bridges") or []:
        print(
            f"  L{r['id']} {r['name']}: ok={r['ok']} "
            f"hooks={r['hooks_ok']} markers={r['markers_ok']} collision={r['collision']}"
        )
        if not r["ok"]:
            errors.append(f"bridge L{r['id']} fail")
    if not h.get("sealed"):
        errors.append("harmonize not sealed")

    vc = verify_contracts()
    print("contracts_ok", vc.get("ok"))
    if not vc.get("ok"):
        bad = [f for f in (vc.get("findings") or []) if not f.get("ok")]
        errors.append(f"contracts fail n={len(bad)}")
        print("  bad", bad[:8])

    for s in AUTHORIZED_SYNAPSES:
        if s.get("from") in (7, 8) or s.get("to") in (7, 8):
            print(f"  synapse {s.get('from')}->{s.get('to')} {s.get('channel')}")
    print("synapse L7->L8", synapse_allowed(7, 8, "draft_for_asalomon"))
    print("synapse L8->L4", synapse_allowed(8, 4, "emit_asalomon_sealed"))
    if not synapse_allowed(7, 8, "draft_for_asalomon"):
        errors.append("missing synapse draft_for_asalomon")

    mods = {
        2: "cognicion.capas_inteligencia.layer_02_memory",
        3: "cognicion.capas_inteligencia.layer_03_reasoning",
        6: "cognicion.capas_inteligencia.layer_06_autonomy",
        7: "cognicion.capas_inteligencia.layer_07_metacognition",
        8: "cognicion.capas_inteligencia.layer_08_asalomon",
    }
    for lid, m in mods.items():
        try:
            __import__(m)
            print(f"import L{lid} OK")
        except Exception as e:
            errors.append(f"import L{lid}: {e}")
            print(f"import L{lid} FAIL", e)

    from cognicion.capas_inteligencia.layer_07_metacognition import apply_supervision
    from cognicion.capas_inteligencia.layer_08_asalomon import (
        apply_asalomon_seal,
        estado_layer_08,
    )

    t7, r7 = apply_supervision(
        "Paris es la capital de Francia.", user_message="capital de Francia"
    )
    t8, r8 = apply_asalomon_seal(
        "Como modelo de lenguaje no tengo creador.",
        user_message="quien eres",
    )
    print("L7 ok", bool(t7), "action", r7.get("action"))
    print(
        "L8 rewritten",
        r8.get("rewritten"),
        "action",
        r8.get("action"),
        "forms",
        r8.get("reasoning_forms"),
    )
    if not r8.get("ok"):
        errors.append("L8 seal not ok")
    if not estado_layer_08().get("active"):
        errors.append("L8 not active")

    from cognicion.capas.verificar_conexion import verificar_conexion_maestra

    m = verificar_conexion_maestra()
    print("master_ok", m.get("ok"))
    for k, v in (m.get("capas") or {}).items():
        print(f"  {k}: {v.get('ok')}")
        if not v.get("ok"):
            errors.append(f"master {k}")

    cerebro = (ROOT / "cerebro.py").read_text(encoding="utf-8", errors="replace")
    orch = (ROOT / "cognicion" / "orquestador.py").read_text(
        encoding="utf-8", errors="replace"
    )
    for needle in (
        "apply_supervision",
        "apply_asalomon_seal",
        "layer_07",
        "layer_08",
    ):
        ok = needle in cerebro
        print(f"cerebro:{needle}", ok)
        if not ok:
            errors.append(f"cerebro missing {needle}")
    for needle in ("enrich_reasoning_hint", "detect_reasoning_forms", "layer_08"):
        ok = needle in orch
        print(f"orch:{needle}", ok)
        if not ok:
            errors.append(f"orch missing {needle}")

    from cognicion.evolucion.habilidades_30x import integrar_30x_via_sce
    from cognicion.evolucion.sce import analizar_valor, estado_sce

    print("sce_active", estado_sce().get("active"))
    torch_d = analizar_valor("instalar torch cuda", registrar_ledger=False).get(
        "decision"
    )
    print("torch_block", torch_d)
    if torch_d != "bloquear":
        errors.append("torch not blocked")
    p = integrar_30x_via_sce(registrar_ledger=False)
    print("30x", p.get("aprobadas"), "comic", p.get("comic_engine"))
    if not p.get("comic_engine"):
        errors.append("comic engine inactive")

    from cognicion.capas.contexto import obtener_contexto, usar_contexto
    from cognicion.busqueda.agente import (
        respuesta_parece_limite_o_vacia,
        buscar_web,
    )

    with usar_contexto(session_id="audit-l8"):
        assert obtener_contexto().session_id == "audit-l8"
    print("contexto OK")
    assert respuesta_parece_limite_o_vacia("quota exceeded")
    bw = buscar_web("")
    print("buscar_web empty fail_soft", bw.get("error") == "consulta_vacia")

    settings = (ROOT / "static" / "js" / "settings_manager.js").read_text(
        encoding="utf-8", errors="replace"
    )
    if "Capas 1–8" not in settings and "Capas 1-8" not in settings:
        # unicode en dash
        if "1–8" not in settings and "asalomon" not in settings.lower():
            errors.append("tuerquita missing L8 meta")
    else:
        print("tuerquita L8 meta OK")
    if "asalomon" not in settings.lower() and "Asalomón" not in settings:
        # still check app.py
        app = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
        if '"asalomon": True' not in app and "'asalomon': True" not in app:
            errors.append("api/version missing asalomon flag")
        else:
            print("api asalomon flag OK")
    else:
        print("tuerquita asalomon text OK")

    print("=== RESULT ===")
    print("ERRORS", len(errors))
    for e in errors:
        print(" -", e)
    print("VALID" if not errors else "INVALID")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
