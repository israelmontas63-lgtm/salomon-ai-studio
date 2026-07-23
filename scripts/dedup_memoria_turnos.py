# -*- coding: utf-8 -*-
"""
Deduplica turnos consecutivos idénticos (rol+contenido) en SQLite
y regenera hilos JSON desde SQLite (SoT).

Uso:
  python scripts/dedup_memoria_turnos.py
  python scripts/dedup_memoria_turnos.py --session SID
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def dedup_session(session_id: str) -> dict:
    from persistencia.sesiones import cargar_mensajes, guardar_mensaje, limpiar_sesion
    from mente.hilos import guardar_hilo

    msgs = cargar_mensajes(session_id) or []
    cleaned: list[dict] = []
    for m in msgs:
        rol = m.get("rol") or ""
        contenido = (m.get("contenido") or "").strip()
        if cleaned:
            prev = cleaned[-1]
            if prev.get("rol") == rol and (prev.get("contenido") or "").strip() == contenido:
                continue
        cleaned.append({"rol": rol, "contenido": contenido})

    removed = len(msgs) - len(cleaned)
    if removed <= 0:
        return {"session_id": session_id, "removed": 0, "kept": len(cleaned)}

    # Reescribir: limpiar proyecciones + SQLite y reinsertar
    limpiar_sesion(session_id)
    for m in cleaned:
        if m["rol"] in ("usuario", "asistente") and m["contenido"]:
            guardar_mensaje(session_id, m["rol"], m["contenido"][:8000])

    turnos = []
    for m in cleaned[-80:]:
        turnos.append(
            {
                "rol": "usuario" if m["rol"] == "usuario" else "asistente",
                "texto": m["contenido"][:4000],
                "area": "razonamiento",
                "origen": "dedup_sqlite",
            }
        )
    guardar_hilo(
        {
            "session_id": session_id,
            "turnos": turnos,
            "hechos": [],
            "estado": "dedup",
            "area_activa": "razonamiento",
        }
    )
    return {"session_id": session_id, "removed": removed, "kept": len(cleaned)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Dedup memoria turnos SQLite/hilos")
    parser.add_argument("--session", default="", help="Solo una session_id")
    args = parser.parse_args()

    from persistencia.sesiones import inicializar, listar_sesiones

    inicializar()
    if args.session:
        print(dedup_session(args.session))
        return 0

    total_removed = 0
    for row in listar_sesiones(limite=100):
        sid = row.get("session_id")
        if not sid:
            continue
        pack = dedup_session(sid)
        total_removed += int(pack.get("removed") or 0)
        if pack.get("removed"):
            print(pack)
    print({"ok": True, "total_removed": total_removed})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
