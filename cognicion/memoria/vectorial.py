"""
Memoria vectorial local (RAG) con ChromaDB + fallback JSON (v104).
Nunca usa HttpClient / puerto 800 — solo filesystem local estable.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from cognicion.config import CONOCIMIENTO_BASE, MEMORIA_DIR, RAG_TOP_K

_log = logging.getLogger("salomon.memoria.vectorial")

_instancia_global: "MemoriaVectorial | None" = None
_FALLBACK_PATH = MEMORIA_DIR.parent / "memoria_json_fallback.jsonl"

# Chroma solo acepta str | int | float | bool en metadatos planos
_MetaScalar = str | int | float | bool


def sanitize_metadata_value(val: Any, *, bool_as_int: bool = True) -> _MetaScalar | None:
    """
    Normaliza un valor para Chroma / where.
    None → descarta. bool → 1/0 (o "true"/"false"). list/dict → JSON compacto.
    """
    if val is None:
        return None
    if isinstance(val, bool):
        if bool_as_int:
            return 1 if val else 0
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, str):
        s = val.strip()
        return s if s else None
    if isinstance(val, (list, tuple, set)):
        try:
            return json.dumps(list(val), ensure_ascii=False, separators=(",", ":"))[:2000]
        except Exception:
            return str(val)[:500]
    if isinstance(val, dict):
        try:
            return json.dumps(val, ensure_ascii=False, separators=(",", ":"))[:2000]
        except Exception:
            return str(val)[:500]
    return str(val)[:500]


def sanitize_metadata(
    metadata: dict[str, Any] | None,
    *,
    bool_as_int: bool = True,
    prefix: str = "",
    max_keys: int = 64,
) -> dict[str, _MetaScalar]:
    """
    Limpieza recursiva / tipado estricto de metadatos Chroma.
    Aplana dicts anidados con claves `padre.hijo`; omite None.
    """
    out: dict[str, _MetaScalar] = {}
    if not metadata:
        return out

    def _walk(obj: Any, path: str) -> None:
        if len(out) >= max_keys:
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = str(k).strip()
                if not key:
                    continue
                child = f"{path}.{key}" if path else key
                if isinstance(v, dict):
                    _walk(v, child)
                elif isinstance(v, (list, tuple)) and v and isinstance(next(iter(v)), dict):
                    cleaned = sanitize_metadata_value(v, bool_as_int=bool_as_int)
                    if cleaned is not None:
                        out[child[:120]] = cleaned
                else:
                    cleaned = sanitize_metadata_value(v, bool_as_int=bool_as_int)
                    if cleaned is not None:
                        out[child[:120]] = cleaned
            return
        cleaned = sanitize_metadata_value(obj, bool_as_int=bool_as_int)
        if cleaned is not None and path:
            out[path[:120]] = cleaned

    _walk(dict(metadata), prefix.strip("."))
    return out


def normalize_where_filter(filtro: dict[str, Any] | None) -> dict[str, Any] | None:
    """Normaliza booleanos en cláusulas where de Chroma ($and/$or/…)."""
    if not filtro:
        return None

    def _norm(node: Any) -> Any:
        if isinstance(node, dict):
            out: dict[str, Any] = {}
            for k, v in node.items():
                if k in ("$and", "$or"):
                    if isinstance(v, list):
                        out[k] = [_norm(x) for x in v]
                    else:
                        out[k] = _norm(v)
                elif k.startswith("$"):
                    out[k] = _norm(v)
                else:
                    if isinstance(v, dict):
                        out[str(k)] = {op: _norm(val) for op, val in v.items()}
                    else:
                        cleaned = sanitize_metadata_value(v, bool_as_int=True)
                        if cleaned is not None:
                            out[str(k)] = cleaned
            return out
        if isinstance(node, list):
            return [_norm(x) for x in node]
        cleaned = sanitize_metadata_value(node, bool_as_int=True)
        return cleaned if cleaned is not None else node

    normalized = _norm(filtro)
    return normalized if isinstance(normalized, dict) and normalized else None


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
        try:
            import chromadb

            MEMORIA_DIR.mkdir(parents=True, exist_ok=True)
            try:
                from chromadb.config import Settings

                cliente = chromadb.PersistentClient(
                    path=str(MEMORIA_DIR),
                    settings=Settings(anonymized_telemetry=False, allow_reset=True),
                )
            except Exception:
                cliente = chromadb.PersistentClient(path=str(MEMORIA_DIR))

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
            except Exception as exc:
                _log.warning(
                    "memoria_cohere_embed_omitido: %s",
                    type(exc).__name__,
                    exc_info=True,
                )
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
            _log.warning(
                "memoria_chroma_fallo → fallback_json error=%s",
                f"{type(exc).__name__}: {exc}",
                exc_info=True,
            )

        try:
            MEMORIA_DIR.mkdir(parents=True, exist_ok=True)
            self._cargar_fallback()
            self._disponible = True
            self.motor = "json_fallback"
            self._sembrar_fallback_base()
        except Exception as exc:
            self._disponible = False
            self.motor = "offline"
            _log.warning(
                "memoria_fallback_fallo error=%s",
                f"{type(exc).__name__}: {exc}",
                exc_info=True,
            )

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
            except Exception as exc:
                _log.warning(
                    "memoria_fallback_linea_invalida: %s",
                    type(exc).__name__,
                    exc_info=True,
                )

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
                    "metadata": sanitize_metadata(
                        {
                            "tipo": item["tipo"],
                            "categoria": item["categoria"],
                            "capa": "permanente",
                            "sesion_id": "global",
                        }
                    ),
                }
            )

    def _sembrar_conocimiento_base(self) -> None:
        if not self._coleccion:
            return

        try:
            existentes = set(
                self._coleccion.get(ids=[item["id"] for item in CONOCIMIENTO_BASE])["ids"]
            )
        except Exception as exc:
            _log.warning(
                "memoria_sembrar_get_ids: %s", type(exc).__name__, exc_info=True
            )
            existentes = set()
        for item in CONOCIMIENTO_BASE:
            if item["id"] in existentes:
                continue
            meta = sanitize_metadata(
                {
                    "tipo": item["tipo"],
                    "categoria": item["categoria"],
                    "capa": "permanente",
                    "sesion_id": "global",
                }
            )
            try:
                self._coleccion.add(
                    ids=[item["id"]],
                    documents=[item["texto"]],
                    metadatas=[meta],
                )
            except Exception as exc:
                _log.warning(
                    "memoria_sembrar_add id=%s error=%s",
                    item["id"],
                    type(exc).__name__,
                    exc_info=True,
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
        if not self.activa or not (texto or "").strip():
            return None

        identificador = doc_id or str(uuid.uuid4())
        meta_crudo: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }
        meta_limpio = sanitize_metadata(meta_crudo, bool_as_int=True)

        if self.motor == "json_fallback":
            try:
                self._persistir_fallback(
                    {
                        "id": identificador,
                        "texto": texto.strip(),
                        "metadata": meta_limpio,
                    }
                )
                return identificador
            except Exception as exc:
                _log.warning(
                    "memoria_guardar_json_fallback_fallo: %s",
                    type(exc).__name__,
                    exc_info=True,
                )
                return None

        try:
            self._coleccion.add(
                ids=[identificador],
                documents=[texto.strip()],
                metadatas=[meta_limpio],
            )
        except Exception as exc:
            _log.warning(
                "memoria_guardar_chroma_fallo → intentando JSONL error=%s",
                f"{type(exc).__name__}: {exc}",
                exc_info=True,
            )
            try:
                self._persistir_fallback(
                    {
                        "id": identificador,
                        "texto": texto.strip(),
                        "metadata": meta_limpio,
                        "chroma_error": type(exc).__name__,
                    }
                )
                return identificador
            except Exception as exc2:
                _log.warning(
                    "memoria_guardar_doble_fallo: %s",
                    type(exc2).__name__,
                    exc_info=True,
                )
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
        if not self.activa or not (consulta or "").strip():
            return []

        limite = n or k or top_k or RAG_TOP_K

        if self.motor == "json_fallback":
            q = consulta.lower().split()
            scored: list[tuple[float, dict[str, Any]]] = []
            for doc in self._docs_fallback:
                texto_doc = (doc.get("texto") or "").lower()
                score = sum(1.0 for w in q if w and w in texto_doc)
                if session_id:
                    sid = (doc.get("metadata") or {}).get("sesion_id")
                    if sid not in (session_id, "global", None):
                        continue
                if score > 0:
                    scored.append((score, doc))
            scored.sort(key=lambda x: x[0], reverse=True)
            out: list[dict[str, Any]] = []
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
        except Exception as exc:
            _log.warning(
                "memoria_buscar_count: %s", type(exc).__name__, exc_info=True
            )
            limite = max(1, int(limite or RAG_TOP_K))

        filtro: dict[str, Any] | None = None
        if session_id:
            filtro = normalize_where_filter(
                {
                    "$or": [
                        {"sesion_id": session_id},
                        {"sesion_id": "global"},
                    ]
                }
            )

        try:
            resultado = self._coleccion.query(
                query_texts=[consulta],
                n_results=limite,
                where=filtro,
            )
        except Exception as exc:
            _log.warning(
                "memoria_buscar_where_fallo → query sin filtro: %s",
                type(exc).__name__,
                exc_info=True,
            )
            try:
                resultado = self._coleccion.query(
                    query_texts=[consulta],
                    n_results=limite,
                )
            except Exception as exc2:
                _log.warning(
                    "memoria_buscar_chroma_fallo: %s",
                    type(exc2).__name__,
                    exc_info=True,
                )
                return []

        documentos = resultado.get("documents", [[]])[0]
        metadatos = resultado.get("metadatas", [[]])[0]
        distancias = resultado.get("distances", [[]])[0]

        items: list[dict[str, Any]] = []
        for doc, meta, dist in zip(documentos, metadatos, distancias):
            items.append(
                {
                    "texto": doc,
                    "metadata": meta or {},
                    "relevancia": round(1 - dist, 3) if dist is not None else None,
                }
            )
        return items

    def guardar_turno(
        self,
        session_id: str,
        usuario: str,
        asistente: str,
    ) -> None:
        if not self.activa:
            _log.warning("memoria_guardar_turno: motor inactivo session=%s", session_id)
            return

        resumen = f"Usuario: {usuario}\nSalomón: {asistente}"
        mid = self.guardar(
            resumen,
            metadata={
                "tipo": "turno",
                "categoria": "conversacion",
                "capa": "temporal",
                "sesion_id": session_id,
            },
        )
        if not mid:
            _log.warning(
                "memoria_guardar_turno: escritura fallida session=%s", session_id
            )

    def buscar_por_capa(
        self,
        consulta: str,
        capa: str,
        n: int | None = None,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Busca fragmentos filtrados por capa de memoria."""
        if not self.activa or not (consulta or "").strip():
            return []

        limite = n or max(2, RAG_TOP_K // 2)
        if self.motor == "json_fallback" or not self._coleccion:
            base = self.buscar(consulta, n=limite * 2, session_id=session_id)
            return [
                f
                for f in base
                if (f.get("metadata") or {}).get("capa") == capa
            ][:limite] or base[:limite]

        filtro_raw: dict[str, Any] = {"capa": capa}
        if capa in ("temporal", "proyecto", "contexto") and session_id:
            filtro_raw = {
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
        elif capa in ("preferencias", "aprendizaje", "permanente", "episodica"):
            filtro_raw = {"capa": capa}

        filtro = normalize_where_filter(filtro_raw)

        try:
            resultado = self._coleccion.query(
                query_texts=[consulta],
                n_results=limite,
                where=filtro,
            )
        except Exception as exc:
            _log.warning(
                "memoria_buscar_por_capa_fallo capa=%s: %s — degradando a buscar()",
                capa,
                type(exc).__name__,
                exc_info=True,
            )
            return self.buscar(consulta, n=limite, session_id=session_id)

        documentos = resultado.get("documents", [[]])[0]
        metadatos = resultado.get("metadatas", [[]])[0]
        distancias = resultado.get("distances", [[]])[0]

        items: list[dict[str, Any]] = []
        for doc, meta, dist in zip(documentos, metadatos, distancias):
            items.append(
                {
                    "texto": doc,
                    "metadata": meta or {},
                    "relevancia": round(1 - dist, 3) if dist is not None else None,
                }
            )
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
                    clave = (frag.get("texto") or "")[:80]
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
            texto_frag = (frag.get("texto") or "").strip()
            if texto_frag:
                lineas.append(f"{i}. {texto_frag}")

        lineas.append(
            "Instrucción: Usa esta memoria SOLO como referencia interna si es pertinente. "
            "NUNCA la repitas, cites ni muestres al usuario. "
            "No menciones «memoria vectorial», relevancia ni bases de datos. "
            "Responde en prosa natural."
        )
        return "\n".join(lineas)
