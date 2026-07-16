"""
Controlador unificado de memoria — fachada sobre SQLite, JSON personal y Chroma.
No altera el system prompt; solo persiste y recupera contexto.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cognicion.memoria.contexto_personal import (
    bloque_contexto,
    extraer_y_aprender,
    registrar_hecho,
)
from cognicion.memoria.gestor import GestorMemoria
from cognicion.memoria.vectorial import obtener_memoria
from persistencia.sesiones import ultimos_mensajes
from settings import ROOT_DIR

_SESSIONS_JSON = Path(ROOT_DIR) / "data" / "memoria_sesiones.json"


class MemoryController:
    """API única para guardar/recuperar memoria de sesión y hechos."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id or "default"
        self._gestor = GestorMemoria(self.session_id)

    @property
    def vectorial_activa(self) -> bool:
        return bool(self._gestor.activa)

    def contexto_para_turno(self, consulta: str) -> tuple[str, dict[str, Any]]:
        """Bloque de contexto (inmediata + proyecto + RAG + personal)."""
        meta: dict[str, Any] = {
            "session_id": self.session_id,
            "vectorial": self.vectorial_activa,
        }
        bloques: list[str] = []

        personal = (bloque_contexto() or "").strip()
        if personal:
            bloques.append(personal)
            meta["personal"] = True

        inmediata = self._gestor.memoria_inmediata(limite=8)
        if inmediata:
            bloques.append(inmediata)
            meta["inmediata"] = True

        rag, meta_rag = self._gestor.contexto_rag(consulta or "")
        if rag:
            bloques.append(rag)
            meta["rag"] = meta_rag

        # Fallback JSON de sesiones (ligero, siempre disponible)
        snap = self._cargar_snapshot_sesion()
        if snap.get("hechos"):
            lineas = ["[Memoria de sesión — hechos recordados]"]
            for h in snap["hechos"][-12:]:
                lineas.append(f"- {h}")
            bloques.append("\n".join(lineas))
            meta["sesion_json"] = True

        return "\n\n".join(bloques).strip(), meta

    def recordar_turno(self, usuario: str, asistente: str) -> dict[str, Any]:
        """Aprende del turno y persiste snapshot local."""
        hechos = extraer_y_aprender(usuario or "")
        try:
            self._gestor.guardar_turno(usuario or "", asistente or "")
        except Exception:
            pass

        snap = self._cargar_snapshot_sesion()
        hist = snap.setdefault("historial", [])
        if usuario:
            hist.append({"rol": "usuario", "contenido": (usuario or "")[:2000]})
        if asistente:
            hist.append({"rol": "asistente", "contenido": (asistente or "")[:4000]})
        snap["historial"] = hist[-80:]

        hechos_sesion = snap.setdefault("hechos", [])
        for h in hechos or []:
            if h and h not in hechos_sesion:
                hechos_sesion.append(h)
        # También indexar frases "me llamo / mi proyecto"
        for m in (usuario or "",):
            low = m.lower()
            if "mi proyecto" in low or "se llama" in low or "me llamo" in low:
                if m.strip() and m.strip() not in hechos_sesion:
                    hechos_sesion.append(m.strip()[:300])
        snap["hechos"] = hechos_sesion[-40:]
        self._guardar_snapshot_sesion(snap)

        return {
            "hechos_nuevos": hechos or [],
            "historial_turnos": len(snap["historial"]),
            "vectorial": self.vectorial_activa,
        }

    def historial_reciente(self, limite: int = 12) -> list[dict[str, str]]:
        rows = ultimos_mensajes(self.session_id, limite=limite)
        if rows:
            return [{"rol": r["rol"], "contenido": r["contenido"]} for r in rows]
        snap = self._cargar_snapshot_sesion()
        return list(snap.get("historial") or [])[-limite:]

    def registrar(self, hecho: str, *, categoria: str = "general") -> bool:
        hecho = (hecho or "").strip()
        if not hecho:
            return False
        clave = f"sesion_{categoria}_{abs(hash(hecho)) % 10_000_000}"
        try:
            registrar_hecho(clave, hecho, categoria)
        except Exception:
            pass
        snap = self._cargar_snapshot_sesion()
        hechos = snap.setdefault("hechos", [])
        if hecho not in hechos:
            hechos.append(hecho)
        snap["hechos"] = hechos[-40:]
        self._guardar_snapshot_sesion(snap)
        return True

    def estado(self) -> dict[str, Any]:
        mem = obtener_memoria()
        snap = self._cargar_snapshot_sesion()
        return {
            "session_id": self.session_id,
            "vectorial_activa": bool(getattr(mem, "activa", False)),
            "hechos_sesion": len(snap.get("hechos") or []),
            "historial_sesion": len(snap.get("historial") or []),
            "sqlite_reciente": len(ultimos_mensajes(self.session_id, limite=3)),
        }

    def _cargar_snapshot_sesion(self) -> dict[str, Any]:
        try:
            if _SESSIONS_JSON.is_file():
                data = json.loads(_SESSIONS_JSON.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return dict(data.get(self.session_id) or {"hechos": [], "historial": []})
        except Exception:
            pass
        return {"hechos": [], "historial": []}

    def _guardar_snapshot_sesion(self, snap: dict[str, Any]) -> None:
        try:
            _SESSIONS_JSON.parent.mkdir(parents=True, exist_ok=True)
            root: dict[str, Any] = {}
            if _SESSIONS_JSON.is_file():
                try:
                    root = json.loads(_SESSIONS_JSON.read_text(encoding="utf-8"))
                    if not isinstance(root, dict):
                        root = {}
                except Exception:
                    root = {}
            root[self.session_id] = snap
            _SESSIONS_JSON.write_text(
                json.dumps(root, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass


def obtener_memory_controller(session_id: str) -> MemoryController:
    return MemoryController(session_id)
