"""
Planificador — pide a Gemini un plan de corrección estructurado en JSON.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from cognicion.agente.ejecutor import (
    archivos_contexto_default,
    extraer_archivos_de_error,
    leer_archivo,
)
from cognicion.config import AGENTE_MAX_ARCHIVOS
from cognicion.llm import gemini_disponible, generar_texto


@dataclass
class AccionParche:
    archivo: str
    buscar: str
    reemplazar: str


@dataclass
class PlanCorreccion:
    exito: bool
    resumen: str = ""
    acciones: list[AccionParche] = field(default_factory=list)
    error: str | None = None


def _recolectar_contexto(tarea: str, error: str | None) -> tuple[str, list[str]]:
    """Arma el bloque de contexto con archivos relevantes."""
    rutas = extraer_archivos_de_error(error or "")
    if not rutas:
        rutas = archivos_contexto_default()

    tarea_lower = (tarea or "").lower()
    for extra in ("app.py", "cerebro.py", "cognicion/orquestador.py"):
        if extra.replace(".py", "") in tarea_lower or extra in tarea_lower:
            if extra not in rutas:
                rutas.append(extra)

    rutas = rutas[:AGENTE_MAX_ARCHIVOS]
    bloques: list[str] = []
    leidos: list[str] = []

    for ruta in rutas:
        contenido = leer_archivo(ruta)
        if contenido is None:
            continue
        leidos.append(ruta)
        bloques.append(f"--- ARCHIVO: {ruta} ---\n{contenido}")

    contexto = "\n\n".join(bloques) if bloques else "(Sin archivos legibles)"
    return contexto, leidos


def _extraer_json(texto: str) -> dict | None:
    """Extrae el primer objeto JSON de la respuesta de Gemini."""
    texto = (texto or "").strip()
    if not texto:
        return None

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.DOTALL)
    if fence:
        texto = fence.group(1)

    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio == -1 or fin == -1:
        return None

    try:
        return json.loads(texto[inicio: fin + 1])
    except json.JSONDecodeError:
        return None


def generar_plan(tarea: str, error: str | None = None) -> PlanCorreccion:
    """Genera un plan de corrección con parches concretos."""
    if not gemini_disponible():
        return PlanCorreccion(False, error="gemini_no_configurado")

    contexto, archivos = _recolectar_contexto(tarea, error)

    prompt = f"""Eres el agente autónomo de Salomón AI Studio.
Analiza el error o tarea técnica y propón correcciones MÍNIMAS y SEGURAS.

TAREA DEL USUARIO:
{tarea}

ERROR DE CONSOLA (si aplica):
{error or "(ninguno)"}

ARCHIVOS DEL PROYECTO:
{contexto}

ARCHIVOS LEÍDOS: {", ".join(archivos) or "ninguno"}

Responde ÚNICAMENTE con JSON válido (sin markdown extra):
{{
  "resumen": "Breve explicación en español dominicano de qué corregirás",
  "acciones": [
    {{
      "archivo": "ruta/relativa.py",
      "buscar": "texto EXACTO a reemplazar (incluye indentación)",
      "reemplazar": "texto nuevo completo"
    }}
  ]
}}

Reglas estrictas:
- Máximo 3 acciones.
- "buscar" debe existir literalmente una sola vez en el archivo.
- No modifiques .env ni node_modules.
- Si no puedes corregir con certeza, devuelve "acciones": [] y explica en resumen.
- Prioriza correcciones pequeñas y verificables."""

    try:
        respuesta_texto = generar_texto(prompt)
        datos = _extraer_json(respuesta_texto)

        if not datos:
            return PlanCorreccion(
                False,
                error="plan_json_invalido",
                resumen="No pude interpretar el plan de corrección.",
            )

        acciones: list[AccionParche] = []
        for item in datos.get("acciones", [])[:3]:
            if not isinstance(item, dict):
                continue
            archivo = str(item.get("archivo", "")).strip()
            buscar = str(item.get("buscar", ""))
            reemplazar = str(item.get("reemplazar", ""))
            if archivo and buscar:
                acciones.append(AccionParche(archivo, buscar, reemplazar))

        return PlanCorreccion(
            True,
            resumen=str(datos.get("resumen", "Plan generado.")).strip(),
            acciones=acciones,
        )

    except Exception as exc:
        return PlanCorreccion(
            False,
            error=str(type(exc).__name__),
            resumen="Falló la generación del plan de corrección.",
        )
