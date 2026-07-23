"""
Controlador unificado de memoria — fachada sobre SQLite, JSON personal y Chroma.
Observabilidad total: ningún fallo de escritura queda en silencio.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from cognicion.memoria.contexto_personal import (
    bloque_contexto,
    registrar_hecho,
)
from cognicion.memoria.gestor import GestorMemoria
from cognicion.memoria.vectorial import obtener_memoria
from persistencia.sesiones import ultimos_mensajes
from settings import ROOT_DIR

_log = logging.getLogger("salomon.memoria.controller")

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

        try:
            personal = (bloque_contexto() or "").strip()
        except Exception:
            _log.warning(
                "memory_controller.contexto: bloque_contexto falló session=%s",
                self.session_id,
                exc_info=True,
            )
            personal = ""
        if personal:
            bloques.append(personal)
            meta["personal"] = True

        try:
            proyecto, meta_proj = self._gestor.memoria_proyecto()
        except Exception:
            _log.warning(
                "memory_controller.contexto: memoria_proyecto falló session=%s",
                self.session_id,
                exc_info=True,
            )
            proyecto, meta_proj = "", {}
        if proyecto:
            bloques.append(proyecto)
            meta["proyecto"] = meta_proj

        if self._gestor.activa:
            try:
                from cognicion.memoria.tipos import CAPAS_RAG

                capas = [c.value for c in CAPAS_RAG]
                rag = obtener_memoria().contexto_rag(
                    consulta or "",
                    session_id=self.session_id,
                    capas=capas,
                )
                if rag:
                    bloques.append(rag)
                    meta["rag"] = {"capas_consultadas": capas, "rag_usado": True}
            except Exception:
                _log.warning(
                    "memory_controller.contexto: RAG falló session=%s",
                    self.session_id,
                    exc_info=True,
                )
                meta["rag_error"] = True

        snap = self._cargar_snapshot_sesion()
        if snap.get("hechos"):
            lineas = ["[Memoria de sesión — hechos recordados]"]
            for h in snap["hechos"][-12:]:
                lineas.append(f"- {h}")
            lineas.append(
                "Instrucción: Usa estos hechos solo como referencia interna. "
                "No los cites ni muestres etiquetas técnicas al usuario."
            )
            bloques.append("\n".join(lineas))
            meta["sesion_json"] = True

        return "\n\n".join(bloques).strip(), meta

    def recordar_turno(self, usuario: str, asistente: str) -> dict[str, Any]:
        """Delega en OrquestadorMemoriaUnificado (escritura multi-capa atómica)."""
        try:
            from cognicion.memoria.orquestador_memoria import (
                obtener_orquestador_memoria,
            )

            orch = obtener_orquestador_memoria(self.session_id)
            resultado = orch.guardar_turno(usuario or "", asistente or "")
            return {
                "hechos_nuevos": resultado.hechos_nuevos,
                "historial_turnos": len(
                    self._cargar_snapshot_sesion().get("historial") or []
                ),
                "vectorial": self.vectorial_activa,
                "snapshot_ok": bool(resultado.capas.get("snapshot")),
                "errores": resultado.errores,
                "capas": resultado.capas,
                "ok": resultado.ok,
                "via": "orquestador_memoria_unificado",
            }
        except Exception as exc:
            _log.warning(
                "memory_controller.recordar_turno: orquestador falló session=%s "
                "— degradando a snapshot local",
                self.session_id,
                exc_info=True,
            )
            # Degradación: al menos snapshot JSON para no perder el turno PWA
            snap = self._cargar_snapshot_sesion()
            hist = snap.setdefault("historial", [])
            if usuario:
                hist.append({"rol": "usuario", "contenido": (usuario or "")[:2000]})
            if asistente:
                hist.append({"rol": "asistente", "contenido": (asistente or "")[:4000]})
            snap["historial"] = hist[-80:]
            ok_snap = self._guardar_snapshot_sesion(snap)
            return {
                "hechos_nuevos": [],
                "historial_turnos": len(snap.get("historial") or []),
                "vectorial": self.vectorial_activa,
                "snapshot_ok": ok_snap,
                "errores": [f"orquestador:{type(exc).__name__}"],
                "ok": ok_snap,
                "via": "snapshot_fallback",
            }

    def historial_reciente(self, limite: int = 12) -> list[dict[str, str]]:
        try:
            rows = ultimos_mensajes(self.session_id, limite=limite)
        except Exception:
            _log.warning(
                "memory_controller.historial_reciente: SQLite falló session=%s",
                self.session_id,
                exc_info=True,
            )
            rows = []
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
            _log.warning(
                "memory_controller.registrar: registrar_hecho falló clave=%s",
                clave,
                exc_info=True,
            )
        snap = self._cargar_snapshot_sesion()
        hechos = snap.setdefault("hechos", [])
        if hecho not in hechos:
            hechos.append(hecho)
        snap["hechos"] = hechos[-40:]
        return self._guardar_snapshot_sesion(snap)

    def estado(self) -> dict[str, Any]:
        try:
            mem = obtener_memoria()
            vec_ok = bool(getattr(mem, "activa", False))
            motor = getattr(mem, "motor", "unknown")
        except Exception:
            _log.warning(
                "memory_controller.estado: obtener_memoria falló",
                exc_info=True,
            )
            vec_ok = False
            motor = "error"
        snap = self._cargar_snapshot_sesion()
        try:
            sqlite_n = len(ultimos_mensajes(self.session_id, limite=3))
        except Exception:
            _log.warning(
                "memory_controller.estado: SQLite falló",
                exc_info=True,
            )
            sqlite_n = 0
        return {
            "session_id": self.session_id,
            "vectorial_activa": vec_ok,
            "motor": motor,
            "hechos_sesion": len(snap.get("hechos") or []),
            "historial_sesion": len(snap.get("historial") or []),
            "sqlite_reciente": sqlite_n,
            "snapshot_path": str(_SESSIONS_JSON),
        }

    def _cargar_snapshot_sesion(self) -> dict[str, Any]:
        try:
            if _SESSIONS_JSON.is_file():
                data = json.loads(_SESSIONS_JSON.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    slot = data.get(self.session_id) or {
                        "hechos": [],
                        "historial": [],
                    }
                    if isinstance(slot, dict):
                        return dict(slot)
        except Exception:
            _log.warning(
                "memory_controller: lectura snapshot falló path=%s session=%s",
                _SESSIONS_JSON,
                self.session_id,
                exc_info=True,
            )
        return {"hechos": [], "historial": []}

    def _guardar_snapshot_sesion(self, snap: dict[str, Any]) -> bool:
        """Persiste snapshot JSON local. True si OK; False si falla (con warning)."""
        try:
            from cognicion.memoria.atomic_json import locked_update_json

            sid = self.session_id

            def _mut(root: dict[str, Any]) -> dict[str, Any]:
                if not isinstance(root, dict):
                    root = {}
                root[sid] = snap
                return root

            locked_update_json(_SESSIONS_JSON, _mut, default={})
            return True
        except Exception:
            _log.warning(
                "memory_controller: escritura snapshot falló path=%s session=%s",
                _SESSIONS_JSON,
                self.session_id,
                exc_info=True,
            )
            return False

    def borrar_snapshot_sesion(self) -> bool:
        """Quita el slot de esta sesión del JSON de snapshots."""
        try:
            from cognicion.memoria.atomic_json import locked_update_json

            sid = self.session_id

            def _mut(root: dict[str, Any]) -> dict[str, Any]:
                if isinstance(root, dict):
                    root.pop(sid, None)
                return root if isinstance(root, dict) else {}

            locked_update_json(_SESSIONS_JSON, _mut, default={})
            return True
        except Exception:
            _log.warning(
                "memory_controller: borrar snapshot falló session=%s",
                self.session_id,
                exc_info=True,
            )
            return False


def obtener_memory_controller(session_id: str) -> MemoryController:
    return MemoryController(session_id)
