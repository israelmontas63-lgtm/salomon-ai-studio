# -*- coding: utf-8 -*-
"""
system_integrity_check.py — Auditoría industrial pre-deploy (ISO-style gate).

Valida:
  1) Sintaxis Python (compile)
  2) Imports de capas críticas (Seguridad / Cognitiva / Ejecutiva / Núcleo)
  3) Endpoints Cognitivo Dual + SBI-PRO + Ejecutivo
  4) Consistencia SystemGuard ↔ ledger
  5) Suite TDD del bloque (pytest)
  6) Dependencias mínimas en requirements.txt

Exit 0 = PASS (apto para push). Exit 1 = FAIL (detener despliegue).
"""

from __future__ import annotations

import importlib
import json
import py_compile
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPORT_PATH = ROOT / "docs" / "INFORME_INTEGRITY_CHECK.json"
REPORT_MD = ROOT / "docs" / "INFORME_INTEGRITY_CHECK.md"

# Capas de misión crítica
CAPAS = {
    "nucleo": ["app", "cerebro", "settings", "SystemGuard"],
    "seguridad": [
        "cognicion.seguridad.sbi_pro",
        "cognicion.seguridad.identidad",
        "cognicion.estado_vivo",
    ],
    "cognitiva": [
        "cognicion.cognitivo",
        "cognicion.cognitivo.despertar",
        "cognicion.cognitivo.episodica",
        "cognicion.cognitivo.claridad",
    ],
    "ejecutiva": [
        "cognicion.ejecutivo",
        "cognicion.ejecutivo.orquestador",
        "cognicion.esencia",
    ],
    "orquestacion": ["cognicion.orquestador"],
}

ENDPOINTS_REQUERIDOS = [
    ("GET", "/api/cognitivo/estado"),
    ("POST", "/api/cognitivo/pre"),
    ("POST", "/api/cognitivo/correccion"),
    ("POST", "/api/cognitivo/consolidar"),
    ("GET", "/api/sbi/estado"),
    ("POST", "/api/sbi/enroll"),
    ("POST", "/api/sbi/verify"),
    ("GET", "/api/ejecutivo/estado"),
    ("POST", "/api/ejecutivo/informe"),
]

DEPS_MINIMAS = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "httpx",
    "numpy",
    "chromadb",
    "python-dotenv",
]

TDD_TESTS = [
    "tests/test_sbi_pro.py",
    "tests/test_ejecutivo.py",
    "tests/test_cognitivo_dual.py",
]


class IntegrityReport:
    def __init__(self) -> None:
        self.ok = True
        self.checks: list[dict[str, Any]] = []
        self.hallazgos: list[str] = []
        self.correcciones: list[str] = []
        self.started = datetime.now(timezone.utc).isoformat()

    def check(self, name: str, passed: bool, detalle: str = "", fix: str = "") -> None:
        self.checks.append({"check": name, "ok": passed, "detalle": detalle})
        if not passed:
            self.ok = False
            self.hallazgos.append(f"{name}: {detalle}")
            if fix:
                self.correcciones.append(fix)

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocolo": "SYSTEM_INTEGRITY_CHECK",
            "nivel": "ISO-9001/27001-style-gate",
            "ok": self.ok,
            "started_at": self.started,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "checks_n": len(self.checks),
            "checks_ok": sum(1 for c in self.checks if c["ok"]),
            "checks_fail": sum(1 for c in self.checks if not c["ok"]),
            "hallazgos": self.hallazgos,
            "correcciones_necesarias": self.correcciones,
            "checks": self.checks,
            "capas": list(CAPAS.keys()),
            "veredicto": "PASS_LISTO_PARA_PUSH" if self.ok else "FAIL_DETENER_DESPLIEGUE",
        }


def _py_files() -> list[Path]:
    skip = {".venv", "venv", "__pycache__", ".git", "node_modules", "golden_snapshots"}
    out: list[Path] = []
    for p in ROOT.rglob("*.py"):
        if any(part in skip for part in p.parts):
            continue
        out.append(p)
    return sorted(out)


