"""
Ejecutor seguro de parches sobre archivos del proyecto.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from cognicion.config import AGENTE_BACKUP_DIR, AGENTE_MAX_BYTES, ROOT_DIR

RUTAS_BLOQUEADAS = (
    ".env",
    ".git",
    "node_modules",
    "__pycache__",
    "memoria_chroma",
    "agente_backups",
    "studio/dist",
    "studio/node_modules",
)

EXTENSIONES_PERMITIDAS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".html", ".json",
    ".txt", ".md", ".env.example",
}


@dataclass
class CambioArchivo:
    archivo: str
    exito: bool
    detalle: str


@dataclass
class ResultadoEjecucion:
    exito: bool
    cambios: list[CambioArchivo] = field(default_factory=list)
    error: str | None = None


def ruta_segura(ruta_relativa: str) -> Path | None:
    """Valida que la ruta quede dentro del proyecto y no esté bloqueada."""
    if not ruta_relativa or not ruta_relativa.strip():
        return None

    limpia = ruta_relativa.strip().replace("\\", "/").lstrip("/")
    if ".." in limpia.split("/"):
        return None

    candidata = (ROOT_DIR / limpia).resolve()
    try:
        candidata.relative_to(ROOT_DIR.resolve())
    except ValueError:
        return None

    partes = candidata.parts
    for bloqueada in RUTAS_BLOQUEADAS:
        if bloqueada in str(candidata).replace("\\", "/"):
            return None

    if candidata.suffix and candidata.suffix.lower() not in EXTENSIONES_PERMITIDAS:
        return None

    if candidata.name == ".env":
        return None

    return candidata


def leer_archivo(ruta_relativa: str) -> str | None:
    """Lee un archivo del proyecto con límite de tamaño."""
    ruta = ruta_segura(ruta_relativa)
    if not ruta or not ruta.is_file():
        return None

    if ruta.stat().st_size > AGENTE_MAX_BYTES:
        return None

    try:
        return ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ruta.read_text(encoding="latin-1", errors="replace")


def _respaldar(ruta: Path) -> None:
    AGENTE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    destino = AGENTE_BACKUP_DIR / f"{marca}_{ruta.name}"
    shutil.copy2(ruta, destino)


def aplicar_reemplazo(
    ruta_relativa: str,
    buscar: str,
    reemplazar: str,
) -> CambioArchivo:
    """Aplica un reemplazo exacto en un archivo (supervisado por Agent_Guard)."""
    try:
        from cognicion.agente.guard import autorizar_escritura

        gate = autorizar_escritura(ruta_relativa, autorizado=False)
        # Core crítico solo con AUTORIZADO; rutas no críticas pasan ruta_segura
        if gate.get("integrity_violation") and any(
            x in ruta_relativa.replace("\\", "/")
            for x in (
                "camera-engine.js",
                "studio/dist/camera",
                "salomon-security-kernel.js",
            )
        ):
            return CambioArchivo(ruta_relativa, False, "Agent_Guard: INTEGRITY_VIOLATION")
    except Exception:
        pass

    ruta = ruta_segura(ruta_relativa)
    if not ruta:
        return CambioArchivo(ruta_relativa, False, "Ruta no permitida")

    if not ruta.is_file():
        return CambioArchivo(ruta_relativa, False, "Archivo no encontrado")

    if not buscar:
        return CambioArchivo(ruta_relativa, False, "Texto a buscar vacío")

    try:
        contenido = ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        contenido = ruta.read_text(encoding="latin-1", errors="replace")

    ocurrencias = contenido.count(buscar)
    if ocurrencias == 0:
        return CambioArchivo(
            ruta_relativa,
            False,
            "No se encontró el fragmento exacto en el archivo",
        )

    if ocurrencias > 1:
        return CambioArchivo(
            ruta_relativa,
            False,
            f"Fragmento ambiguo ({ocurrencias} coincidencias). Sé más específico.",
        )

    _respaldar(ruta)
    nuevo = contenido.replace(buscar, reemplazar, 1)
    ruta.write_text(nuevo, encoding="utf-8")
    return CambioArchivo(ruta_relativa, True, "Parche aplicado correctamente")


def extraer_archivos_de_error(texto: str) -> list[str]:
    """Extrae rutas de archivos mencionadas en tracebacks o errores."""
    if not texto:
        return []

    hallados: list[str] = []
    patrones = (
        r'File "([^"]+)"',
        r"File '([^']+)'",
        r"(?:^|\s)([\w./\\-]+\.(?:py|js|jsx|ts|tsx|css))(?:\s|:|$)",
    )

    base = str(ROOT_DIR).replace("\\", "/").lower()

    for patron in patrones:
        for match in re.finditer(patron, texto, re.MULTILINE):
            candidato = match.group(1).replace("\\", "/")
            if candidato.startswith(base):
                candidato = candidato[len(base):].lstrip("/")
            if candidato and candidato not in hallados:
                hallados.append(candidato)

    return hallados[:6]


def archivos_contexto_default() -> list[str]:
    """Archivos clave del proyecto cuando el error no cita rutas."""
    candidatos = [
        "app.py",
        "cerebro.py",
        "cognicion/orquestador.py",
        "studio/src/App.jsx",
        "studio/src/api/salomon.js",
    ]
    return [c for c in candidatos if leer_archivo(c) is not None]
