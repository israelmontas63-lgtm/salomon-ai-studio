# -*- coding: utf-8 -*-
"""Smoke: 1 turno → 2 filas SQLite; limpiar → vacío; CORS no *."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_single_writer() -> None:
    from cognicion.memoria.orquestador_memoria import obtener_orquestador_memoria
    from persistencia.sesiones import cargar_mensajes, inicializar, limpiar_sesion
    from mente.hilos import cargar_hilo

    inicializar()
    sid = f"test-mem-{uuid.uuid4().hex[:10]}"
    try:
        orch = obtener_orquestador_memoria(sid)
        orch.guardar_turno("hola israel", "hola, aquí estoy", aprender=False)
        msgs = cargar_mensajes(sid) or []
        assert len(msgs) == 2, f"esperaba 2 filas, got {len(msgs)}"
        assert msgs[0]["rol"] == "usuario"
        assert msgs[1]["rol"] == "asistente"
        hilo = cargar_hilo(sid)
        turnos = hilo.get("turnos") or []
        assert len(turnos) == 2, f"esperaba 2 hilos, got {len(turnos)}"

        # Segunda escritura orquestador no debe duplicar vía app (aquí solo orquestador)
        limpiar_sesion(sid)
        msgs2 = cargar_mensajes(sid) or []
        assert msgs2 == [], f"tras limpiar esperaba vacío, got {len(msgs2)}"
        hilo2 = cargar_hilo(sid)
        assert not (hilo2.get("turnos") or []), "hilo debía vaciarse"
        print("OK test_single_writer", sid)
    finally:
        try:
            limpiar_sesion(sid)
        except Exception:
            pass


def test_cors_not_star() -> None:
    import app as app_mod

    origins = getattr(app_mod, "_CORS_ORIGINS", None)
    assert origins is not None
    assert "*" not in origins, "CORS no debe ser *"
    assert any("onrender.com" in o for o in origins)
    assert "/api/deploy/finalize" not in app_mod.RUTAS_API_PUBLICAS
    assert "/api/chat" in app_mod.RUTAS_API_PUBLICAS
    print("OK test_cors_not_star", origins[:3])


def test_atomic_json() -> None:
    import tempfile
    from pathlib import Path
    from cognicion.memoria.atomic_json import atomic_write_json, locked_update_json

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.json"
        assert atomic_write_json(p, {"a": 1})
        assert p.is_file()

        def mut(d):
            d["b"] = 2
            return d

        locked_update_json(p, mut, default={})
        import json

        data = json.loads(p.read_text(encoding="utf-8"))
        assert data.get("a") == 1 and data.get("b") == 2
    print("OK test_atomic_json")


if __name__ == "__main__":
    test_atomic_json()
    test_cors_not_star()
    test_single_writer()
    print("ALL_OK")
