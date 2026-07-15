"""
Memoria vectorial local (RAG) con ChromaDB.
Persiste preferencias, configuraciones y turnos de conversación.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from cognicion.config import CONOCIMIENTO_BASE, MEMORIA_DIR, RAG_TOP_K

_instancia_global: "MemoriaVectorial | None" = None


def obtener_memoria() -> "MemoriaVectorial":
    """Instancia compartida — evita reinicializar ChromaDB en cada sesión."""
    global _instancia_global
    if _instancia_global is None:
        _instancia_global = MemoriaVectorial()
    return _instancia_global


class MemoriaVectorial:
    """Base de conocimiento vectorial persistente."""

    def __init__(self) -> None:
        self._disponible = False
        self._coleccion = None
        self._inicializar()

    def _inicializar(self) -> None:
        try:
            import chromadb

            MEMORIA_DIR.mkdir(parents=True, exist_ok=True)
            cliente = chromadb.PersistentClient(path=str(MEMORIA_DIR))
            self._coleccion = cliente.get_or_create_collection(
                name="salomon_conocimiento",
                metadata={"hnsw:space": "cosine"},
            )
            self._disponible = True
            self._sembrar_conocimiento_base()
        except Exception as exc:
            self._disponible = False
            self._coleccion = None
            try:
                from cognicion.registro import obtener_logger

                obtener_logger("memoria").warning(
                    "memoria_vectorial_fallo_init error=%s",
                    f"{type(exc).__name__}: {exc}",
                )
            except Exception:
                pass

    def _sembrar_conocimiento_base(self) -> None:
        if not self._coleccion:
            return

        try:
            existentes = set(
                self._coleccion.get(ids=[item["id"] for item in CONOCIMIENTO_BASE])["ids"]
            )
        except Exception:
            existentes = set()
        for item in CONOCIMIENTO_BASE:
            if item["id"] in existentes:
                continue
            self._coleccion.add(
                ids=[item["id"]],
                documents=[item["texto"]],
                metadatas=[{
                    "tipo": item["tipo"],
                    "categoria": item["categoria"],
                    "capa": "permanente",
                    "sesion_id": "global",
                }],
            )

    @property
    def activa(self) -> bool:
        return self._disponible and self._coleccion is not None

    def guardar(
        self,
        texto: str,
        metadata: dict[str, Any] | None = None,
        doc_id: str | None = None,
    ) -> str | None:
        if not self.activa or not texto.strip():
            return None

        identificador = doc_id or str(uuid.uuid4())
        meta = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }
        meta_limpio = {
            key: val
            for key, val in meta.items()
            if isinstance(val, (str, int, float, bool))
        }
        try:
            self._coleccion.add(
                ids=[identificador],
                documents=[texto.strip()],
                metadatas=[meta_limpio],
            )
        except Exception as exc:
            try:
                from cognicion.registro import obtener_logger

                obtener_logger("memoria").warning(
                    "memoria_guardar_fallo error=%s",
                    f"{type(exc).__name__}: {exc}",
                )
            except Exception:
                pass
            return None
        return identificador

    def buscar(
        self,
        consulta: str,
        n: int | None = None,
        session_id: str | None = None,
        *,
        k: int | None = None,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        if not self.activa or not consulta.strip():
            return []

        limite = n or k or top_k or RAG_TOP_K
        try:
            total = int(self._coleccion.count())
            if total <= 0:
                return []
            limite = max(1, min(int(limite), total))
        except Exception:
            limite = max(1, int(limite or RAG_TOP_K))

        filtro: dict | None = None
        if session_id:
            filtro = {
                "$or": [
                    {"sesion_id": session_id},
                    {"sesion_id": "global"},
                ]
            }

        try:
            resultado = self._coleccion.query(
                query_texts=[consulta],
                n_results=limite,
                where=filtro,
            )
        except Exception:
            resultado = self._coleccion.query(
                query_texts=[consulta],
                n_results=limite,
            )

        documentos = resultado.get("documents", [[]])[0]
        metadatos = resultado.get("metadatas", [[]])[0]
        distancias = resultado.get("distances", [[]])[0]

        items = []
        for doc, meta, dist in zip(documentos, metadatos, distancias):
            items.append({
                "texto": doc,
                "metadata": meta or {},
                "relevancia": round(1 - dist, 3) if dist is not None else None,
            })
        return items

    def guardar_turno(
        self,
        session_id: str,
        usuario: str,
        asistente: str,
    ) -> None:
        if not self.activa:
            return

        resumen = f"Usuario: {usuario}\nSalomón: {asistente}"
        self.guardar(
            resumen,
            metadata={
                "tipo": "turno",
                "categoria": "conversacion",
                "capa": "temporal",
                "sesion_id": session_id,
            },
        )

    def buscar_por_capa(
        self,
        consulta: str,
        capa: str,
        n: int | None = None,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Busca fragmentos filtrados por capa de memoria."""
        if not self.activa or not consulta.strip():
            return []

        limite = n or max(2, RAG_TOP_K // 2)
        filtro: dict[str, Any] = {"capa": capa}

        if capa in ("temporal", "proyecto", "contexto") and session_id:
            filtro = {
                "$and": [
                    {"capa": capa},
                    {
                        "$or": [
                            {"sesion_id": session_id},
                            {"sesion_id": "global"},
                        ]
                    },
                ]
            }
        elif capa in ("preferencias", "aprendizaje", "permanente"):
            filtro = {"capa": capa}

        try:
            resultado = self._coleccion.query(
                query_texts=[consulta],
                n_results=limite,
                where=filtro,
            )
        except Exception:
            return self.buscar(consulta, n=limite, session_id=session_id)

        documentos = resultado.get("documents", [[]])[0]
        metadatos = resultado.get("metadatas", [[]])[0]
        distancias = resultado.get("distances", [[]])[0]

        items = []
        for doc, meta, dist in zip(documentos, metadatos, distancias):
            items.append({
                "texto": doc,
                "metadata": meta or {},
                "relevancia": round(1 - dist, 3) if dist is not None else None,
            })
        return items

    def guardar_en_capa(
        self,
        texto: str,
        capa: str,
        session_id: str = "global",
        categoria: str = "general",
        origen: str = "sistema",
    ) -> str | None:
        return self.guardar(
            texto,
            metadata={
                "capa": capa,
                "categoria": categoria,
                "sesion_id": session_id,
                "origen": origen,
            },
        )

    def contexto_rag(
        self,
        consulta: str,
        session_id: str | None = None,
        capas: list[str] | None = None,
    ) -> str:
        """Formatea fragmentos recuperados para inyectar en el prompt."""
        if capas:
            fragmentos: list[dict[str, Any]] = []
            vistos: set[str] = set()
            for capa in capas:
                for frag in self.buscar_por_capa(consulta, capa, session_id=session_id):
                    clave = frag["texto"][:80]
                    if clave in vistos:
                        continue
                    vistos.add(clave)
                    frag["metadata"] = {**(frag.get("metadata") or {}), "capa": capa}
                    fragmentos.append(frag)
                    if len(fragmentos) >= RAG_TOP_K:
                        break
                if len(fragmentos) >= RAG_TOP_K:
                    break
        else:
            fragmentos = self.buscar(consulta, session_id=session_id)

        if not fragmentos:
            return ""

        lineas = ["[Memoria vectorial — contexto relevante]"]
        for i, frag in enumerate(fragmentos, 1):
            relevancia = frag.get("relevancia")
            capa = (frag.get("metadata") or {}).get("capa", "")
            extra_capa = f" [{capa}]" if capa else ""
            extra = f" (relevancia: {relevancia})" if relevancia else ""
            lineas.append(f"{i}. {frag['texto']}{extra_capa}{extra}")

        lineas.append(
            "Instrucción: Usa esta memoria si es pertinente. "
            "No menciones que proviene de una base de datos."
        )
        return "\n".join(lineas)
