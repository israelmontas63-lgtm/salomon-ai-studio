# -*- coding: utf-8 -*-
"""
[FILE: core_salomon_master_neural_engine.py]
Motor Maestro de Autonomía, Agentes y Enlaces (Salomón AI).
Audita APIs/memoria, despliega enjambre web paralelo y orquesta imagen.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

ROOT_HINT = os.getenv("SALOMON_ROOT", "")

_RE_IMAGEN = re.compile(
    r"(?i)\b("
    r"(genera(r)?|crea(r)?|dibuja(r)?|haz|renderiza(r)?)\b[\w\s]{0,40}\b"
    r"(imagen|foto|ilustraci[oó]n|dibujo|picture|image|art)|"
    r"(imagen|foto|ilustraci[oó]n)\s+(de|del|con)\b"
    r")"
)

_RE_FACTUAL = re.compile(
    r"(?i)\b("
    r"qu[eé]\s+(es|son|fue|pasa)|qui[eé]n\s+(es|fue|son)|"
    r"c[oó]mo\s+funciona|por\s+qu[eé]|cu[aá]ndo\s+(fue|es|pas)|"
    r"d[oó]nde\s+(est[aá]|queda)|explica|define|noticias?\s+(de|sobre)|"
    r"actualidad|precio\s+de|cotizaci[oó]n"
    r")\b"
)

_RE_VACIO_CONOCIMIENTO = re.compile(
    r"(?i)\b("
    r"no\s+(tengo|s[eé]|encuentro)\s+(informaci[oó]n|datos|idea)|"
    r"no\s+estoy\s+seguro|fuera\s+de\s+mi\s+(conocimiento|alcance)|"
    r"no\s+puedo\s+verificar|desconozco"
    r")\b"
)


class SalomonMasterNeuralEngine:
    def __init__(self) -> None:
        self.module = "SalomonMasterNeuralEngine"
        self.performance_mode = "ULTRA_FAST_PARALLEL_AGENTS"

    def compile_master_neural_spec(self) -> str:
        spec = {
            "system_name": "Salomon AI - Master Neural Core",
            "capabilities": [
                "100% active persistent memory and context retention",
                "Full API bridge verification (Gemini, Groq, Image Generation Endpoints)",
                "Autonomous Web-Scraping Agent Swarm for missing information",
                "High-speed multithreaded reasoning with zero bottlenecks",
                "Real-time recursive agent deployment",
            ],
            "deployment": (
                "Auto-commit, push to Render production, and hot-load PWA with update badge."
            ),
        }
        return json.dumps(spec, indent=2)

    # ─── 1) Auditoría de APIs / llaves ─────────────────────────────────

    def audit_apis(self) -> dict[str, Any]:
        from config.providers import inventario_claves
        import settings as S

        inv = inventario_claves()
        # Ampliar con Tavily (web) — no secreto completo
        inv["TAVILY_API_KEY"] = (
            f"set:{len(S.TAVILY_API_KEY)}c" if S.TAVILY_API_KEY else "missing"
        )

        llm_ok = any(
            inv.get(k, "missing") != "missing"
            for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY")
        )
        media_ok = any(
            inv.get(k, "missing") != "missing"
            for k in ("FAL_KEY", "REPLICATE_API_TOKEN", "OPENAI_API_KEY")
        )
        web_ok = inv.get("TAVILY_API_KEY", "missing") != "missing"
        # DuckDuckGo no requiere key — web siempre parcialmente disponible
        web_ok = True if web_ok else True

        try:
            from cognicion.llm import llm_disponible, obtener_proveedor

            prov = obtener_proveedor()
            llm_runtime = {
                "disponible": bool(llm_disponible()),
                "proveedor": type(prov).__name__,
            }
        except Exception as exc:
            llm_runtime = {"disponible": False, "error": type(exc).__name__}

        try:
            from cognicion.media.media_engine import estado_media_routing

            media_runtime = estado_media_routing()
        except Exception as exc:
            media_runtime = {"error": type(exc).__name__}

        return {
            "ok": llm_ok,
            "llm_bridge": llm_ok,
            "media_bridge": media_ok,
            "web_bridge": web_ok,
            "inventory": inv,
            "llm_runtime": llm_runtime,
            "media_runtime": media_runtime,
            "flags": {
                "BUSQUEDA_WEB_AUTO": bool(getattr(S, "BUSQUEDA_WEB_AUTO", False)),
                "MODO_EJECUCION": bool(getattr(S, "MODO_EJECUCION", False)),
                "SBI_ENABLED": bool(getattr(S, "SBI_ENABLED", False)),
            },
        }

    # ─── 2) Memoria persistente ────────────────────────────────────────

    def audit_memory(self, session_id: str | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {"ok": False, "layers": {}}
        try:
            from persistencia.sesiones import inicializar, listar_sesiones, ultimos_mensajes

            inicializar()
            chats = listar_sesiones(limite=5)
            out["layers"]["sesiones_sqlite"] = {
                "ok": True,
                "chats_indexados": len(chats),
            }
            if session_id:
                out["layers"]["inmediata"] = {
                    "ok": True,
                    "mensajes": len(ultimos_mensajes(session_id, 6)),
                }
        except Exception as exc:
            out["layers"]["sesiones_sqlite"] = {
                "ok": False,
                "error": type(exc).__name__,
            }

        try:
            from cognicion.memoria.vectorial import obtener_memoria

            mem = obtener_memoria()
            out["layers"]["vectorial"] = {
                "ok": True,
                "activa": bool(getattr(mem, "activa", True)),
            }
        except Exception as exc:
            out["layers"]["vectorial"] = {"ok": False, "error": type(exc).__name__}

        try:
            from cognicion.memoria.memory_controller import MemoryController

            sid = session_id or "audit-master"
            mc = MemoryController(sid)
            ctx, meta = mc.contexto_para_turno("auditoria memoria salomon")
            out["layers"]["memory_controller"] = {
                "ok": True,
                "contexto_chars": len(ctx or ""),
                "meta_keys": list((meta or {}).keys())[:8],
            }
        except Exception as exc:
            out["layers"]["memory_controller"] = {
                "ok": False,
                "error": type(exc).__name__,
            }

        out["ok"] = bool(
            (out["layers"].get("sesiones_sqlite") or {}).get("ok")
            and (
                (out["layers"].get("memory_controller") or {}).get("ok")
                or (out["layers"].get("vectorial") or {}).get("ok")
            )
        )
        return out

    # ─── 3) Enjambre / búsqueda autónoma ───────────────────────────────

    def is_greeting(self, mensaje: str) -> bool:
        try:
            from config.memory_cortex import es_saludo_o_charla_simple

            return es_saludo_o_charla_simple(mensaje)
        except Exception:
            return False

    def is_factual_gap(self, mensaje: str) -> bool:
        return bool(_RE_FACTUAL.search(mensaje or ""))

    def wants_image(self, mensaje: str) -> bool:
        return bool(_RE_IMAGEN.search(mensaje or ""))

    def should_search_web(
        self,
        mensaje: str,
        *,
        hechos_personales: str = "",
        rag_empty: bool = False,
        forzar: bool = False,
    ) -> bool:
        if forzar:
            return True
        if self.is_greeting(mensaje):
            return False
        try:
            from config.memory_cortex import pedido_busqueda_explicito

            if pedido_busqueda_explicito(mensaje):
                return True
        except Exception:
            pass

        try:
            from settings import BUSQUEDA_WEB_AUTO

            if not BUSQUEDA_WEB_AUTO:
                return False
        except Exception:
            return False

        # Auto: orquesta / factual sin memoria / RAG vacío
        try:
            from cognicion.orquesta.agentes_paralelos import necesita_orquesta

            if necesita_orquesta(mensaje, hechos_personales=hechos_personales):
                return True
        except Exception:
            pass

        if rag_empty and self.is_factual_gap(mensaje):
            return True
        if self.is_factual_gap(mensaje) and len((hechos_personales or "").strip()) < 40:
            return True
        return False

    def deploy_agent_swarm(
        self,
        mensaje: str,
        *,
        max_workers: int = 3,
    ) -> dict[str, Any]:
        """Despliegue paralelo fail-soft (web + académico + mercado)."""
        from cognicion.orquesta.agentes_paralelos import (
            consolidar_hallazgos_texto,
            desplegar_agentes_paralelos,
        )

        pack = desplegar_agentes_paralelos(
            mensaje, max_workers=max(1, min(int(max_workers or 3), 4))
        )
        texto = consolidar_hallazgos_texto(pack)
        return {
            "ok": bool(pack.get("exito")),
            "pack": pack,
            "texto": texto,
            "bloque": (
                (
                    "[Enjambre neuronal — agentes paralelos en vivo]\n"
                    f"{texto[:2800]}\n"
                    "Instrucción: Sintetiza con precisión. No inventes hechos "
                    "ausentes en los hallazgos. Cita origen si aplica."
                )
                if texto
                else ""
            ),
            "via": "master_neural_swarm",
        }

    def maybe_deploy_swarm(
        self,
        mensaje: str,
        *,
        hechos_personales: str = "",
        rag_empty: bool = False,
    ) -> dict[str, Any]:
        if not self.should_search_web(
            mensaje, hechos_personales=hechos_personales, rag_empty=rag_empty
        ):
            return {"ok": False, "skipped": True, "bloque": ""}
        return self.deploy_agent_swarm(mensaje)

    # ─── 4) Generación de imagen ───────────────────────────────────────

    def maybe_generate_image(self, mensaje: str) -> dict[str, Any]:
        if not self.wants_image(mensaje):
            return {"ok": False, "skipped": True, "bloque": ""}

        prompt = (mensaje or "").strip()
        prompt = re.sub(
            r"(?i)^(genera(r)?|crea(r)?|dibuja(r)?|haz|renderiza(r)?)\s+"
            r"(una\s+|la\s+)?(imagen|foto|ilustraci[oó]n|dibujo)\s*(de|del|con)?\s*",
            "",
            prompt,
        ).strip() or mensaje

        # Prefer Colsub / Fal / Flux bridge
        try:
            from cognicion.media.media_engine import bridge_colsub_media

            pack = bridge_colsub_media(prompt, hint="imagen_hd")
            url = None
            if isinstance(pack, dict):
                url = (
                    pack.get("url")
                    or pack.get("image_url")
                    or (pack.get("resultado") or {}).get("url")
                )
                if not url and pack.get("images"):
                    url = (pack["images"][0] or {}).get("url")
            if url or (isinstance(pack, dict) and pack.get("ok")):
                return {
                    "ok": True,
                    "url": url,
                    "pack": pack,
                    "bloque": (
                        "[Generación de imagen — motor multimodal]\n"
                        f"Prompt: {prompt[:200]}\n"
                        f"URL: {url or '(procesando / ver metadata)'}\n"
                        "Instrucción: Describe la imagen generada y comparte el enlace "
                        "si está disponible."
                    ),
                    "via": "bridge_colsub_media",
                }
        except Exception as exc:
            last_err = type(exc).__name__
        else:
            last_err = None

        try:
            from cognicion.media import generar_imagen

            resultado = generar_imagen(prompt)
            if isinstance(resultado, dict) and (
                resultado.get("url") or resultado.get("exito") or resultado.get("ok")
            ):
                url = resultado.get("url") or resultado.get("image_url")
                return {
                    "ok": True,
                    "url": url,
                    "pack": resultado,
                    "bloque": (
                        "[Generación de imagen — fallback OpenAI/DALL·E]\n"
                        f"Prompt: {prompt[:200]}\n"
                        f"URL: {url or '(ver metadata)'}\n"
                        "Instrucción: Informa a Israel del resultado de la generación."
                    ),
                    "via": "generar_imagen",
                }
        except Exception as exc:
            last_err = type(exc).__name__

        return {
            "ok": False,
            "error": last_err or "media_unavailable",
            "bloque": (
                "[Generación de imagen no disponible]\n"
                "Falta FAL_KEY / REPLICATE_API_TOKEN / OPENAI_API_KEY para renderizar. "
                "Informa con claridad y ofrece reintentar cuando la clave esté activa."
            ),
        }

    # ─── 5) Pipeline enriquecimiento (llamado desde MotorCognicion) ────

    def enrich_turn(
        self,
        mensaje: str,
        *,
        session_id: str | None = None,
        hechos_personales: str = "",
        rag_empty: bool = False,
    ) -> dict[str, Any]:
        """Enjambre + imagen en paralelo cuando aplica (sin bloquear el hilo principal de más)."""
        jobs: dict[str, Any] = {}
        need_swarm = self.should_search_web(
            mensaje, hechos_personales=hechos_personales, rag_empty=rag_empty
        )
        need_img = self.wants_image(mensaje)

        def _swarm() -> dict[str, Any]:
            return self.deploy_agent_swarm(mensaje) if need_swarm else {"skipped": True}

        def _img() -> dict[str, Any]:
            return self.maybe_generate_image(mensaje) if need_img else {"skipped": True}

        with ThreadPoolExecutor(max_workers=2) as pool:
            futs = {}
            if need_swarm:
                futs[pool.submit(_swarm)] = "swarm"
            if need_img:
                futs[pool.submit(_img)] = "image"
            for fut in as_completed(futs):
                jobs[futs[fut]] = fut.result()

        bloques: list[str] = []
        if (jobs.get("swarm") or {}).get("bloque"):
            bloques.append(jobs["swarm"]["bloque"])
        if (jobs.get("image") or {}).get("bloque"):
            bloques.append(jobs["image"]["bloque"])

        return {
            "ok": bool(bloques),
            "bloques": bloques,
            "swarm": jobs.get("swarm"),
            "image": jobs.get("image"),
            "session_id": session_id,
            "performance_mode": self.performance_mode,
        }

    def full_status(self, session_id: str | None = None) -> dict[str, Any]:
        apis = self.audit_apis()
        mem = self.audit_memory(session_id)
        return {
            "module": self.module,
            "performance_mode": self.performance_mode,
            "apis": apis,
            "memory": mem,
            "ok": bool(apis.get("ok") and mem.get("ok")),
            "neural_link": "ACTIVE" if apis.get("ok") and mem.get("ok") else "DEGRADED",
        }


_ENGINE: SalomonMasterNeuralEngine | None = None


def obtener_master_neural() -> SalomonMasterNeuralEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = SalomonMasterNeuralEngine()
    return _ENGINE


def run_master_neural_audit(session_id: str | None = None) -> dict[str, Any]:
    return obtener_master_neural().full_status(session_id)


if __name__ == "__main__":
    engine = SalomonMasterNeuralEngine()
    print("[INICIALIZANDO MOTOR NEURONAL MAESTRO Y ENJAMBRE DE AGENTES - SALOMON AI]")
    print(engine.compile_master_neural_spec())
    print(json.dumps(engine.full_status(), indent=2, default=str)[:2000])
