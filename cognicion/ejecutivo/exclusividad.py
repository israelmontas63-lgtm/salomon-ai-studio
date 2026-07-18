# -*- coding: utf-8 -*-
"""Exclusividad: este cerebro operativo es solo para Israel Montas."""

from __future__ import annotations

from typing import Any

OWNER = "Israel Montas"
OWNER_ALT = "Israel Monta"
PROTOCOLO = "CEREBRO_EJECUTIVO"
VERSION = "1.0.0"

DISCLAIMER = (
    "Información de apoyo a decisión. No es asesoría financiera regulada ni "
    "acceso a cuentas bancarias. Hallazgos = propiedad privada de Israel Montas."
)


def sello_propiedad(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    from cognicion.seguridad.sbi_pro import estado_sbi

    sbi = estado_sbi()
    return {
        "protocolo": PROTOCOLO,
        "version": VERSION,
        "owner": OWNER,
        "exclusividad": True,
        "propiedad_privada": True,
        "sbi": {
            "enabled": sbi.get("enabled"),
            "enrolled": sbi.get("enrolled"),
            "modo": sbi.get("modo"),
            "puerta": "SBI-PRO (enrollment recomendado antes de datos sensibles)",
        },
        "systemguard": "respetado",
        "disclaimer": DISCLAIMER,
        **(extra or {}),
    }


def exigir_contexto_israel(actor: str | None = None) -> dict[str, Any]:
    """No bloquea runtime local; documenta exclusividad en cada informe."""
    nombre = (actor or OWNER).strip()
    ok = nombre.lower() in {
        OWNER.lower(),
        OWNER_ALT.lower(),
        "israel",
    }
    return {
        "ok": ok,
        "actor": nombre,
        "mensaje": (
            "Contexto autorizado para Israel Montas."
            if ok
            else "Este módulo es exclusivo de Israel Montas."
        ),
    }
