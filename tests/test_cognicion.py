"""Tests del kernel cognitivo — intención, skills, conectores, aprendizaje."""

from __future__ import annotations

from cognicion.aprendizaje import procesar_turno
from cognicion.conectores import consultar_conectores, listar_conectores
from cognicion.llm import GeminiProvider, listar_proveedores, obtener_proveedor
from cognicion.orquestador import MotorCognicion
from cognicion.razonamiento.intencion import Intencion, clasificar_intencion, planificar
from cognicion.skills import listar_skills, skills_para_intencion


def test_clasificar_intencion_clima():
    assert clasificar_intencion("¿Cómo está el clima hoy?") == Intencion.CLIMA


def test_clasificar_intencion_vision():
    assert clasificar_intencion("mira esto", imagen_base64="abc123") == Intencion.VISION


def test_clasificar_intencion_tecnico():
    assert clasificar_intencion("explica el flujo del backend con python") == Intencion.TECNICO


def test_planificar_clima_activa_conector():
    plan = planificar(Intencion.CLIMA)
    assert plan.usar_clima is True
    assert plan.usar_vision is False


def test_skills_registradas():
    ids = {s.id for s in listar_skills()}
    assert "memoria_rag" in ids
    assert "clima" in ids
    assert "agente" in ids


def test_skills_para_intencion_clima():
    ids = {s.id for s in skills_para_intencion(Intencion.CLIMA)}
    assert "clima" in ids


def test_conectores_incluye_clima():
    nombres = listar_conectores()
    assert "clima" in nombres
    assert "wikipedia" in nombres
    assert "wikidata" in nombres
    assert "busqueda" in nombres
    assert "noticias" in nombres


def test_conector_clima_no_dispara_sin_keyword():
    activos, resultados = consultar_conectores("Hola, ¿qué tal?")
    assert activos == []
    assert resultados == []


def test_proveedor_llm_gemini_default():
    assert "gemini" in listar_proveedores()
    proveedor = obtener_proveedor()
    # Sin GEMINI_API_KEY el núcleo cae a local (Free Tier / entorno de prueba).
    if GeminiProvider().disponible():
        assert proveedor.nombre == "gemini"
        assert isinstance(proveedor, GeminiProvider)
    else:
        assert proveedor.nombre in listar_proveedores()
        assert proveedor.disponible()


def test_motor_cognicion_enriquece_con_intencion():
    motor = MotorCognicion("test-session")
    mensaje, meta = motor.enriquecer_mensaje("¿Qué tiempo hace en Santo Domingo?")
    assert "intencion" in meta["cognicion"]
    assert meta["cognicion"]["intencion"] == Intencion.CLIMA.value


def test_aprendizaje_extrae_preferencia():
    class GestorFake:
        activa = True
        preferencias: list[str] = []
        aprendizajes: list[str] = []

        def guardar_preferencia(self, texto: str) -> str | None:
            self.preferencias.append(texto)
            return "id-1"

        def guardar_aprendizaje(self, texto: str, categoria: str = "contexto") -> str | None:
            self.aprendizajes.append(texto)
            return "id-2"

        def guardar_proyecto(self, texto: str, nombre: str | None = None) -> str | None:
            return None

    gestor = GestorFake()
    resultado = procesar_turno(
        "s1",
        "Recuerda que prefiero respuestas cortas",
        "Entendido, Israel.",
        gestor,  # type: ignore[arg-type]
    )
    assert resultado.procesado is True
    assert len(resultado.recuerdos) >= 1
