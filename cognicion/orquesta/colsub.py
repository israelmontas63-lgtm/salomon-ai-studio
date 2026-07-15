"""
Colsub — orquestador on-demand de Salomón.

- Escala 1–40 agentes según complejidad (nunca 40 por defecto).
- Limitador CPU/RAM: si hay presión, deja de crear agentes y sintetiza.
- Bus de memoria compartida con deduplicación en tiempo real.
- Economía de procesos: solo lo mínimo necesario.
"""

from __future__ import annotations

import hashlib
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from cognicion.busqueda.agente import buscar_web, extraer_consulta
from cognicion.orquesta.agentes_paralelos import (
    _agente_academico,
    _agente_mercado,
    _agente_web,
    consolidar_hallazgos_texto,
    sintetizar_orquesta,
)

# ── Configuración (sobrescribible por settings) ─────────────────────────────

def _cfg() -> dict[str, Any]:
    try:
        from settings import (
            COLSUB_CPU_CRITICO,
            COLSUB_MAX_AGENTES,
            COLSUB_MAX_WORKERS,
            COLSUB_RAM_CRITICO,
        )

        return {
            "max_agentes": max(1, min(40, int(COLSUB_MAX_AGENTES))),
            "max_workers": max(1, min(16, int(COLSUB_MAX_WORKERS))),
            "cpu_critico": float(COLSUB_CPU_CRITICO),
            "ram_critico": float(COLSUB_RAM_CRITICO),
        }
    except Exception:
        return {
            "max_agentes": 40,
            "max_workers": 8,
            "cpu_critico": 85.0,
            "ram_critico": 88.0,
        }


# Roles base (se expanden hasta N con ángulos distintos)
_ROLES = (
    "web",
    "academico",
    "mercado",
    "noticias",
    "contexto",
    "contraste",
    "datos",
    "aplicacion",
)

_ANGULOS = (
    "definición clara",
    "contexto histórico",
    "impacto práctico",
    "datos recientes",
    "contraste de opiniones",
    "implicaciones económicas",
    "visión científica",
    "ejemplos concretos",
    "riesgos y límites",
    "tendencias actuales",
)


@dataclass
class HallazgoBus:
    agente_id: str
    rol: str
    resumen: str
    fingerprint: str
    exito: bool
    meta: dict[str, Any] = field(default_factory=dict)


