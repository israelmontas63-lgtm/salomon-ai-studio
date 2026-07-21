# -*- coding: utf-8 -*-
"""Shim de compatibilidad — implementación canónica en lib.system_guard."""
from lib.system_guard import *  # noqa: F403
from lib.system_guard import (  # noqa: F401
    CRITICAL_MAP,
    IntegrityViolation,
    ROOT,
    assert_writable,
    auto_reparar,
    boot_guard,
    crear_snapshot_salud,
    load_ledger,
    mapear_integridad,
    verificar_contra_ledger,
)