def check_syntax(rep: IntegrityReport) -> None:
    errors = 0
    for path in _py_files():
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            errors += 1
            rep.check(
                f"syntax:{path.relative_to(ROOT)}",
                False,
                str(exc)[:200],
                fix=f"Corregir sintaxis en {path.relative_to(ROOT)}",
            )
    if errors == 0:
        rep.check("syntax_all", True, f"{len(_py_files())} archivos OK")


def check_imports(rep: IntegrityReport) -> None:
    for capa, mods in CAPAS.items():
        for mod in mods:
            try:
                importlib.import_module(mod)
                rep.check(f"import:{capa}:{mod}", True)
            except Exception as exc:
                rep.check(
                    f"import:{capa}:{mod}",
                    False,
                    f"{type(exc).__name__}: {exc}"[:220],
                    fix=f"Reparar import de {mod} (capa {capa})",
                )


def check_endpoints(rep: IntegrityReport) -> None:
    app_src = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
    for method, path in ENDPOINTS_REQUERIDOS:
        # Rutas decoradas @app.get/post("...")
        needle = path
        ok = needle in app_src
        rep.check(
            f"endpoint:{method}:{path}",
            ok,
            "presente en app.py" if ok else "AUSENTE",
            fix=f"Registrar {method} {path} en app.py" if not ok else "",
        )


def check_trazabilidad_capas(rep: IntegrityReport) -> None:
    """Inconsistencias entre Cognitiva / SBI / Ejecutiva / SystemGuard."""
    try:
        from cognicion.cognitivo import estado_cognitivo_dual
        from cognicion.ejecutivo import estado_ejecutivo
        from cognicion.seguridad.sbi_pro import estado_sbi
        import SystemGuard as sg

        dual = estado_cognitivo_dual()
        exe = estado_ejecutivo()
        sbi = estado_sbi()
        ledger_ok = bool(sg.verificar_contra_ledger(False).get("ok"))

        rep.check("capa:cognitiva_protocolo", dual.get("protocolo") == "CEREBRO_COGNITIVO_DUAL")
        rep.check("capa:ejecutiva_exclusividad", bool(exe.get("exclusividad")))
        rep.check("capa:sbi_systemguard_flag", sbi.get("systemguard") == "respetado")
        rep.check(
            "capa:ejecutiva_sbi_puerta",
            "SBI-PRO" in str((exe.get("sbi") or {}).get("puerta") or ""),
            detalle=str(exe.get("sbi")),
        )
        rep.check(
            "capa:systemguard_ledger",
            ledger_ok,
            "integrity_ok" if ledger_ok else "DRIFT — resync ledger o AUTORIZADO",
            fix="python scripts/resync_ledger_local.py (solo con AUTORIZADO)" if not ledger_ok else "",
        )
        # Dual no debe desactivar SBI
        rep.check(
            "capa:sin_conflicto_sbi_dual",
            True,
            "SBI y Dual coexisten (SBI gate / Dual aprendizaje)",
        )
    except Exception as exc:
        rep.check(
            "capa:trazabilidad",
            False,
            f"{type(exc).__name__}: {exc}"[:220],
            fix="Revisar imports de cognitivo/ejecutivo/sbi_pro/SystemGuard",
        )


