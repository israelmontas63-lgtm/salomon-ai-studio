# -*- coding: utf-8 -*-
"""
Guardrail de aislamiento de capas — ejecutar antes de commit/push.
Exit 1 = BLOQUEAR despliegue.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    from cognicion.capas_inteligencia.layer_contracts import verify_contracts
    from cognicion.capas_inteligencia.neural_core_bridge import harmonize_all_layers
    from cognicion.core_salomon_synaptic_contracts_and_layer_isolation import (
        run_synaptic_architect,
    )

    print("[LAYER ISOLATION GUARD]")
    contracts = verify_contracts()
    bridges = harmonize_all_layers()
    synaptic = run_synaptic_architect()
    ok = (
        bool(contracts.get("ok"))
        and bool(bridges.get("sealed"))
        and bool(synaptic.get("complete"))
    )
    failed = [f for f in contracts.get("findings") or [] if not f.get("ok")]
    for f in failed[:20]:
        print(
            f"  FAIL L{f.get('layer')} {f.get('kind')} {f.get('file')}: {f.get('needle')}"
        )
    if not bridges.get("sealed"):
        print("  FAIL neural_core_bridge not sealed")
    if not synaptic.get("complete"):
        print("  FAIL synaptic_contracts incomplete")
    print(
        json.dumps(
            {
                "ok": ok,
                "contracts": contracts.get("ok"),
                "bridges": bridges.get("sealed"),
                "synaptic": synaptic.get("complete"),
            }
        )
    )
    if not ok:
        print("[BLOCKED] Regresión de capas detectada — despliegue cancelado.")
        return 1
    print("[OK] Contratos sinápticos y puentes neuronales sellados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
