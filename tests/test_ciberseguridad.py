"""Tests del motor de ciberseguridad."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reiniciar_seguridad():
    from cognicion.seguridad.intrusion import obtener_detector
    from cognicion.seguridad import reiniciar_motor

    reiniciar_motor()
    yield
    reiniciar_motor()


def test_enmascarar_openai():
    from cognicion.seguridad import enmascarar_secreto

    texto = "Error con sk-proj-abc123xyz_secret_key_here extra"
    assert "sk-proj" not in enmascarar_secreto(texto)
    assert "[REDACTED]" in enmascarar_secreto(texto)


def test_ruta_sensible_bloquea_env():
    from cognicion.seguridad import ruta_sensible

    assert ruta_sensible("/.env") is True
    assert ruta_sensible("/api/salud") is False


def test_patron_inyeccion_detectado():
    from cognicion.seguridad import contiene_patron_sospechoso

    assert contiene_patron_sospechoso("SELECT * FROM users; DROP TABLE") is True
    assert contiene_patron_sospechoso("hola mundo") is False


def test_identidad_usuario_sin_clave():
    from cognicion.seguridad.identidad import puede_acceder, resolver_actor
    from cognicion.seguridad.tipos import RolAcceso

    actor = resolver_actor(None)
    assert actor.rol == RolAcceso.USUARIO
    ok, _ = puede_acceder(actor, "/api/chat")
    assert ok is True


def test_detector_intrusion_rate_limit():
    from cognicion.seguridad.intrusion import DetectorIntrusion

    det = DetectorIntrusion()
    tipos: list[str] = []
    for _ in range(125):
        ev = det.evaluar_peticion("/api/chat", "POST", "10.0.0.1")
        if ev:
            tipos.append(ev.tipo.value)
    assert "rate_limit" in tipos


def test_detector_anomalias_linea_base():
    from cognicion.seguridad.anomalias import DetectorAnomalias

    det = DetectorAnomalias()
    for i in range(20):
        det.registrar_observacion("/api/chat", 50.0 + i, 200)
    base = det.linea_base()
    assert "/api/chat" in base


def test_sandbox_timeout():
    from cognicion.seguridad.sandbox import ejecutar_aislado
    import time

    def lento():
        time.sleep(5)
        return "ok"

    res = ejecutar_aislado(lento, timeout_seg=1)
    assert res.timeout is True
    assert res.exito is False


def test_motor_estado():
    from cognicion.seguridad import obtener_motor

    estado = obtener_motor().estado()
    assert estado["motor"] == "ciberseguridad"
    assert estado["ofensivo"] is False
    assert len(estado["capas"]) >= 8


def test_api_bloquea_env():
    from app import app

    client = TestClient(app)
    res = client.get("/.env")
    assert res.status_code == 404


def test_api_seguridad_estado_sin_admin_key():
    from app import app

    client = TestClient(app)
    res = client.get("/api/seguridad/estado")
    assert res.status_code == 200
    data = res.json()
    assert data["ofensivo"] is False


def test_api_bloquea_patron_inyeccion():
    from app import app

    client = TestClient(app)
    res = client.get("/api/salud?q=<script>alert(1)</script>")
    assert res.status_code == 403


def test_inventario_secretos_sin_valores():
    from cognicion.seguridad.secretos import inventario_secretos

    items = inventario_secretos()
    for item in items:
        assert "valor" not in item
        assert "configurado" in item


def test_crear_snapshot():
    from cognicion.seguridad.recuperacion import crear_snapshot, listar_snapshots

    manifest = crear_snapshot(motivo="test")
    assert manifest["motivo"] == "test"
    assert len(listar_snapshots()) >= 1
