"""
Colsub — colas de trabajo + auto-diagnóstico de enjambres.

Arquitectura de colas: las consultas entran a una cola FIFO;
el Orquestador de Carga las consume respetando CPU/RAM y el
escalado on-demand (1–40 agentes).
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrabajoCola:
    id: str
    mensaje: str
    session_id: str | None = None
    prioridad: int = 5  # 1 alta … 10 baja
    forzar_n: int | None = None
    creado_en: float = field(default_factory=time.time)
    estado: str = "en_cola"  # en_cola | procesando | listo | error
    resultado: dict[str, Any] | None = None
    error: str | None = None


class OrquestadorDeCarga:
    """
    Gestor de colas de Colsub.
    - Encola consultas de alto rendimiento
    - Procesa una a una (o con workers limitados)
    - No lanza nuevos trabajos si CPU/RAM están críticos
    """

    def __init__(self, max_workers: int = 2) -> None:
        self._cola: deque[TrabajoCola] = deque()
        self._lock = threading.Lock()
        self._resultados: dict[str, TrabajoCola] = {}
        self._activo = True
        self._procesando = 0
        self._max_workers = max(1, min(4, max_workers))
        self._total_encolados = 0
        self._total_completados = 0
        self._worker_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._iniciar_worker()

    def _iniciar_worker(self) -> None:
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._stop.clear()
        self._worker_thread = threading.Thread(
            target=self._bucle,
            name="colsub-orquestador-carga",
            daemon=True,
        )
        self._worker_thread.start()

    @property
    def activo(self) -> bool:
        return self._activo and bool(
            self._worker_thread and self._worker_thread.is_alive()
        )

    def encolar(
        self,
        mensaje: str,
        *,
        session_id: str | None = None,
        prioridad: int = 5,
        forzar_n: int | None = None,
    ) -> str:
        job = TrabajoCola(
            id=uuid.uuid4().hex[:12],
            mensaje=(mensaje or "").strip(),
            session_id=session_id,
            prioridad=max(1, min(10, int(prioridad))),
            forzar_n=forzar_n,
        )
        with self._lock:
            self._cola.append(job)
            # Reordenar por prioridad
            items = sorted(self._cola, key=lambda j: (j.prioridad, j.creado_en))
            self._cola = deque(items)
            self._resultados[job.id] = job
            self._total_encolados += 1
        return job.id

    def estado_trabajo(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._resultados.get(job_id)
            if not job:
                return None
            return {
                "id": job.id,
                "estado": job.estado,
                "prioridad": job.prioridad,
                "mensaje": job.mensaje[:200],
                "resultado": job.resultado,
                "error": job.error,
                "espera_s": round(time.time() - job.creado_en, 2),
            }

    def snapshot(self) -> dict[str, Any]:
        from cognicion.orquesta.colsub import recursos_criticos

        critico, rec = recursos_criticos()
        with self._lock:
            return {
                "nombre": "Orquestador de Carga",
                "activo": self.activo,
                "arquitectura": "colas",
                "en_cola": len(self._cola),
                "procesando": self._procesando,
                "completados": self._total_completados,
                "encolados_total": self._total_encolados,
                "max_workers": self._max_workers,
                "recursos_criticos": critico,
                "recursos": rec,
            }

    def _siguiente(self) -> TrabajoCola | None:
        with self._lock:
            if self._procesando >= self._max_workers:
                return None
            if not self._cola:
                return None
            job = self._cola.popleft()
            job.estado = "procesando"
            self._procesando += 1
            return job

    def _finalizar(self, job: TrabajoCola) -> None:
        with self._lock:
            self._procesando = max(0, self._procesando - 1)
            self._total_completados += 1
            self._resultados[job.id] = job

    def _bucle(self) -> None:
        from cognicion.orquesta.colsub import colsub_desplegar, recursos_criticos

        while not self._stop.is_set():
            critico, _ = recursos_criticos()
            if critico:
                time.sleep(0.4)
                continue
            job = self._siguiente()
            if not job:
                time.sleep(0.15)
                continue
            try:
                pack = colsub_desplegar(
                    job.mensaje,
                    forzar_n=job.forzar_n,
                )
                job.resultado = {
                    "respuesta": pack.get("texto_sintesis"),
                    "hallazgos_agentes": {
                        "exito": pack.get("exito"),
                        "agentes_ok": pack.get("agentes_ok"),
                        "agentes_fallidos": pack.get("agentes_fallidos"),
                        "colsub": pack.get("colsub"),
                        "informes": pack.get("informes"),
                    },
                    "colsub": pack.get("colsub"),
                }
                job.estado = "listo"
            except Exception as exc:
                job.estado = "error"
                job.error = type(exc).__name__
            finally:
                self._finalizar(job)

    def detener(self) -> None:
        self._activo = False
        self._stop.set()


_ORQUESTADOR: OrquestadorDeCarga | None = None
_ORQ_LOCK = threading.Lock()


def obtener_orquestador_carga() -> OrquestadorDeCarga:
    global _ORQUESTADOR
    with _ORQ_LOCK:
        if _ORQUESTADOR is None or not _ORQUESTADOR.activo:
            from settings import COLSUB_MAX_WORKERS

            _ORQUESTADOR = OrquestadorDeCarga(
                max_workers=min(2, max(1, COLSUB_MAX_WORKERS // 4 or 1))
            )
        return _ORQUESTADOR


def autodiagnostico_enjambres() -> dict[str, Any]:
    """
    Protocolo de auto-diagnóstico de enjambres Colsub.
    Verifica: módulos, recursos, escalado, cola, grafo.
    """
    checks: list[dict[str, Any]] = []

    def _ok(nombre: str, ok: bool, detalle: str = "") -> None:
        checks.append({"check": nombre, "ok": ok, "detalle": detalle})

    # 1) Módulo Colsub
    try:
        from cognicion.orquesta.colsub import (
            colsub_desplegar,
            puntuacion_complejidad,
            recursos_criticos,
        )

        _ok("modulo_colsub", True, "cargado")
    except Exception as exc:
        _ok("modulo_colsub", False, type(exc).__name__)
        return {"exito": False, "protocolo": "autodiagnostico_enjambres", "checks": checks}

    # 2) Recursos
    critico, rec = recursos_criticos()
    _ok(
        "orquestador_recursos",
        not critico,
        f"cpu={rec.get('cpu')} ram={rec.get('ram')} critico={critico}",
    )

    # 3) Escalado on-demand
    simple = puntuacion_complejidad("Hola")
    compleja = puntuacion_complejidad(
        "Investiga a fondo impacto económico científico y estratégico "
        "comparando fuentes académicas y de mercado desde varios ángulos"
    )
    escala_ok = (
        simple["agentes_recomendados"] <= 3
        and compleja["agentes_recomendados"] >= 6
    )
    _ok(
        "escalado_ondemand",
        escala_ok,
        f"simple={simple['agentes_recomendados']} compleja={compleja['agentes_recomendados']}",
    )

    # 4) Orquestador de carga / colas
    orq = obtener_orquestador_carga()
    snap = orq.snapshot()
    _ok("orquestador_carga_activo", orq.activo, snap.get("arquitectura", ""))
    _ok("arquitectura_colas", snap.get("arquitectura") == "colas", "FIFO+prioridad")

    # 5) Enjambre mínimo (1 agente)
    try:
        pack = colsub_desplegar("diagnostico enjambre colsub", forzar_n=1)
        _ok(
            "enjambre_minimo",
            bool(pack.get("exito") or pack.get("texto_sintesis")),
            f"lanzados={pack.get('colsub', {}).get('agentes_lanzados')}",
        )
    except Exception as exc:
        _ok("enjambre_minimo", False, type(exc).__name__)

    # 6) Grafo orquestador
    try:
        from cognicion.grafo.grafo import obtener_grafo

        obtener_grafo(forzar_recrear=True)
        _ok("grafo_orquestador", True, "compilado")
    except Exception as exc:
        _ok("grafo_orquestador", False, type(exc).__name__)

    # 7) Prompt de estabilidad presente
    try:
        from cerebro import SalomonAI

        _ok(
            "prompt_estabilidad",
            "Prompt de Estabilidad" in SalomonAI.INSTRUCCION_SISTEMA,
            "inyectado",
        )
    except Exception as exc:
        _ok("prompt_estabilidad", False, type(exc).__name__)

    exito = all(c["ok"] for c in checks)
    return {
        "exito": exito,
        "protocolo": "autodiagnostico_enjambres",
        "orquestador": snap,
        "escalado": {"simple": simple, "compleja": compleja},
        "checks": checks,
        "mensaje": (
            "Enjambres operativos. Orquestador de Carga activo. "
            "Arquitectura de colas lista para consultas de alto rendimiento."
            if exito
            else "Diagnóstico con fallos — revisar checks."
        ),
        "listo_alto_rendimiento": exito,
    }
