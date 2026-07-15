"""
Auditoría completa — quién, qué, cuándo, desde dónde.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from settings import DATA_DIR

AUDITORIA_DB = DATA_DIR / "auditoria.db"


def _conexion() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(AUDITORIA_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar() -> None:
    with _conexion() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS auditoria (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                actor_rol TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                ip TEXT,
                user_agent TEXT,
                accion TEXT NOT NULL,
                recurso TEXT NOT NULL,
                metodo TEXT,
                status INTEGER,
                duracion_ms REAL,
                detalle TEXT,
                session_id TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_auditoria_ts ON auditoria(timestamp);
            CREATE INDEX IF NOT EXISTS idx_auditoria_actor ON auditoria(actor_id);
            CREATE INDEX IF NOT EXISTS idx_auditoria_accion ON auditoria(accion);
        """)


def registrar(
    *,
    actor_rol: str,
    actor_id: str,
    accion: str,
    recurso: str,
    ip: str = "",
    user_agent: str = "",
    metodo: str = "",
    status: int | None = None,
    duracion_ms: float | None = None,
    detalle: str = "",
    session_id: str = "",
) -> str:
    registro_id = str(uuid.uuid4())
    ahora = datetime.now(timezone.utc).isoformat()
    with _conexion() as conn:
        conn.execute(
            """
            INSERT INTO auditoria
            (id, timestamp, actor_rol, actor_id, ip, user_agent,
             accion, recurso, metodo, status, duracion_ms, detalle, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                registro_id, ahora, actor_rol, actor_id, ip, user_agent,
                accion, recurso, metodo, status, duracion_ms, detalle, session_id,
            ),
        )
    return registro_id


def listar(
    limite: int = 50,
    actor_id: str | None = None,
    accion: str | None = None,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM auditoria WHERE 1=1"
    params: list[Any] = []
    if actor_id:
        query += " AND actor_id = ?"
        params.append(actor_id)
    if accion:
        query += " AND accion = ?"
        params.append(accion)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limite)

    with _conexion() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def contar_por_accion() -> dict[str, int]:
    with _conexion() as conn:
        rows = conn.execute(
            "SELECT accion, COUNT(*) as total FROM auditoria GROUP BY accion"
        ).fetchall()
    return {r["accion"]: r["total"] for r in rows}
