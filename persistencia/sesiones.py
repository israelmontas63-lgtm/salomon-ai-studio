"""
Persistencia de sesiones de chat en SQLite.
Sobrevive reinicios del servidor.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from settings import SESIONES_DB


def _conexion() -> sqlite3.Connection:
    SESIONES_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SESIONES_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar() -> None:
    with _conexion() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sesiones (
                id TEXT PRIMARY KEY,
                creada_en TEXT NOT NULL,
                actualizada_en TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                rol TEXT NOT NULL,
                contenido TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sesiones(id)
            );
            CREATE INDEX IF NOT EXISTS idx_mensajes_session
                ON mensajes(session_id, id);
            CREATE TABLE IF NOT EXISTS proyecto_sesion (
                session_id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL DEFAULT '',
                contexto TEXT NOT NULL DEFAULT '',
                actualizada_en TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sesiones(id)
            );
        """)
        _migrate_sesiones_columns(conn)


def _migrate_sesiones_columns(conn: sqlite3.Connection) -> None:
    """Columnas opcionales: guardada / titulo (carpeta de chats)."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(sesiones)").fetchall()}
    if "guardada" not in cols:
        conn.execute(
            "ALTER TABLE sesiones ADD COLUMN guardada INTEGER NOT NULL DEFAULT 0"
        )
    if "titulo" not in cols:
        conn.execute(
            "ALTER TABLE sesiones ADD COLUMN titulo TEXT NOT NULL DEFAULT ''"
        )

def sesion_existe(session_id: str) -> bool:
    with _conexion() as conn:
        row = conn.execute(
            "SELECT 1 FROM sesiones WHERE id = ?",
            (session_id,),
        ).fetchone()
    return row is not None


def asegurar_sesion(session_id: str) -> None:
    ahora = datetime.now(timezone.utc).isoformat()
    with _conexion() as conn:
        conn.execute(
            """
            INSERT INTO sesiones (id, creada_en, actualizada_en)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET actualizada_en = excluded.actualizada_en
            """,
            (session_id, ahora, ahora),
        )


def guardar_mensaje(session_id: str, rol: str, contenido: str) -> None:
    if rol not in ("usuario", "asistente"):
        return

    ahora = datetime.now(timezone.utc).isoformat()
    asegurar_sesion(session_id)
    with _conexion() as conn:
        conn.execute(
            """
            INSERT INTO mensajes (session_id, rol, contenido, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, rol, contenido, ahora),
        )
        conn.execute(
            "UPDATE sesiones SET actualizada_en = ? WHERE id = ?",
            (ahora, session_id),
        )


def cargar_mensajes(session_id: str) -> list[dict[str, str]]:
    with _conexion() as conn:
        rows = conn.execute(
            """
            SELECT rol, contenido FROM mensajes
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()
    return [{"rol": row["rol"], "contenido": row["contenido"]} for row in rows]


def ultimos_mensajes(session_id: str, limite: int = 6) -> list[dict[str, str]]:
    """Devuelve los últimos N mensajes de una sesión (memoria inmediata)."""
    if limite <= 0:
        return []

    with _conexion() as conn:
        rows = conn.execute(
            """
            SELECT rol, contenido FROM mensajes
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limite),
        ).fetchall()

    mensajes = [{"rol": row["rol"], "contenido": row["contenido"]} for row in rows]
    mensajes.reverse()
    return mensajes


