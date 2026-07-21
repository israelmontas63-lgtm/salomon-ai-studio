"""
Memoria vectorial local (RAG) con ChromaDB + fallback JSON (v104).
Nunca usa HttpClient / puerto 800 — solo filesystem local estable.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cognicion.config import CONOCIMIENTO_BASE, MEMORIA_DIR, RAG_TOP_K

_instancia_global: "MemoriaVectorial | None" = None
_FALLBACK_PATH = MEMORIA_DIR.parent / "memoria_json_fallback.jsonl"


class _CohereChromaEF:
    """EmbeddingFunction Chroma → ServiceManager.embeddings (Cohere)."""

    def __init__(self, manager: Any) -> None:
        self._mgr = manager

    def name(self) -> str:
        return "cohere_salomon"

    def __call__(self, input: list[str]) -> list[list[float]]:
        texts = [str(t) for t in (input or [])]
        if not texts:
            return []
        return self._mgr.embed_texts(texts)

    # Chroma ≥1.0 llama embed_query / embed_documents (no solo __call__)
    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self(input)

    def embed_documents(self, input: list[str]) -> list[list[float]]:
        return self(input)



def reiniciar_instancia() -> "MemoriaVectorial":
    """Fuerza re-init (reconexión de emergencia)."""
    global _instancia_global
    _instancia_global = None
    return obtener_memoria()


def obtener_memoria() -> "MemoriaVectorial":
    """Instancia compartida — evita reinicializar ChromaDB en cada sesión."""
    global _instancia_global
    if _instancia_global is None:
        _instancia_global = MemoriaVectorial()
    return _instancia_global


class MemoriaVectorial:
    """Base de conocimiento vectorial persistente (chroma o JSON)."""

    def __init__(self) -> None:
        self._disponible = False
        self._coleccion = None
        self.motor = "offline"
        self._docs_fallback: list[dict[str, Any]] = []
        self._inicializar()

    def _inicializar(self) -> None:
        # 1) Chroma PersistentClient — SOLO path local (nunca :800 / HttpClient)
        try:
            import chromadb

            MEMORIA_DIR.mkdir(parents=True, exist_ok=True)
            # Evitar telemetría / servidores remotos
            try:
                from chromadb.config import Settings

                cliente = chromadb.PersistentClient(
                    path=str(MEMORIA_DIR),
                    settings=Settings(anonymized_telemetry=False, allow_reset=True),
                )
            except Exception:
                cliente = chromadb.PersistentClient(path=str(MEMORIA_DIR))

            # Cohere embeddings cuando hay COHERE_API_KEY (ruta neuronal)
            self._coleccion = None
            try:
                from cognicion.servicios import obtener_manager

                mgr = obtener_manager()
                if mgr.cohere_disponible():
                    self._coleccion = cliente.get_or_create_collection(
                        name="salomon_conocimiento_cohere",
                        metadata={"hnsw:space": "cosine", "embedder": "cohere"},
                        embedding_function=_CohereChromaEF(mgr),
                    )
                    self.motor = "chroma_cohere"
            except Exception:
                self._coleccion = None

            if self._coleccion is None:
                self._coleccion = cliente.get_or_create_collection(
                    name="salomon_conocimiento",
                    metadata={"hnsw:space": "cosine"},
                )
                self.motor = "chroma_local"
            self._disponible = True
            self._sembrar_conocimiento_base()
            return
        except Exception as exc:
            self._coleccion = None
            try:
                from cognicion.registro import obtener_logger

                obtener_logger("memoria").warning(
                    "memoria_chroma_fallo → fallback_json error=%s",
                    f"{type(exc).__name__}: {exc}",
                )
            except Exception:
                pass

        # 2) Fallback JSONL — siempre R/W en disco local
        try:
            MEMORIA_DIR.mkdir(parents=True, exist_ok=True)
            self._cargar_fallback()
            self._disponible = True
            self.motor = "json_fallback"
            self._sembrar_fallback_base()
        except Exception as exc:
            self._disponible = False
            self.motor = "offline"
            try:
                from cognicion.registro import obtener_logger

                obtener_logger("memoria").warning(
                    "memoria_fallback_fallo error=%s",
                    f"{type(exc).__name__}: {exc}",
                )
            except Exception:
                pass

    def _cargar_fallback(self) -> None:
        self._docs_fallback = []
        if not _FALLBACK_PATH.exists():
            return
        for ln in _FALLBACK_PATH.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                self._docs_fallback.append(json.loads(ln))
            except Exception:
                continue

    def _persistir_fallback(self, entry: dict[str, Any]) -> None:
        _FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _FALLBACK_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._docs_fallback.append(entry)

    def _sembrar_fallback_base(self) -> None:
        ids = {d.get("id") for d in self._docs_fallback}
        for item in CONOCIMIENTO_BASE:
            if item["id"] in ids:
                continue
            self._persistir_fallback(
                {
                    "id": item["id"],
                    "texto": item["texto"],
                    "metadata": {
                        "tipo": item["tipo"],
                        "categoria": item["categoria"],
                        "capa": "permanente",
                        "sesion_id": "global",
                    },
                }
            )

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
        if self.motor == "json_fallback":
            return self._disponible
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

        if self.motor == "json_fallback":
            try:
                self._persistir_fallback(
                    {"id": identificador, "texto": texto.strip(), "metadata": meta_limpio}
                )
                return identificador
            except Exception:
                return None

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

        if self.motor == "json_fallback":
            q = consulta.lower().split()
            scored: list[tuple[float, dict[str, Any]]] = []
            for doc in self._docs_fallback:
                texto = (doc.get("texto") or "").lower()
                score = sum(1.0 for w in q if w and w in texto)
                if session_id:
                    sid = (doc.get("metadata") or {}).get("sesion_id")
                    if sid not in (session_id, "global", None):
                        continue
                if score > 0:
                    scored.append((score, doc))
            scored.sort(key=lambda x: x[0], reverse=True)
            out = []
            for score, doc in scored[: max(1, int(limite))]:
                out.append(
                    {
                        "texto": doc.get("texto"),
                        "metadata": doc.get("metadata") or {},
                        "relevancia": round(min(1.0, score / max(1, len(q))), 3),
                    }
                )
            return out

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
            try:
                resultado = self._coleccion.query(
                    query_texts=[consulta],
                    n_results=limite,
                )
            except Exception:
                # Cero crash del cerebro: RAG degradado → sin fragmentos
                return []

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
        if self.motor == "json_fallback" or not self._coleccion:
            # Fallback: filtrar en memoria tras búsqueda textual
            base = self.buscar(consulta, n=limite * 2, session_id=session_id)
            return [
                f for f in base
                if (f.get("metadata") or {}).get("capa") == capa
            ][:limite] or base[:limite]

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
            # Sin puntuaciones ni etiquetas técnicas en el texto (solo hechos).
            texto = (frag.get("texto") or "").strip()
            if texto:
                lineas.append(f"{i}. {texto}")

        lineas.append(
            "Instrucción: Usa esta memoria SOLO como referencia interna si es pertinente. "
            "NUNCA la repitas, cites ni muestres al usuario. "
            "No menciones «memoria vectorial», relevancia ni bases de datos. "
            "Responde en prosa natural."
        )
        return "\n".join(lineas)
