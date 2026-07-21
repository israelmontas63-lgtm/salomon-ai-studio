# [FILE: core_salomon_final_live_integration_gate.py]
"""Gate final de integración en vivo: FastAPI, WAL, rutas críticas, PWA."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

import sys

# Al ejecutar como script, sys.path[0] = cognicion/ y sombrea el paquete config/
_cognicion_dir = str((ROOT / "cognicion").resolve())
sys.path[:] = [p for p in sys.path if str(Path(p).resolve()) != _cognicion_dir]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class SalomonFinalLiveIntegrationGate:
    MODULE = "SalomonFinalLiveIntegrationGate"
    VERSION = "110.16.1"

    def run_local(self) -> dict[str, Any]:
        from fastapi.testclient import TestClient

        import app as appmod
        from persistencia.sesiones import _conexion

        conn = _conexion()
        wal = str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        conn.close()

        client = TestClient(appmod.app)
        checks: list[dict[str, Any]] = []

        def add(name: str, ok: bool, **extra: Any) -> None:
            checks.append({"name": name, "ok": ok, **extra})

        add("app_is_fastapi", type(appmod.app).__name__ == "FastAPI")
        add("sqlite_wal", wal == "wal", journal=wal)

        for method, path in (
            ("GET", "/api/salud"),
            ("GET", "/api/version"),
            ("GET", "/version.json"),
            ("GET", "/api/ai/lock"),
        ):
            r = getattr(client, method.lower())(path)
            add(path, r.status_code == 200, status=r.status_code)

        r = client.post("/api/ai/secondary", json={"accion": "ping"})
        add("/api/ai/secondary", r.status_code == 200, status=r.status_code)

        r = client.post("/api/tts", json={"texto": "Prueba breve."})
        add("/api/tts", r.status_code == 200, status=r.status_code)

        r = client.post(
            "/api/ai/central-button",
            json={"mensaje": "Hola Salomon, prueba de integracion final."},
        )
        pack = r.json() if r.content else {}
        brain = pack.get("brain") if isinstance(pack.get("brain"), dict) else {}
        texto = str(brain.get("texto") or pack.get("texto") or "")
        add(
            "/api/ai/central-button",
            r.status_code == 200 and bool(texto.strip()) and pack.get("ok") is not False,
            status=r.status_code,
            texto_len=len(texto),
            ok_flag=pack.get("ok"),
            error=str(pack.get("error") or "")[:120] or None,
        )

        # Visión sin frame: no debe tumbar el proceso (validación mime)
        tiny = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQ"
            "AAAABJRU5ErkJggg=="
        )
        r = client.post(
            "/api/vision/brain-bridge",
            json={
                "contexto": "Describe brevemente.",
                "imagen_base64": tiny,
                "imagen_mime": "image/png",
                "via_brain_bridge": True,
            },
        )
        add(
            "/api/vision/brain-bridge",
            r.status_code == 200,
            status=r.status_code,
        )

        # Assets PWA / smart button
        for rel in (
            "static/js/components/SmartButton.js",
            "static/js/voice_layer.js",
            "static/js/vision_engine.js",
            "static/js/service-worker.js",
            "version.json",
        ):
            add(rel, (ROOT / rel).is_file())

        ok = all(c.get("ok") for c in checks)
        return {
            "module": self.MODULE,
            "version": self.VERSION,
            "ok": ok,
            "checks": checks,
            "backend": "FastAPI",
        }


def run_gate() -> dict[str, Any]:
    return SalomonFinalLiveIntegrationGate().run_local()


if __name__ == "__main__":
    print(json.dumps(run_gate(), indent=2, ensure_ascii=False))
