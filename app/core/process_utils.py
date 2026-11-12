"""Utilidades compartidas y caché TTL para el descubrimiento de procesos ARK."""

from dataclasses import dataclass
import re
import threading
import time
from typing import List, Optional
import psutil

_IGNORED_SHELL_NAMES = frozenset({
    "python",
    "python.exe",
    "python3",
    "bash",
    "sh",
    "powershell.exe",
    "pwsh.exe",
    "cmd.exe",
})

_PORT_PATTERN = re.compile(r"Port=(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class ArkProcessInfo:
    """Instantánea inmutable de un proceso ShooterGameServer detectado."""

    pid: int
    name: str
    cmdline: List[str]
    ports: List[int]


_cache_lock = threading.Lock()
_cached_processes: List[ArkProcessInfo] = []
_cache_timestamp: float = 0.0


def invalidate_ark_process_cache() -> None:
    """Invalida la caché TTL de procesos ShooterGameServer."""
    global _cache_timestamp
    with _cache_lock:
        _cache_timestamp = 0.0


def _scan_ark_processes() -> List[ArkProcessInfo]:
    """Escanea psutil.process_iter una sola vez y extrae procesos ARK."""
    results: List[ArkProcessInfo] = []
    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                info = proc.info
                raw_name = info.get("name") or ""
                pname = raw_name.lower()
                if pname in _IGNORED_SHELL_NAMES:
                    continue

                cmdline_list = list(info.get("cmdline") or [])
                cmdline_str = " ".join(cmdline_list)
                cmdline_lower = cmdline_str.lower()
                is_server = (
                    "shootergameserver" in pname
                    or pname.startswith("shootergameserv")
                    or "shootergameserver" in cmdline_lower
                )
                if not is_server:
                    continue

                ports = [int(m.group(1)) for m in _PORT_PATTERN.finditer(cmdline_str)]
                results.append(
                    ArkProcessInfo(
                        pid=int(info.get("pid") or 0),
                        name=raw_name,
                        cmdline=cmdline_list,
                        ports=ports,
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception:
        pass
    return results


def find_ark_processes(
    port: Optional[int] = None,
    ttl: float = 1.5,
    force_refresh: bool = False,
) -> List[ArkProcessInfo]:
    """Retorna procesos ShooterGameServer en ejecución usando caché TTL thread-safe.

    Si se indica `port`, conserva procesos que listen en ese puerto explícitamente
    o procesos sin parámetro `Port=` (instancia principal por defecto).
    """
    global _cached_processes, _cache_timestamp

    now = time.time()
    with _cache_lock:
        cache_valid = (
            not force_refresh
            and _cache_timestamp > 0.0
            and ttl > 0.0
            and (now - _cache_timestamp) < ttl
        )
        if not cache_valid:
            _cached_processes = _scan_ark_processes()
            _cache_timestamp = now
        snapshot = list(_cached_processes)

    if port is None:
        return snapshot

    return [proc for proc in snapshot if not proc.ports or port in proc.ports]
