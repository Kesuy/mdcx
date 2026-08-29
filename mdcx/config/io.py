from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path

_WRITE_LOCK = threading.RLock()


def atomic_write_text(path: Path, text: str, *, backup: bool = False) -> None:
    """Durably replace *path* without exposing a partially written file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = text.encode("utf-8")
    with _WRITE_LOCK:
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
            if backup:
                atomic_write_text(path.with_suffix(path.suffix + ".bak"), text)
        finally:
            if temp_path.exists():
                temp_path.unlink()
