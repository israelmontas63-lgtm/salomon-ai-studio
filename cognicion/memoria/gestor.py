"""
Gestor de memoria tipada — unifica SQLite (inmediata, proyecto) y ChromaDB (capas).
"""

from __future__ import annotations

from typing import Any

from cognicion.memoria.tipos import CAPAS_RAG, TipoMemoria
from cognicion.memoria.vectorial import MemoriaVectorial, obtener_memoria
from persistencia.sesiones import cargar_proyecto, guardar_proyecto, ultimos_mensajes


class GestorMemoria:
    """Coordina las capas de memoria sin duplicar almacenes."""

    def __init__(
        self,
        session_id: str,
        vectorial: MemoriaVectorial | None = None,
    ) -> None:
        self.session_id = session_id
        self._vectorial = vectorial or obtener_memoria()

    @property
    def vectorial(self) -> MemoriaVectorial:
        return self._vectorial

    @property
    def activa(self) -> bool:
        return self._vectorial.activa

    def memoria_inmediata(self, limite: int = 6) -> str:
        """Últimos turnos desde SQLite."""
        mensajes = ultimos_mensajes(self.session_id, limite=limite)
        if not mensajes:
            return ""

        lineas = ["[Memoria inmediata — turnos recientes de esta sesión]"]
        for item in mensajes:
            rol = "Usuario" if item["rol"] == "usuario" else "Salomón"
            lineas.append(f"- {rol}: {item['contenido'][:300]}")
        lineas.append(
            "Instrucción: Mantén coherencia con este hilo reciente."
        )
        return "\n".join(lineas)

    def memoria_proyecto(self) -> tuple[str, dict[str, Any]]:
        """Contexto explícito del proyecto para esta sesión."""
        meta: dict[str, Any] = {"proyecto_activo": False}
        proyecto = cargar_proyecto(self.session_id)
        if not proyecto or (not proyecto.get("nombre") and not proyecto.get("contexto")):
            return "", meta

        meta["proyecto_activo"] = True
        meta["proyecto_nombre"] = proyecto.get("nombre") or ""

        lineas = ["[Memoria de proyecto — esta sesión]"]
        if proyecto.get("nombre"):
            lineas.append(f"Nombre: {proyecto['nombre']}")
        if proyecto.get("contexto"):
            lineas.append("Notas de contexto:")
            lineas.append(proyecto["contexto"][:1200])
        lineas.append(
            "Instrucción: Adapta respuestas técnicas a este proyecto cuando sea relevante."
        )
        return "\n".join(lineas), meta

    def registrar_nota_proyecto(
        self,
        nota: str,
        nombre: str | None = None,
    ) -> dict[str, str] | None:
        """Persiste nota de proyecto en SQLite y capa vectorial."""
        if not nota.strip() and not (nombre or "").strip():
            return None

        registro = guardar_proyecto(
            self.session_id,
            nombre=nombre,
            nota=nota.strip() if nota else None,
        )

        if self._vectorial.activa and nota.strip():
            self._vectorial.guardar_en_capa(
                nota.strip(),
                TipoMemoria.PROYECTO.value,
                session_id=self.session_id,
                categoria="proyecto",
                origen="explicito",
            )

        return registro

    def contexto_rag(self, consulta: str) -> tuple[str, dict[str, Any]]:
        """Recupera contexto priorizando capas de memoria."""
        meta: dict[str, Any] = {"capas_consultadas": []}
        bloques: list[str] = []

        proyecto, meta_proj = self.memoria_proyecto()
        if proyecto:
            bloques.append(proyecto)
            meta["capas_consultadas"].append(TipoMemoria.PROYECTO.value)
            meta.update(meta_proj)

        # Historial de turnos NO va en el bloque RAG: Gemini ya recibe
        # el historial por chat_con_historial (evita reinjectar el hilo).

        if self._vectorial.activa:
            capas = [c.value for c in CAPAS_RAG]
            rag = self._vectorial.contexto_rag(
                consulta,
                session_id=self.session_id,
                capas=capas,
            )
            if rag:
                bloques.append(rag)
                meta["capas_consultadas"].extend(capas)
                meta["rag_usado"] = True

        if not bloques:
            return "", meta

        return "\n\n".join(bloques), meta

    def guardar_turno(self, usuario: str, asistente: str) -> None:
        if self._vectorial.activa:
            self._vectorial.guardar_turno(self.session_id, usuario, asistente)

    def guardar_preferencia(self, texto: str) -> str | None:
        return self._vectorial.guardar_en_capa(
            texto,
            TipoMemoria.PREFERENCIAS.value,
            session_id="global",
            categoria="preferencia",
            origen="aprendizaje",
        )

    def guardar_aprendizaje(self, texto: str, categoria: str = "contexto") -> str | None:
        capa = (
            TipoMemoria.PREFERENCIAS.value
            if categoria == "preferencia"
            else TipoMemoria.APRENDIZAJE.value
        )
        return self._vectorial.guardar_en_capa(
            texto,
            capa,
            session_id=self.session_id,
            categoria=categoria,
            origen="post_turno",
        )

    def guardar_proyecto(self, texto: str, nombre: str | None = None) -> str | None:
        registro = self.registrar_nota_proyecto(texto, nombre=nombre)
        return registro["actualizada_en"] if registro else None
