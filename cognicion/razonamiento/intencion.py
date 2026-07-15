"""
Router de intención — decide qué pilares activar antes de enriquecer el mensaje.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import clima
from cognicion.autocorreccion.ciclo import es_mensaje_de_error
from cognicion.conectores import es_consulta_busqueda, es_consulta_noticias, es_consulta_wikipedia
from cognicion.razonamiento.cadena import requiere_razonamiento


class Intencion(str, Enum):
    CHAT = "chat"
    CLIMA = "clima"
    VISION = "vision"
    ERROR = "error"
    TECNICO = "tecnico"
    AGENTE = "agente"
    INVESTIGACION = "investigacion"


@dataclass(frozen=True)
class PlanEnriquecimiento:
    """Qué módulos ejecutar para esta intención."""

    intencion: Intencion
    usar_rag: bool = True
    usar_clima: bool = False
    usar_vision: bool = False
    usar_autocorreccion: bool = False
    usar_razonamiento: bool = False
    prioridad_modelo: str = "chat"


PALABRAS_AGENTE = (
    "aplica", "aplicar", "corrige", "corregir", "arregla", "arreglar",
    "automático", "automatico", "autonomo", "autónomo", "ejecuta", "ejecutar",
    "implementa", "implementar", "fix", "patch",
)


def clasificar_intencion(
    entrada: str,
    *,
    error_consola: str | None = None,
    imagen_base64: str | None = None,
    autonomo: bool = False,
) -> Intencion:
    """Clasifica la intención del turno sin llamadas externas."""
    texto = (entrada or "").strip()
    texto_lower = texto.lower()

    if imagen_base64:
        return Intencion.VISION

    if error_consola and es_mensaje_de_error(error_consola):
        return Intencion.ERROR

    if es_mensaje_de_error(texto):
        return Intencion.ERROR

    if autonomo or any(p in texto_lower for p in PALABRAS_AGENTE):
        return Intencion.AGENTE

    if clima.es_consulta_clima(texto):
        return Intencion.CLIMA

    if es_consulta_wikipedia(texto) or es_consulta_busqueda(texto) or es_consulta_noticias(texto):
        return Intencion.INVESTIGACION

    if requiere_razonamiento(texto):
        return Intencion.TECNICO

    return Intencion.CHAT


def planificar(intencion: Intencion) -> PlanEnriquecimiento:
    """Traduce intención a plan de enriquecimiento."""
    planes: dict[Intencion, PlanEnriquecimiento] = {
        Intencion.CHAT: PlanEnriquecimiento(intencion=Intencion.CHAT),
        Intencion.CLIMA: PlanEnriquecimiento(
            intencion=Intencion.CLIMA,
            usar_clima=True,
        ),
        Intencion.VISION: PlanEnriquecimiento(
            intencion=Intencion.VISION,
            usar_vision=True,
            prioridad_modelo="vision",
        ),
        Intencion.ERROR: PlanEnriquecimiento(
            intencion=Intencion.ERROR,
            usar_autocorreccion=True,
            usar_razonamiento=True,
        ),
        Intencion.TECNICO: PlanEnriquecimiento(
            intencion=Intencion.TECNICO,
            usar_razonamiento=True,
        ),
        Intencion.AGENTE: PlanEnriquecimiento(
            intencion=Intencion.AGENTE,
            usar_autocorreccion=True,
            usar_razonamiento=True,
        ),
        Intencion.INVESTIGACION: PlanEnriquecimiento(
            intencion=Intencion.INVESTIGACION,
            usar_rag=True,
        ),
    }
    return planes.get(intencion, PlanEnriquecimiento(intencion=Intencion.CHAT))
