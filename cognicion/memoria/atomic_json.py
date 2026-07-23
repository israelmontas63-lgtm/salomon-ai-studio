# -*- coding: utf-8 -*-
"""Escritura JSON atómica con lock de archivo (tmp + os.replace)."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

_log = logging.getLogger("salomon.memoria.atomic_json")

try:
    import msvcrt  # type: ignore

    def _lock_exclusive(fh) -> None:
        fh.seek(0)
        if fh.tell() == 0:
            fh.write("0")
            fh.flush()
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)

    def _unlock(fh) -> None:
        try:
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass

except ImportError:
    import fcntl  # type: ignore

    def _lock_exclusive(fh) -> None:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)

    def _unlock(fh) -> None:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass


def atomic_write_json(path: Path, data: Any, *, indent: int = 2) -> bool:
    """Escribe JSON de forma atómica. True si OK."""
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, ensure_ascii=False, indent=indent)
        if not payload.endswith("\n"):
            payload += "\n"
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, path)
            return True
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
    except Exception:
        _log.warning("atomic_write_json falló path=%s", path, exc_info=True)
        return False


def locked_update_json(
    path: Path,
    mutator,
    *,
    default: dict | None = None,
) -> Any:
    """
    Lee → muta → escribe con lock. `mutator(data) -> data`.
    Retorna el data final o default si falla.
    """
    path = Path(path)
    default = default if default is not None else {}
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    try:
        with open(lock_path, "a+", encoding="utf-8") as lock_fh:
            _lock_exclusive(lock_fh)
            try:
                data: Any = default
                if path.is_file():
                    try:
                        loaded = json.loads(path.read_text(encoding="utf-8"))
                        if isinstance(loaded, dict):
                            data = loaded
                    except Exception:
                        _log.warning(
                            "locked_update_json: JSON corrupto path=%s",
                            path,
                            exc_info=True,
                        )
                        data = dict(default) if isinstance(default, dict) else default
                data = mutator(data)
                atomic_write_json(path, data)
                return data
            finally:
                _unlock(lock_fh)
    except Exception:
        _log.warning("locked_update_json falló path=%s", path, exc_info=True)
        return default