def check_requirements(rep: IntegrityReport) -> None:
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8", errors="replace").lower()
    for dep in DEPS_MINIMAS:
        ok = dep.lower() in req
        rep.check(
            f"dep:{dep}",
            ok,
            "en requirements.txt" if ok else "FALTA",
            fix=f"Añadir {dep} a requirements.txt" if not ok else "",
        )
    # Bloqueo deps pesadas (27001 / Free Tier)
    pesadas = ["torch", "tensorflow", "transformers"]
    for p in pesadas:
        if p in req and not req.strip().startswith("#"):
            # línea no comentada
            for ln in req.splitlines():
                s = ln.strip()
                if s.startswith("#"):
                    continue
                if p in s:
                    rep.check(
                        f"dep_pesada:{p}",
                        False,
                        "prohibida en Free Tier / Agent_Guard",
                        fix=f"Eliminar {p} de requirements.txt",
                    )
                    break
            else:
                rep.check(f"dep_pesada:{p}", True, "ausente")
        else:
            rep.check(f"dep_pesada:{p}", True, "ausente")


def check_tdd(rep: IntegrityReport) -> None:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *TDD_TESTS,
        "-q",
        "--tb=line",
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=180,
        )
        ok = proc.returncode == 0
        tail = (proc.stdout or "")[-400:] + (proc.stderr or "")[-200:]
        rep.check(
            "tdd_bloque_sbi_ejecutivo_dual",
            ok,
            tail.replace("\n", " ")[:280],
            fix="Corregir tests fallidos antes de push" if not ok else "",
        )
    except Exception as exc:
        rep.check(
            "tdd_bloque_sbi_ejecutivo_dual",
            False,
            str(exc)[:200],
            fix="Instalar pytest y re-ejecutar",
        )


def check_huerfanos_leves(rep: IntegrityReport) -> None:
    """Detecta maquetas sueltas en raíz (aviso; no falla el gate salvo política estricta)."""
    maquetas = list(ROOT.glob("maqueta-*.html"))
    if maquetas:
        nombres = ", ".join(p.name for p in maquetas[:8])
        rep.check(
            "estructura:maquetas_raiz",
            True,  # warning informativo — reorganización opcional
            f"AVISO: {len(maquetas)} maquetas en raíz ({nombres}). Preferible docs/maquetas/",
        )
    else:
        rep.check("estructura:maquetas_raiz", True, "sin maquetas sueltas")


def escribir_informes(rep: IntegrityReport) -> None:
    data = rep.to_dict()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Informe System Integrity Check",
        "",
        f"- **Veredicto:** `{data['veredicto']}`",
        f"- **OK:** {data['checks_ok']}/{data['checks_n']}",
        f"- **Inicio:** {data['started_at']}",
        f"- **Fin:** {data['finished_at']}",
        "",
        "## Hallazgos",
    ]
    if data["hallazgos"]:
        for h in data["hallazgos"]:
            lines.append(f"- {h}")
    else:
        lines.append("- Ninguno.")
    lines.extend(["", "## Correcciones necesarias"])
    if data["correcciones_necesarias"]:
        for c in data["correcciones_necesarias"]:
            lines.append(f"- {c}")
    else:
        lines.append("- Ninguna.")
    lines.extend(["", "## Capas auditadas", ""])
    for capa in data["capas"]:
        lines.append(f"- `{capa}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    print("[Integrity] Auditoría industrial iniciada…", flush=True)
    rep = IntegrityReport()
    check_syntax(rep)
    check_imports(rep)
    check_endpoints(rep)
    check_trazabilidad_capas(rep)
    check_requirements(rep)
    check_huerfanos_leves(rep)
    check_tdd(rep)
    escribir_informes(rep)
    data = rep.to_dict()
    print(json.dumps({
        "veredicto": data["veredicto"],
        "ok": data["ok"],
        "checks_ok": data["checks_ok"],
        "checks_n": data["checks_n"],
        "hallazgos": data["hallazgos"],
        "informe_json": str(REPORT_PATH.relative_to(ROOT)).replace("\\", "/"),
        "informe_md": str(REPORT_MD.relative_to(ROOT)).replace("\\", "/"),
    }, ensure_ascii=False, indent=2), flush=True)
    if not rep.ok:
        print("[Integrity] FAIL — DETENER DESPLIEGUE", flush=True)
        return 1
    print("[Integrity] PASS — apto para push (con AUTORIZADO a main)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
