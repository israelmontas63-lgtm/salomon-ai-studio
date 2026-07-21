# -*- coding: utf-8 -*-
"""
Orquestador de Memoria Unificada — fachada atómica por capas.

Escribe de forma síncrona e ininterrupida (best-effort ordenado) en:
  1) SQLite  → persistencia/sesiones.py
  2) Hilos   → data/mente/hilos/*.json
  3) Vectorial → cognicion/memoria/vectorial.py (metadatos sanitizados)
  4) Snapshot sesión JSON → data/memoria_sesiones.json

Evita estados huérfanos con verificación de integridad al iniciar sesión.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger("salomon.memoria.orquestador")


@dataclass
class ResultadoEscrituraMemoria:
    """Resultado de una escritura multi-capa."""

    ok: bool
    session_id: str
    capas: dict[str, bool] = field(default_factory=dict)
    errores: list[str] = field(default_factory=list)
    hechos_nuevos: list[str] = field(default_factory=list)
    integridad: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "session_id": self.session_id,
            "capas": dict(self.capas),
            "errores": list(self.errores),
            "hechos_nuevos": list(self.hechos_nuevos),
            "integridad": dict(self.integridad),
        }


class OrquestadorMemoriaUnificado:
    """
    API de punto único para turnos, hechos y proyectos.
    Tipado estricto + logging con exc_info (sin fallos silenciosos).
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = (session_id or "default").strip() or "default"
        self._integridad_cache: dict[str, Any] | None = None

    # ── Inicialización / integridad ─────────────────────────────────────

    def inicializar_sesion(self) -> dict[str, Any]:
        """
        Asegura sesión SQLite + alinea hilos JSON con registros recientes.
        Auto-repara desfasajes temporales de forma transparente.
        """
        reporte: dict[str, Any] = {
            "session_id": self.session_id,
            "sqlite_ok": False,
            "reparado": False,
            "turnos_sqlite": 0,
            "turnos_hilo": 0,
        }
        try:
            from persistencia.sesiones import asegurar_sesion, inicializar

            inicializar()
            asegurar_sesion(self.session_id)
            reporte["sqlite_ok"] = True
        except Exception as exc:
            reporte["errores"] = [f"sqlite_init:{type(exc).__name__}"]
            _log.warning(
                "orquestador_memoria.inicializar_sesion: SQLite falló session=%s",
                self.session_id,
                exc_info=True,
            )

        integridad = self.verificar_integridad(reparar=True)
        reporte["integridad"] = integridad
        reporte["reparado"] = bool(integridad.get("reparado"))
        reporte["turnos_sqlite"] = int(integridad.get("turnos_sqlite") or 0)
        reporte["turnos_hilo"] = int(integridad.get("turnos_hilo") or 0)
        self._integridad_cache = integridad
        return reporte

    def verificar_integridad(self, *, reparar: bool = True) -> dict[str, Any]:
        """Compara hilos JSON vs SQLite; rellena el hilo si está atrasado."""
        out: dict[str, Any] = {
            "alineado": True,
            "reparado": False,
            "turnos_sqlite": 0,
            "turnos_hilo": 0,
            "delta": 0,
        }
        sqlite_msgs: list[dict[str, str]] = []
        try:
            from persistencia.sesiones import ultimos_mensajes

            sqlite_msgs = ultimos_mensajes(self.session_id, limite=40) or []
            out["turnos_sqlite"] = len(sqlite_msgs)
        except Exception:
            _log.warning(
                "orquestador_memoria.integridad: lectura SQLite falló session=%s",
                self.session_id,
                exc_info=True,
            )

        hilo: dict[str, Any] = {}
        try:
            from mente.hilos import cargar_hilo

            hilo = cargar_hilo(self.session_id)
            turnos_h = list(hilo.get("turnos") or [])
            out["turnos_hilo"] = len(turnos_h)
        except Exception:
            _log.warning(
                "orquestador_memoria.integridad: lectura hilo falló session=%s",
                self.session_id,
                exc_info=True,
            )
            turnos_h = []

        delta = out["turnos_sqlite"] - out["turnos_hilo"]
        out["delta"] = delta
        if abs(delta) <= 1:
            out["alineado"] = True
            return out

        out["alineado"] = False
        if not reparar or not sqlite_msgs:
            return out

        # Auto-reparación: reconstruir cola del hilo desde SQLite (sin borrar hechos)
        try:
            from mente.hilos import guardar_hilo

            nuevos = []
            for m in sqlite_msgs[-80:]:
                rol = "usuario" if m.get("rol") == "usuario" else "asistente"
                nuevos.append(
                    {
                        "at": m.get("creado_en") or m.get("at") or "",
                        "rol": rol,
                        "texto": (m.get("contenido") or "")[:4000],
                        "area": "razonamiento",
                        "origen": "integridad_sqlite",
                    }
                )
            hilo = hilo or {"session_id": self.session_id, "hechos": [], "estado": "reparado"}
            hilo["session_id"] = self.session_id
            hilo["turnos"] = nuevos
            hilo["estado"] = "reparado_integridad"
            guardar_hilo(hilo)
            out["reparado"] = True
            out["turnos_hilo"] = len(nuevos)
            out["alineado"] = True
            _log.warning(
                "orquestador_memoria.integridad: hilo reparado desde SQLite "
                "session=%s delta_prev=%s",
                self.session_id,
                delta,
            )
        except Exception:
            _log.warning(
                "orquestador_memoria.integridad: reparación falló session=%s",
                self.session_id,
                exc_info=True,
            )
        return out

    # ── Escritura atómica de turno ──────────────────────────────────────

    def guardar_turno(
        self,
        usuario: str,
        asistente: str,
        *,
        area: str = "razonamiento",
        aprender: bool = True,
    ) -> ResultadoEscrituraMemoria:
        """
        Escritura síncrona multi-capa. No interrumpe la PWA si una capa falla;
        registra warning con traza y continúa con las restantes.
        """
        if self._integridad_cache is None:
            try:
                self.inicializar_sesion()
            except Exception:
                _log.warning(
                    "orquestador_memoria.guardar_turno: init falló session=%s",
                    self.session_id,
                    exc_info=True,
                )

        u = (usuario or "").strip()
        a = (asistente or "").strip()
        res = ResultadoEscrituraMemoria(ok=False, session_id=self.session_id)
        capas: dict[str, bool] = {
            "sqlite": False,
            "hilos_json": False,
            "vectorial": False,
            "snapshot": False,
            "hechos": False,
        }

        # 1) SQLite (fuente relacional)
        try:
            from persistencia.sesiones import asegurar_sesion, guardar_mensaje, inicializar

            inicializar()
            asegurar_sesion(self.session_id)
            if u:
                guardar_mensaje(self.session_id, "usuario", u[:8000])
            if a:
                guardar_mensaje(self.session_id, "asistente", a[:8000])
            capas["sqlite"] = True
        except Exception as exc:
            res.errores.append(f"sqlite:{type(exc).__name__}")
            _log.warning(
                "orquestador_memoria: SQLite guardar_turno falló session=%s",
                self.session_id,
                exc_info=True,
            )

        # 2) Hilos JSON (data/mente/hilos)
        try:
            from mente.hilos import registrar_turno as reg_hilo

            if u:
                reg_hilo(self.session_id, rol="usuario", texto=u, area=area)
            if a:
                reg_hilo(self.session_id, rol="asistente", texto=a, area=area)
            capas["hilos_json"] = True
        except Exception as exc:
            res.errores.append(f"hilos:{type(exc).__name__}")
            _log.warning(
                "orquestador_memoria: hilos JSON falló session=%s",
                self.session_id,
                exc_info=True,
            )

        # 3) Vectorial (metadatos ya sanitizados en vectorial.guardar)
        try:
            from cognicion.memoria.vectorial import obtener_memoria

            mem = obtener_memoria()
            if mem.activa and (u or a):
                mid = mem.guardar(
                    f"Usuario: {u}\nSalomón: {a}",
                    metadata={
                        "tipo": "turno",
                        "categoria": "conversacion",
                        "capa": "temporal",
                        "sesion_id": self.session_id,
                        "aprendizaje": bool(aprender),
                        "nested_probe": None,  # sanitizer debe descartar
                    },
                )
                capas["vectorial"] = bool(mid)
                if not mid:
                    res.errores.append("vectorial:sin_id")
                    _log.warning(
                        "orquestador_memoria: vectorial sin id session=%s",
                        self.session_id,
                    )
            else:
                _log.warning(
                    "orquestador_memoria: vectorial inactiva session=%s motor=%s",
                    self.session_id,
                    getattr(mem, "motor", "?"),
                )
                res.errores.append("vectorial:inactiva")
        except Exception as exc:
            res.errores.append(f"vectorial:{type(exc).__name__}")
            _log.warning(
                "orquestador_memoria: vectorial falló session=%s",
                self.session_id,
                exc_info=True,
            )

        # 4) Aprendizaje de hechos + snapshot JSON de sesión
        hechos: list[str] = []
        if aprender and u:
            try:
                from cognicion.memoria.contexto_personal import extraer_y_aprender

                hechos = extraer_y_aprender(u) or []
                capas["hechos"] = True
                res.hechos_nuevos = list(hechos)
            except Exception as exc:
                res.errores.append(f"hechos:{type(exc).__name__}")
                _log.warning(
                    "orquestador_memoria: extraer_y_aprender falló session=%s",
                    self.session_id,
                    exc_info=True,
                )

        try:
            from cognicion.memoria.memory_controller import MemoryController

            mc = MemoryController(self.session_id)
            snap = mc._cargar_snapshot_sesion()
            hist = snap.setdefault("historial", [])
            if u:
                hist.append({"rol": "usuario", "contenido": u[:2000]})
            if a:
                hist.append({"rol": "asistente", "contenido": a[:4000]})
            snap["historial"] = hist[-80:]
            hechos_sesion = snap.setdefault("hechos", [])
            for h in hechos:
                if h and h not in hechos_sesion:
                    hechos_sesion.append(h)
            snap["hechos"] = hechos_sesion[-40:]
            capas["snapshot"] = bool(mc._guardar_snapshot_sesion(snap))
            if not capas["snapshot"]:
                res.errores.append("snapshot:write_fail")
        except Exception as exc:
            res.errores.append(f"snapshot:{type(exc).__name__}")
            _log.warning(
                "orquestador_memoria: snapshot falló session=%s",
                self.session_id,
                exc_info=True,
            )

        res.capas = capas
        # OK si al menos una capa persistente (sqlite o hilos o snapshot) escribió
        res.ok = bool(capas.get("sqlite") or capas.get("hilos_json") or capas.get("snapshot"))
        res.integridad = self._integridad_cache or {}
        return res

    def guardar_hecho(
        self,
        clave: str,
        valor: str,
        *,
        capa: str = "preferencias",
    ) -> ResultadoEscrituraMemoria:
        """Persiste un hecho en JSON personal + vectorial."""
        res = ResultadoEscrituraMemoria(ok=False, session_id=self.session_id)
        try:
            from cognicion.memoria.contexto_personal import registrar_hecho

            registrar_hecho(clave, valor, capa)
            res.capas["hechos_json"] = True
            res.hechos_nuevos = [clave]
            res.ok = True
        except Exception as exc:
            res.errores.append(f"hecho:{type(exc).__name__}")
            _log.warning(
                "orquestador_memoria.guardar_hecho falló clave=%s",
                clave,
                exc_info=True,
            )
        return res

    def guardar_proyecto(
        self,
        nombre: str,
        nota: str = "",
    ) -> ResultadoEscrituraMemoria:
        """Proyecto en SQLite + vectorial capa proyecto + hecho personal."""
        res = ResultadoEscrituraMemoria(ok=False, session_id=self.session_id)
        capas: dict[str, bool] = {}
        try:
            from persistencia.sesiones import guardar_proyecto as gp_sql

            gp_sql(self.session_id, nombre=nombre, nota=nota or None)
            capas["sqlite_proyecto"] = True
        except Exception as exc:
            res.errores.append(f"proyecto_sql:{type(exc).__name__}")
            _log.warning(
                "orquestador_memoria.guardar_proyecto SQLite falló",
                exc_info=True,
            )
        try:
            from cognicion.memoria.vectorial import obtener_memoria

            mid = obtener_memoria().guardar_en_capa(
                f"Proyecto: {nombre}. {nota}".strip(),
                "proyecto",
                session_id=self.session_id,
                categoria="proyecto",
                origen="orquestador",
            )
            capas["vectorial"] = bool(mid)
        except Exception as exc:
            res.errores.append(f"proyecto_vec:{type(exc).__name__}")
            _log.warning(
                "orquestador_memoria.guardar_proyecto vectorial falló",
                exc_info=True,
            )
        try:
            from cognicion.memoria.contexto_personal import registrar_hecho

            registrar_hecho(f"proyecto_{nombre[:40]}", f"{nombre}: {nota}"[:300], "proyecto")
            capas["hechos"] = True
        except Exception as exc:
            res.errores.append(f"proyecto_hecho:{type(exc).__name__}")
            _log.warning(
                "orquestador_memoria.guardar_proyecto hecho falló",
                exc_info=True,
            )
        res.capas = capas
        res.ok = any(capas.values())
        return res


def obtener_orquestador_memoria(session_id: str) -> OrquestadorMemoriaUnificado:
    return OrquestadorMemoriaUnificado(session_id)
