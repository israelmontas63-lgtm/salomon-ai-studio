# -*- coding: utf-8 -*-
"""
Verificación de conexión maestra — Capas 1–5 + SCE + búsqueda.

Usado por /api/version (tuerquita) y arranques de auditoría.
Fail-soft: nunca lanza; reporta ok/detalle por eslabón.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

from typing import Any


def verificar_conexion_maestra() -> dict[str, Any]:
    """Sella el enlace capa-por-capa sin tumbar el proceso."""
    capas: dict[str, Any] = {}
    ok = True

    # Capa 1 — contexto / ContextVar
    try:
        from cognicion.capas.contexto import (
            ContextoPeticion,
            establecer_contexto,
            limpiar_contexto,
            obtener_contexto,
            usar_contexto,
        )

        with usar_contexto(session_id="seal-check", request_id="master"):
            ctx = obtener_contexto()
            assert isinstance(ctx, ContextoPeticion)
            assert ctx.session_id == "seal-check"
        limpiar_contexto()
        capas["1_contexto"] = {"ok": True, "module": "cognicion.capas.contexto"}
    except Exception as exc:
        ok = False
        capas["1_contexto"] = {"ok": False, "error": type(exc).__name__}

    # Capa 2 — loader / hot-plug
    try:
        from cognicion.capas.loader import estado_capas, inicializar_capas

        st = estado_capas()
        capas["2_loader"] = {
            "ok": True,
            "level9": bool(st.get("ok")),
            "activos": st.get("activos"),
            "module": "cognicion.capas.loader",
            "api": "inicializar_capas",
        }
        _ = inicializar_capas  # enlace simbólico verificado
    except Exception as exc:
        ok = False
        capas["2_loader"] = {"ok": False, "error": type(exc).__name__}

    # Capa 3 — pipeline
    try:
        from cognicion.capas.pipeline import (
            ResultadoPipeline,
            generar_respuesta,
            listar_manejadores,
        )

        handlers = listar_manejadores()
        assert callable(generar_respuesta)
        capas["3_pipeline"] = {
            "ok": True,
            "handlers": handlers,
            "resultado_tipo": ResultadoPipeline.__name__,
            "module": "cognicion.capas.pipeline",
        }
    except Exception as exc:
        ok = False
        capas["3_pipeline"] = {"ok": False, "error": type(exc).__name__}

    # Capa 4 — búsqueda
    try:
        from cognicion.busqueda.agente import (
            _buscar_respaldo,
            _buscar_tavily,
            buscar_web,
            respuesta_parece_limite_o_vacia,
            resumir_estilo_salomon,
        )

        assert respuesta_parece_limite_o_vacia("quota exceeded")
        assert not respuesta_parece_limite_o_vacia("Clima estable en Madrid.")
        capas["4_busqueda"] = {
            "ok": True,
            "cascade": ["tavily", "wikipedia", "duckduckgo", "noticias"],
            "module": "cognicion.busqueda.agente",
            "apis": [
                buscar_web.__name__,
                _buscar_tavily.__name__,
                _buscar_respaldo.__name__,
                resumir_estilo_salomon.__name__,
            ],
        }
    except Exception as exc:
        ok = False
        capas["4_busqueda"] = {"ok": False, "error": type(exc).__name__}

    # Capa 5 — SCE / 30-X
    try:
        from cognicion.evolucion.habilidades_30x import (
            HABILIDADES_30X,
            estado_30x,
            integrar_30x_via_sce,
        )
        from cognicion.evolucion.sce import SCE_VERSION, analizar_valor, estado_sce

        bloqueo = analizar_valor(
            "instalar torch cuda local pesos locales",
            registrar_ledger=False,
        )
        sce = estado_sce()
        pack30 = integrar_30x_via_sce(registrar_ledger=False)
        st30 = estado_30x()
        capas["5_sce_30x"] = {
            "ok": True,
            "sce_version": SCE_VERSION,
            "sce_activo": bool(sce.get("active")),
            "bloquea_torch_cuda": bloqueo.get("decision") == "bloquear",
            "habilidades": len(HABILIDADES_30X),
            "aprobadas": pack30.get("aprobadas"),
            "comic_engine": bool(st30.get("comic_engine_activo") or pack30.get("comic_engine")),
            "module": "cognicion.evolucion",
        }
        if bloqueo.get("decision") != "bloquear":
            ok = False
            capas["5_sce_30x"]["ok"] = False
            capas["5_sce_30x"]["error"] = "torch_cuda_no_bloqueado"
    except Exception as exc:
        ok = False
        capas["5_sce_30x"] = {"ok": False, "error": type(exc).__name__}

    return {
        "ok": ok,
        "protocol": "MASTER_LAYER_SYNC_2026",
        "capas": capas,
        "sellado": ok,
    }
