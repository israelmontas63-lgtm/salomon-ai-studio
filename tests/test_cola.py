"""Tests cola de tareas en segundo plano."""

from __future__ import annotations

import time

from cognicion.cola import encolar, esperar_vacio, pendientes


def test_encolar_ejecuta_en_fondo():
    resultado = {"listo": False}

    def tarea():
        resultado["listo"] = True

    encolar(tarea)
    assert esperar_vacio(timeout=3.0)
    assert resultado["listo"] is True
    assert pendientes() == 0


def test_esperar_vacio_con_timeout():
    bloqueo = {"activo": True}

    def tarea_lenta():
        while bloqueo["activo"]:
            time.sleep(0.05)

    encolar(tarea_lenta)
    assert not esperar_vacio(timeout=0.01)
    bloqueo["activo"] = False
    assert esperar_vacio(timeout=3.0)
