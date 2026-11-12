import os
import json
import time
import tempfile
from pathlib import Path
from typing import Any, Dict, Tuple, Optional


def is_subpath(path: Path, parent: Path) -> bool:
    """Comprueba de forma segura si `path` reside dentro de `parent` tras resolver enlaces."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, AttributeError):
        return False


# Caché TTL en memoria para tamaños de directorios: { str(resolved_path): (size_bytes, timestamp) }
_DIR_SIZE_CACHE: Dict[str, Tuple[int, float]] = {}


def atomic_write_text(file_path: Path, content: str, encoding: str = "utf-8") -> None:
    """Escribe un archivo de texto atómicamente con flush + fsync para prevenir corrupción."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    dir_name = file_path.parent

    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding=encoding) as tf:
        tf.write(content)
        tf.flush()
        try:
            os.fsync(tf.fileno())
        except OSError:
            pass
        temp_name = tf.name

    os.replace(temp_name, file_path)
    invalidate_dir_size_cache(dir_name)


def atomic_write_json(file_path: Path, data: Any, indent: int = 2) -> None:
    """Escribe un archivo JSON atómicamente."""
    content = json.dumps(data, indent=indent, ensure_ascii=False)
    atomic_write_text(file_path, content, encoding="utf-8")


def _compute_dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    try:
        for root, _, files in os.walk(path):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    if not os.path.islink(fpath):
                        total += os.path.getsize(fpath)
                except OSError:
                    pass
    except OSError:
        pass
    return total


def get_dir_size_cached(path: Path, ttl_seconds: float = 30.0) -> int:
    """Calcula el tamaño total en bytes de un directorio usando caché con TTL."""
    key = str(Path(path).resolve())
    now = time.time()
    cached = _DIR_SIZE_CACHE.get(key)
    if cached is not None:
        size_val, ts = cached
        if now - ts < ttl_seconds:
            return size_val
    size_val = _compute_dir_size(Path(path))
    _DIR_SIZE_CACHE[key] = (size_val, now)
    return size_val


def invalidate_dir_size_cache(path: Optional[Path] = None) -> None:
    """Invalida la caché de tamaños de directorio (total o para una ruta y sus ancestros)."""
    if path is None:
        _DIR_SIZE_CACHE.clear()
        return
    try:
        resolved = Path(path).resolve()
        keys_to_drop = [
            k for k in _DIR_SIZE_CACHE
            if k == str(resolved) or str(resolved).startswith(k) or k.startswith(str(resolved))
        ]
        for k in keys_to_drop:
            _DIR_SIZE_CACHE.pop(k, None)
    except Exception:
        _DIR_SIZE_CACHE.clear()
