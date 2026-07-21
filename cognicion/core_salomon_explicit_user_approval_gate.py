# [FILE: core_salomon_explicit_user_approval_gate.py]
# Motor de Control Humano y Aprobación Explícita (Salomón AI)
"""Gate de soberanía: cero cambios a producción sin aprobación explícita de Israel."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class SalomonUserApprovalGate:
    """Lista pendientes y exige run humano antes de commit/push."""

    MODULE = "SalomonUserApprovalGate"
    STATUS = "EXPLICIT_APPROVAL_GATE_ACTIVE"
    VERSION = "110.16.2"

    def __init__(self) -> None:
        self.module = self.MODULE
        self.status = self.STATUS
        self.root = ROOT

    def audit_pending_approvals(self) -> dict[str, Any]:
        pending_files: list[str] = []
        try:
            out = subprocess.check_output(
                ["git", "status", "--porcelain"],
                cwd=str(self.root),
                text=True,
                timeout=30,
            )
            pending_files = [ln.strip() for ln in out.splitlines() if ln.strip()]
        except Exception as exc:
            pending_files = [f"git_status_error:{type(exc).__name__}"]

        return {
            "action": (
                "Halt all unapproved changes. List any pending file updates, "
                "cache modifications, or unexecuted scripts for Israel's "
                "explicit review and run command."
            ),
            "policy": "Zero changes without explicit human approval.",
            "deployment": (
                "On-hold pending user confirmation -> Auto-commit -> "
                "Render push -> PWA refresh."
            ),
            "status": self.status,
            "version": self.VERSION,
            "pending_working_tree": pending_files,
            "module_path": "cognicion/core_salomon_explicit_user_approval_gate.py",
            "badge": "settings_gear_update_manager_active",
        }

    def as_json(self) -> str:
        return json.dumps(self.audit_pending_approvals(), indent=2, ensure_ascii=False)


def audit_pending() -> dict[str, Any]:
    return SalomonUserApprovalGate().audit_pending_approvals()


if __name__ == "__main__":
    gate = SalomonUserApprovalGate()
    print("[ACTIVANDO FILTRO DE APROBACIÓN HUMANA - SALOMÓN AI]")
    print(gate.as_json())
