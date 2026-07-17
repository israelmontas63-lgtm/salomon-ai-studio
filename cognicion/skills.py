"""
Sistema de habilidades — módulos registrables sin afectar el núcleo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from cognicion.razonamiento.intencion import Intencion


@dataclass
class Skill:
    id: str
    nombre: str
    descripcion: str
    intenciones: frozenset[Intencion] = field(default_factory=frozenset)
    activa: bool = True
    prioridad: int = 50


_SKILLS: dict[str, Skill] = {}
_HOOKS: dict[str, Callable[..., Any]] = {}


def registrar_skill(skill: Skill, hook: Callable[..., Any] | None = None) -> None:
    _SKILLS[skill.id] = skill
    if hook is not None:
        _HOOKS[skill.id] = hook


def obtener_skill(skill_id: str) -> Skill | None:
    return _SKILLS.get(skill_id)


def listar_skills(activas_only: bool = True) -> list[Skill]:
    items = list(_SKILLS.values())
    if activas_only:
        items = [s for s in items if s.activa]
    return sorted(items, key=lambda s: s.prioridad)


def skills_para_intencion(intencion: Intencion) -> list[Skill]:
    return [
        s for s in listar_skills()
        if not s.intenciones or intencion in s.intenciones
    ]


def ejecutar_hook(skill_id: str, **kwargs: Any) -> Any | None:
    hook = _HOOKS.get(skill_id)
    if hook is None:
        return None
    return hook(**kwargs)


def _registrar_skills_internas() -> None:
    """Skills empaquetadas con el sistema (pilares actuales)."""
    if _SKILLS:
        return

    registrar_skill(Skill(
        id="memoria_rag",
        nombre="Memoria RAG",
        descripcion="Recuperación de contexto vectorial",
        intenciones=frozenset(),
        prioridad=10,
    ))
    registrar_skill(Skill(
        id="clima",
        nombre="Clima en vivo",
        descripcion="OpenWeatherMap",
        intenciones=frozenset({Intencion.CLIMA}),
        prioridad=20,
    ))
    registrar_skill(Skill(
        id="wikipedia",
        nombre="Wikipedia",
        descripcion="Consulta enciclopedia en español",
        intenciones=frozenset({Intencion.INVESTIGACION}),
        prioridad=25,
    ))
    registrar_skill(Skill(
        id="wikidata",
        nombre="Wikidata",
        descripcion="Datos estructurados verificables",
        intenciones=frozenset({Intencion.INVESTIGACION}),
        prioridad=26,
    ))
    registrar_skill(Skill(
        id="busqueda",
        nombre="Búsqueda web",
        descripcion="Resumen instantáneo DuckDuckGo",
        intenciones=frozenset({Intencion.INVESTIGACION}),
        prioridad=27,
    ))
    registrar_skill(Skill(
        id="noticias",
        nombre="Noticias",
        descripcion="Titulares recientes vía RSS",
        intenciones=frozenset({Intencion.INVESTIGACION}),
        prioridad=28,
    ))
    registrar_skill(Skill(
        id="vision",
        nombre="Visión",
        descripcion="Análisis multimodal de capturas",
        intenciones=frozenset({Intencion.VISION}),
        prioridad=30,
    ))
    registrar_skill(Skill(
        id="autocorreccion",
        nombre="Auto-corrección",
        descripcion="Análisis de errores de consola",
        intenciones=frozenset({Intencion.ERROR, Intencion.AGENTE}),
        prioridad=40,
    ))
    registrar_skill(Skill(
        id="razonamiento_cot",
        nombre="Razonamiento CoT",
        descripcion="Chain of Thought APVE para tareas técnicas",
        intenciones=frozenset({Intencion.TECNICO, Intencion.ERROR, Intencion.AGENTE}),
        prioridad=50,
    ))
    registrar_skill(Skill(
        id="empatia_cognitiva",
        nombre="Empatía cognitiva",
        descripcion="Ajuste de tono emocional del turno",
        intenciones=frozenset(),
        prioridad=15,
    ))
    registrar_skill(Skill(
        id="universal_code_engine",
        nombre="Universal Code Engine",
        descripcion="Ingeniería de software + matemática sandbox",
        intenciones=frozenset({Intencion.TECNICO, Intencion.AGENTE, Intencion.ERROR}),
        prioridad=45,
    ))
    registrar_skill(Skill(
        id="multimodal_core",
        nombre="Multimodal Core",
        descripcion="HD Generator + Prompt Enhancer + Visual Scrapers",
        intenciones=frozenset({Intencion.VISION, Intencion.CHAT, Intencion.INVESTIGACION}),
        prioridad=35,
    ))
    registrar_skill(Skill(
        id="web_architect",
        nombre="Web Architect Engine",
        descripcion="HTML5/CSS3/JS + Flask/React structure con ownership Israel Monta",
        intenciones=frozenset({Intencion.TECNICO, Intencion.CHAT, Intencion.AGENTE}),
        prioridad=36,
    ))
    registrar_skill(Skill(
        id="sce_evolucion",
        nombre="SCE — Criterio de Evolución",
        descripcion="Filtro de valor: aprueba mejoras útiles y bloquea riesgos al núcleo",
        intenciones=frozenset({Intencion.TECNICO, Intencion.AGENTE, Intencion.CHAT}),
        prioridad=12,
    ))
    registrar_skill(Skill(
        id="evolucion_30x",
        nombre="Evolución 30-X",
        descripcion="30 habilidades de vanguardia (inteligencia, percepción, creatividad)",
        intenciones=frozenset({Intencion.TECNICO, Intencion.CHAT, Intencion.VISION}),
        prioridad=11,
    ))
    registrar_skill(Skill(
        id="comic_engine",
        nombre="Comic Engine",
        descripcion="Narrativa visual: guion → storyboard → ilustración → lettering",
        intenciones=frozenset({Intencion.VISION, Intencion.CHAT, Intencion.TECNICO}),
        prioridad=13,
    ))
    registrar_skill(Skill(
        id="agente",
        nombre="Agente autónomo",
        descripcion="Correcciones en archivos del proyecto",
        intenciones=frozenset({Intencion.AGENTE, Intencion.ERROR}),
        prioridad=60,
    ))


_registrar_skills_internas()
