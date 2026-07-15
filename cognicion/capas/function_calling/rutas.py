"""Rutas HTTP de la capa function-calling — montadas vía plugin loader."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/capas/function-calling", tags=["capas"])


@router.get("/estado")
def estado() -> dict:
    from cognicion.capas.function_calling import estado_capa, listar_para_api

    return {**estado_capa(), "herramientas_llm": listar_para_api()}
