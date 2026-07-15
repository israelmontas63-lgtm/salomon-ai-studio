"""Tests del kernel OS y gestor de modelos."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_nucleo_singleton_registra_motores():
    from cognicion.nucleo import obtener_nucleo, reiniciar_nucleo

    reiniciar_nucleo()
    nucleo = obtener_nucleo()
    mapa = nucleo.mapa()

    assert mapa["iniciado"] is True
    assert mapa["version"] == "1.0.0"
    ids_motores = set(mapa["motores"].keys())
    assert "motor:memoria" in ids_motores
    assert "motor:modelos" in ids_motores
    assert "orquestador" in {c["id"] for c in mapa["componentes"]}


def test_bus_eventos_emite_y_registra():
    from cognicion.nucleo.eventos import BusEventos

    bus = BusEventos()
    recibidos: list[str] = []
    bus.suscribir("test:evento", lambda nombre, payload: recibidos.append(nombre))
    bus.emitir("test:evento", valor=1)

    assert recibidos == ["test:evento"]
    assert bus.contadores().get("test:evento") == 1


def test_gestor_modelos_resuelve_por_tarea():
    from cognicion.modelos.gestor import normalizar_tarea, resolver_modelo

    assert normalizar_tarea("vision").value == "vision"
    assert normalizar_tarea("tecnico").value == "razonamiento"

    chat = resolver_modelo("chat")
    vision = resolver_modelo("vision")

    assert chat["tarea"] == "chat"
    assert chat["model_name"]
    assert vision["tarea"] == "vision"
    assert vision["model_name"]


def test_registro_multiagente():
    from cognicion.agente.registro import listar_agentes, obtener_agente

    agentes = listar_agentes(activos_only=False)
    ids = {a.id for a in agentes}
    assert "corrector" in ids
    assert "supervisor" in ids

    corrector = obtener_agente("corrector")
    assert corrector is not None
    assert corrector.rol == "codigo"


def test_api_nucleo_estado():
    from app import app

    client = TestClient(app)
    res = client.get("/api/nucleo/estado")
    assert res.status_code == 200
    data = res.json()
    assert data["os"] == "Salomón AI"
    assert "motores" in data
    assert "tareas_modelo" in data
    assert "agentes" in data
    assert any(a["id"] == "corrector" for a in data["agentes"])


def test_mcp_estado_esqueleto():
    from cognicion.mcp.cliente import estado_mcp

    estado = estado_mcp()
    assert estado["modo"] == "cliente"
    assert "servidores_configurados" in estado