def cargar_proyecto(session_id: str) -> dict[str, str] | None:
    """Memoria de proyecto explícita por sesión."""
    with _conexion() as conn:
        row = conn.execute(
            """
            SELECT nombre, contexto, actualizada_en
            FROM proyecto_sesion WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()

    if not row:
        return None

    return {
        "nombre": row["nombre"] or "",
        "contexto": row["contexto"] or "",
        "actualizada_en": row["actualizada_en"],
    }


def guardar_proyecto(
    session_id: str,
    *,
    nombre: str | None = None,
    nota: str | None = None,
) -> dict[str, str]:
    """Actualiza nombre y/o acumula notas de contexto del proyecto."""
    ahora = datetime.now(timezone.utc).isoformat()
    asegurar_sesion(session_id)

    actual = cargar_proyecto(session_id)
    nombre_final = (nombre or (actual or {}).get("nombre") or "").strip()
    contexto_prev = (actual or {}).get("contexto") or ""

    if nota and nota.strip():
        linea = nota.strip()
        if linea not in contexto_prev:
            contexto_prev = f"{contexto_prev}\n- {linea}".strip()

    with _conexion() as conn:
        conn.execute(
            """
            INSERT INTO proyecto_sesion (session_id, nombre, contexto, actualizada_en)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                nombre = excluded.nombre,
                contexto = excluded.contexto,
                actualizada_en = excluded.actualizada_en
            """,
            (session_id, nombre_final, contexto_prev, ahora),
        )

    return {
        "nombre": nombre_final,
        "contexto": contexto_prev,
        "actualizada_en": ahora,
    }


def limpiar_proyecto(session_id: str) -> None:
    with _conexion() as conn:
        conn.execute("DELETE FROM proyecto_sesion WHERE session_id = ?", (session_id,))


def limpiar_sesion(session_id: str) -> None:
    with _conexion() as conn:
        conn.execute("DELETE FROM mensajes WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM proyecto_sesion WHERE session_id = ?", (session_id,))
        conn.execute(
            "UPDATE sesiones SET actualizada_en = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), session_id),
        )


def listar_sesiones(
    *,
    limite: int = 40,
    solo_guardadas: bool | None = None,
) -> list[dict]:
    """Lista chats recientes (más nuevo arriba). solo_guardadas=True → carpeta guardados."""
    inicializar()
    lim = max(1, min(int(limite or 40), 100))
    with _conexion() as conn:
        where = ""
        params: list = []
        if solo_guardadas is True:
            where = "WHERE COALESCE(s.guardada, 0) = 1"
        elif solo_guardadas is False:
            where = "WHERE COALESCE(s.guardada, 0) = 0"
        rows = conn.execute(
            f"""
            SELECT
                s.id AS session_id,
                s.creada_en,
                s.actualizada_en,
                COALESCE(s.guardada, 0) AS guardada,
                COALESCE(s.titulo, '') AS titulo,
                (
                    SELECT contenido FROM mensajes
                    WHERE session_id = s.id AND rol IN ('usuario', 'asistente')
                    ORDER BY id DESC LIMIT 1
                ) AS preview,
                (
                    SELECT COUNT(*) FROM mensajes WHERE session_id = s.id
                ) AS message_count
            FROM sesiones s
            {where}
            ORDER BY s.actualizada_en DESC
            LIMIT ?
            """,
            (*params, lim),
        ).fetchall()

    out: list[dict] = []
    for row in rows:
        preview = (row["preview"] or "").strip()
        titulo = (row["titulo"] or "").strip()
        if not titulo and preview:
            titulo = preview[:48] + ("…" if len(preview) > 48 else "")
        if not titulo:
            titulo = "Chat " + str(row["session_id"])[:8]
        out.append(
            {
                "session_id": row["session_id"],
                "titulo": titulo,
                "preview": preview[:120],
                "actualizada_en": row["actualizada_en"],
                "creada_en": row["creada_en"],
                "guardada": bool(row["guardada"]),
                "message_count": int(row["message_count"] or 0),
            }
        )
    return out


def marcar_sesion_guardada(
    session_id: str,
    *,
    guardada: bool = True,
    titulo: str | None = None,
) -> dict:
    """Marca una sesión como conversación guardada (carpeta persistente)."""
    asegurar_sesion(session_id)
    ahora = datetime.now(timezone.utc).isoformat()
    titulo_clean = (titulo or "").strip()[:120]
    with _conexion() as conn:
        if titulo_clean:
            conn.execute(
                """
                UPDATE sesiones
                SET guardada = ?, titulo = ?, actualizada_en = ?
                WHERE id = ?
                """,
                (1 if guardada else 0, titulo_clean, ahora, session_id),
            )
        else:
            conn.execute(
                """
                UPDATE sesiones
                SET guardada = ?, actualizada_en = ?
                WHERE id = ?
                """,
                (1 if guardada else 0, ahora, session_id),
            )
        # Si no hay título, usar preview del último mensaje
        if not titulo_clean:
            row = conn.execute(
                """
                SELECT contenido FROM mensajes
                WHERE session_id = ? AND rol = 'usuario'
                ORDER BY id DESC LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            if row and row["contenido"]:
                auto = str(row["contenido"]).strip()[:48]
                if auto:
                    conn.execute(
                        "UPDATE sesiones SET titulo = ? WHERE id = ?",
                        (auto, session_id),
                    )
                    titulo_clean = auto
    return {
        "session_id": session_id,
        "guardada": bool(guardada),
        "titulo": titulo_clean,
        "actualizada_en": ahora,
    }
