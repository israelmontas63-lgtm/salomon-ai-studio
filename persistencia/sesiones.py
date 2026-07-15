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