class BusMemoriaCompartida:
    """Bus compartido: agentes publican; Colsub deduplica al vuelo."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hallazgos: list[HallazgoBus] = []
        self._fps: set[str] = set()
        self._resumen_vivo: list[str] = []
        self._detenido = False
        self._motivo_parada: str | None = None

    def detener(self, motivo: str) -> None:
        with self._lock:
            self._detenido = True
            self._motivo_parada = motivo

    @property
    def detenido(self) -> bool:
        with self._lock:
            return self._detenido

    @property
    def motivo_parada(self) -> str | None:
        with self._lock:
            return self._motivo_parada

    def publicar(self, h: HallazgoBus) -> bool:
        """True si se aceptó (no redundante)."""
        with self._lock:
            if self._detenido and not h.exito:
                return False
            if h.fingerprint in self._fps:
                return False
            if h.exito and h.resumen:
                # Dedup semántico ligero
                for prev in self._resumen_vivo:
                    if _solapamiento(prev, h.resumen) >= 0.72:
                        return False
                self._fps.add(h.fingerprint)
                self._hallazgos.append(h)
                self._resumen_vivo.append(h.resumen[:400])
                return True
            self._hallazgos.append(h)
            return True

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            ok = [h for h in self._hallazgos if h.exito]
            fail = [h for h in self._hallazgos if not h.exito]
            return {
                "total": len(self._hallazgos),
                "unicos": len(ok),
                "fallidos": len(fail),
                "resumen_incremental": list(self._resumen_vivo)[:24],
                "detenido": self._detenido,
                "motivo_parada": self._motivo_parada,
                "informes": [
                    {
                        "agente": h.agente_id,
                        "rol": h.rol,
                        "exito": h.exito,
                        "resumen": h.resumen[:900],
                        "motor": (h.meta or {}).get("motor"),
                        "hallazgos": (h.meta or {}).get("hallazgos") or [],
                        "error": (h.meta or {}).get("error"),
                    }
                    for h in self._hallazgos
                ],
            }


def _solapamiento(a: str, b: str) -> float:
    ta = set(re.findall(r"\w{4,}", (a or "").lower()))
    tb = set(re.findall(r"\w{4,}", (b or "").lower()))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))


def _fingerprint(texto: str) -> str:
    norm = re.sub(r"\s+", " ", (texto or "").strip().lower())[:240]
    return hashlib.sha1(norm.encode("utf-8", errors="ignore")).hexdigest()[:16]


def recursos_criticos(cfg: dict[str, Any] | None = None) -> tuple[bool, dict[str, Any]]:
    """True si CPU o RAM están en zona crítica."""
    cfg = cfg or _cfg()
    info: dict[str, Any] = {"cpu": None, "ram": None, "disponible": False}
    try:
        import psutil

        cpu = float(psutil.cpu_percent(interval=0.05))
        ram = float(psutil.virtual_memory().percent)
        info = {"cpu": cpu, "ram": ram, "disponible": True}
        critico = cpu >= cfg["cpu_critico"] or ram >= cfg["ram_critico"]
        return critico, info
    except Exception:
        return False, info


def puntuacion_complejidad(mensaje: str) -> dict[str, Any]:
    """
    Score 0–100 → cuántos agentes desplegar (1–40).
    Simple → 1–3; compleja → escala dinámica.
    """
    t = (mensaje or "").strip()
    baja = t.lower()
    score = 0

    # Longitud
    n = len(t)
    if n < 40:
        score += 5
    elif n < 100:
        score += 15
    elif n < 200:
        score += 30
    elif n < 400:
        score += 45
    else:
        score += 55

    score += min(20, t.count("?") * 8)
    score += min(15, t.count(",") * 2)
    score += min(10, t.count(" y ") * 2)

    marcas_complejas = (
        "compara",
        "análisis",
        "analisis",
        "investiga",
        "a fondo",
        "varios",
        "multi",
        "impacto",
        "tendencia",
        "mercado",
        "académico",
        "academico",
        "pros y contras",
        "desde",
        "implicaciones",
        "estratég",
        "estrateg",
    )
    score += sum(6 for m in marcas_complejas if m in baja)
    score = max(0, min(100, score))

    cfg = _cfg()
    techo = cfg["max_agentes"]

    if score < 25:
        n_ag = 1
    elif score < 40:
        n_ag = 2
    elif score < 50:
        n_ag = 3
    elif score < 65:
        n_ag = min(6, techo)
    elif score < 80:
        n_ag = min(12, techo)
    elif score < 92:
        n_ag = min(20, techo)
    else:
        n_ag = min(40, techo)

    # Pregunta trivial: forzar 1
    if n < 28 and "?" in t and score < 30:
        n_ag = 1

    return {
        "score": score,
        "agentes_recomendados": max(1, min(techo, n_ag)),
        "techo": techo,
    }


def _consulta_con_angulo(base: str, angulo: str, idx: int) -> str:
    return f"{base} — enfoque: {angulo} (vista {idx + 1})"


def _ejecutar_rol(rol: str, consulta: str) -> dict[str, Any]:
    if rol == "web":
        return _agente_web(consulta)
    if rol == "academico":
        return _agente_academico(consulta)
    if rol == "mercado":
        return _agente_mercado(consulta)
    if rol == "noticias":
        try:
            from cognicion.conectores import consultar_noticias

            n = consultar_noticias(consulta, max_items=4)
            ctx = (n.contexto if n else "") or ""
            if "Instrucción:" in ctx:
                ctx = ctx.split("Instrucción:")[0]
            ok = bool(ctx.strip()) and "sin titulares" not in ctx.lower()
            return {
                "agente": "noticias",
                "exito": ok,
                "motor": "noticias",
                "resumen": ctx[:900] if ok else "",
                "hallazgos": [],
                "error": None if ok else "sin_noticias",
            }
        except Exception as exc:
            return {
                "agente": "noticias",
                "exito": False,
                "error": type(exc).__name__,
                "hallazgos": [],
            }
    # roles genéricos → búsqueda web acotada (economía: reutiliza conector)
    datos = buscar_web(consulta)
    return {
        "agente": rol,
        "exito": bool(datos.get("exito")),
        "motor": datos.get("motor") or rol,
        "resumen": (datos.get("respuesta_directa") or "")[:900],
        "hallazgos": (datos.get("resultados") or [])[:3],
        "error": datos.get("error"),
    }


def planificar_agentes(consulta: str, n: int) -> list[dict[str, str]]:
    """Plan mínimo: N tareas (rol + ángulo), sin procesos de más."""
    plan: list[dict[str, str]] = []
    for i in range(n):
        rol = _ROLES[i % len(_ROLES)]
        angulo = _ANGULOS[i % len(_ANGULOS)]
        plan.append(
            {
                "id": f"{rol}_{i + 1}",
                "rol": rol,
                "angulo": angulo,
                "consulta": _consulta_con_angulo(consulta, angulo, i)
                if n > 3
                else consulta,
            }
        )
    # Si n<=3, preferir roles distintos clásicos
    if n <= 3:
        preferidos = ["web", "academico", "mercado"][:n]
        for i, rol in enumerate(preferidos):
            plan[i]["rol"] = rol
            plan[i]["id"] = f"{rol}_{i + 1}"
            plan[i]["consulta"] = consulta
    return plan


def colsub_desplegar(
    mensaje: str,
    *,
    forzar_n: int | None = None,
    hechos_personales: str = "",
) -> dict[str, Any]:
    """
    Motor Colsub: analiza → escala on-demand → paraleliza → sintetiza temprano si hay carga.
    """
    cfg = _cfg()
    consulta = extraer_consulta(mensaje)
    comp = puntuacion_complejidad(mensaje)
    n = forzar_n if forzar_n is not None else comp["agentes_recomendados"]
    n = max(1, min(cfg["max_agentes"], int(n)))

    critico, rec = recursos_criticos(cfg)
    if critico:
        n = min(n, 2)  # economía extrema bajo presión

    plan = planificar_agentes(consulta, n)
    bus = BusMemoriaCompartida()
    t0 = time.perf_counter()
    lanzados = 0
    cancelados = 0

    def _worker(tarea: dict[str, str]) -> HallazgoBus:
        if bus.detenido:
            return HallazgoBus(
                agente_id=tarea["id"],
                rol=tarea["rol"],
                resumen="",
                fingerprint=_fingerprint(tarea["id"] + "skip"),
                exito=False,
                meta={"error": "cancelado_por_recursos", "omitido": True},
            )
        bruto = _ejecutar_rol(tarea["rol"], tarea["consulta"])
        resumen = (bruto.get("resumen") or "").strip()
        return HallazgoBus(
            agente_id=tarea["id"],
            rol=tarea["rol"],
            resumen=resumen,
            fingerprint=_fingerprint(resumen or tarea["id"]),
            exito=bool(bruto.get("exito") and resumen),
            meta={
                "motor": bruto.get("motor"),
                "hallazgos": bruto.get("hallazgos") or [],
                "error": bruto.get("error"),
                "angulo": tarea.get("angulo"),
            },
        )

    # Lotes pequeños: revisar recursos entre lotes (economía)
    tam_lote = min(cfg["max_workers"], max(1, n))
    with ThreadPoolExecutor(max_workers=tam_lote) as pool:
        pendientes = list(plan)
        while pendientes:
            critico, rec = recursos_criticos(cfg)
            if critico and bus.snapshot()["unicos"] >= 1:
                bus.detener("recursos_criticos")
                cancelados += len(pendientes)
                break

            lote = pendientes[:tam_lote]
            pendientes = pendientes[tam_lote:]
            futuros = [pool.submit(_worker, t) for t in lote]
            lanzados += len(lote)
            for fut in as_completed(futuros):
                try:
                    h = fut.result()
                    bus.publicar(h)
                except Exception as exc:
                    bus.publicar(
                        HallazgoBus(
                            agente_id="error",
                            rol="sistema",
                            resumen="",
                            fingerprint=_fingerprint(str(exc)),
                            exito=False,
                            meta={"error": type(exc).__name__},
                        )
                    )

            # Suficiencia temprana: si score bajo y ya hay 1–2 únicos, parar
            snap = bus.snapshot()
            if comp["score"] < 40 and snap["unicos"] >= min(2, n):
                if pendientes:
                    cancelados += len(pendientes)
                    bus.detener("suficiencia_temprana")
                    pendientes = []
                    break

    snap = bus.snapshot()
    informes = []
    for inf in snap["informes"]:
        informes.append(
            {
                "agente": inf.get("rol") or inf.get("agente"),
                "exito": inf.get("exito"),
                "motor": inf.get("motor"),
                "resumen": inf.get("resumen") or "",
                "hallazgos": inf.get("hallazgos") or [],
                "error": inf.get("error"),
                "agente_id": inf.get("agente"),
            }
        )

    pack = {
        "exito": snap["unicos"] > 0,
        "consulta": consulta,
        "informes": informes,
        "agentes_ok": [i["agente"] for i in informes if i.get("exito")],
        "agentes_fallidos": [i["agente"] for i in informes if not i.get("exito")],
        "total_hallazgos": sum(len(i.get("hallazgos") or []) for i in informes)
        + snap["unicos"],
        "colsub": {
            "complejidad": comp,
            "agentes_planificados": n,
            "agentes_lanzados": lanzados,
            "agentes_cancelados": cancelados,
            "recursos": rec,
            "parada": snap.get("motivo_parada"),
            "unicos_en_bus": snap["unicos"],
            "ms": round((time.perf_counter() - t0) * 1000, 1),
            "resumen_incremental": snap.get("resumen_incremental") or [],
        },
    }

    texto = sintetizar_orquesta(
        consulta,
        pack,
        hechos_personales=hechos_personales,
        intentar_llm=False,
    )
    # Prefijo Colsub si hubo parada por recursos
    if snap.get("motivo_parada") == "recursos_criticos":
        texto = (
            "Prioricé sintetizar lo ya reunido para cuidar CPU/RAM.\n\n" + texto
        )

    pack["texto_sintesis"] = texto
    pack["texto_consolidado"] = consolidar_hallazgos_texto(pack)
    return pack


def colsub_media_bridge(
    prompt: str,
    *,
    hint: str | None = None,
    imagen_entrada: str | None = None,
    forzar_motor: str | None = None,
) -> dict[str, Any]:
    """
    Puente Colsub → Media Engine (Multi-Model Routing Pro/Ultra).
    El cerebro analiza el prompt y selecciona Flux / MJ / Runway / Kling / Krea.
    """
    from cognicion.media.media_engine import bridge_colsub_media

    return bridge_colsub_media(
        prompt,
        hint=hint,
        imagen_entrada=imagen_entrada,
        forzar_motor=forzar_motor,
    )


def colsub_vdcp_bridge(
    *,
    imagen_base64: str | None = None,
    ruta: str | None = None,
    imagen_bytes: bytes | None = None,
    max_foveas: int | None = None,
) -> dict[str, Any]:
    """
    Puente Colsub → VDCP (Visión Dinámica de Campo Profundo).
    Gran angular → foveación → OCR de alta resolución.
    """
    from cognicion.vision.vdcp import ejecutar_vdcp

    return ejecutar_vdcp(
        imagen_base64=imagen_base64,
        ruta=ruta,
        imagen_bytes=imagen_bytes,
        max_foveas=max_foveas,
    )
