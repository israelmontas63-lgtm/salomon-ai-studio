"""
Agente autónomo — planifica correcciones con Gemini y las aplica en disco.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from cognicion.agente.ejecutor import aplicar_reemplazo
from cognicion.agente.planificador import generar_plan
from cognicion.autocorreccion.ciclo import es_mensaje_de_error
from cognicion.config import AGENTE_AUTONOMO_HABILITADO
from cognicion.razonamiento.cadena import requiere_razonamiento

PALABRAS_AUTONOMO = (
    "aplica", "aplicar", "corrige", "corregir", "arregla", "arreglar",
    "automático", "automatico", "autonomo", "autónomo", "ejecuta", "ejecutar",
    "implementa", "implementar", "fix", "patch",
)


@dataclass
class ResultadoAgente:
    ejecutado: bool
    exito: bool
    resumen: str = ""
    cambios: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def contexto_para_chat(self) -> str:
        """Bloque para inyectar en el mensaje a Gemini."""
        if not self.ejecutado:
            return ""

        lineas = ["[Agente autónomo — resultado]"]
        lineas.append(self.resumen or "Sin resumen.")

        if self.cambios:
            lineas.append("Cambios aplicados:")
            for c in self.cambios:
                estado = "OK" if c.get("exito") else "FALLÓ"
                lineas.append(f"- [{estado}] {c.get('archivo')}: {c.get('detalle')}")
        elif self.error:
            lineas.append(f"Error del agente: {self.error}")

        lineas.append(
            "Instrucción: Informa al usuario qué se corrigió (o por qué no se pudo) "
            "en español dominicano, de forma clara y proactiva."
        )
        return "\n".join(lineas)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ejecutado": self.ejecutado,
            "exito": self.exito,
            "resumen": self.resumen,
            "cambios": self.cambios,
            "error": self.error,
        }


def debe_ejecutar_agente(
    tarea: str,
    error: str | None = None,
    autonomo: bool = False,
) -> bool:
    """Determina si el agente debe actuar en este turno."""
    if not AGENTE_AUTONOMO_HABILITADO:
        return False

    if autonomo:
        return True

    if error and es_mensaje_de_error(error):
        return True

    texto = (tarea or "").lower()
    if es_mensaje_de_error(tarea):
        return True

    if requiere_razonamiento(tarea) and any(p in texto for p in PALABRAS_AUTONOMO):
        return True

    return any(p in texto for p in PALABRAS_AUTONOMO)


class AgenteAutonomo:
    """Planifica y aplica correcciones de código de forma segura."""

    def corregir(
        self,
        tarea: str,
        error: str | None = None,
    ) -> ResultadoAgente:
        plan = generar_plan(tarea, error)

        if not plan.exito:
            return ResultadoAgente(
                ejecutado=True,
                exito=False,
                resumen=plan.resumen,
                error=plan.error,
            )

        if not plan.acciones:
            return ResultadoAgente(
                ejecutado=True,
                exito=False,
                resumen=plan.resumen or "No encontré una corrección segura para aplicar.",
            )

        cambios_dict: list[dict[str, Any]] = []
        aplicados = 0

        for accion in plan.acciones:
            resultado = aplicar_reemplazo(
                accion.archivo,
                accion.buscar,
                accion.reemplazar,
            )
            cambios_dict.append({
                "archivo": resultado.archivo,
                "exito": resultado.exito,
                "detalle": resultado.detalle,
            })
            if resultado.exito:
                aplicados += 1

        exito = aplicados > 0
        resumen = plan.resumen
        if aplicados:
            resumen += f" Se aplicaron {aplicados} cambio(s) en el proyecto."

        return ResultadoAgente(
            ejecutado=True,
            exito=exito,
            resumen=resumen,
            cambios=cambios_dict,
        )
