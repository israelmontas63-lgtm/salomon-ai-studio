# -*- coding: utf-8 -*-
"""
Cerebro Cognitivo Dual — Despertar de Salomón.

Rutas canónicas (2026):
  - Memoria episódica → `cognicion.episodica`
  - Ciclo heurístico → `cognicion.aprendizaje_ciclo`
  - Motor post-turno → `cognicion.aprendizaje` (distinto; no duplicar)

Este paquete reexporta APIs públicas con imports absolutos estables.
"""

from __future__ import annotations

from typing import Any

from cognicion.cognitivo.despertar import (
    ciclo_pre_tarea,
    consolidar_sesion,
    estado_cognitivo_dual,
    registrar_correccion,
    registrar_exito,
)

__all__ = [
    "ciclo_pre_tarea",
    "consolidar_sesion",
    "estado_cognitivo_dual",
    "registrar_correccion",
    "registrar_exito",
    "verify_path_sync",
    "SYNC_OK",
]


def verify_path_sync() -> dict[str, Any]:
    """Valida que shims y canónicos exporten los mismos contratos."""
    checks: list[dict[str, Any]] = []
    ok = True

    def mark(name: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        checks.append({"check": name, "ok": passed, "detail": detail})
        if not passed:
            ok = False

    try:
        import cognicion.aprendizaje_ciclo as ciclo
        import cognicion.cognitivo.aprendizaje as ciclo_shim
        import cognicion.cognitivo.episodica as epi_shim
        import cognicion.episodica as epi

        mark(
            "episodica_canonical",
            callable(epi.guardar_episodio) and bool(epi.FRASE_APRENDIZAJE),
            "cognicion.episodica",
        )
        mark(
            "episodica_shim",
            epi_shim.guardar_episodio is epi.guardar_episodio
            and epi_shim.FRASE_APRENDIZAJE == epi.FRASE_APRENDIZAJE,
            "cognitivo.episodica → episodica",
        )
        mark(
            "ciclo_canonical",
            callable(ciclo.registrar_incidente) and callable(ciclo.inferir_causa_raiz),
            "cognicion.aprendizaje_ciclo",
        )
        mark(
            "ciclo_shim",
            ciclo_shim.registrar_incidente is ciclo.registrar_incidente,
            "cognitivo.aprendizaje → aprendizaje_ciclo",
        )
        # Separación dura: motor post-turno ≠ ciclo heurístico
        import cognicion.aprendizaje as motor_turno

        mark(
            "no_name_collision",
            not hasattr(motor_turno, "registrar_incidente")
            or motor_turno.registrar_incidente is not ciclo.registrar_incidente,
            "aprendizaje ≠ aprendizaje_ciclo",
        )
        mark(
            "motor_turno_intact",
            callable(getattr(motor_turno, "procesar_turno", None)),
            "cognicion.aprendizaje.procesar_turno",
        )
    except Exception as exc:
        mark("import_graph", False, f"{type(exc).__name__}: {exc}")

    return {
        "ok": ok,
        "status": "SYNC_OK" if ok else "SYNC_FAIL",
        "checks": checks,
        "canonical": {
            "episodica": "cognicion.episodica",
            "aprendizaje_ciclo": "cognicion.aprendizaje_ciclo",
            "aprendizaje_turno": "cognicion.aprendizaje",
        },
        "legacy_shims": {
            "episodica": "cognicion.cognitivo.episodica",
            "aprendizaje": "cognicion.cognitivo.aprendizaje",
        },
    }


SYNC_OK: bool = bool(verify_path_sync().get("ok"))
