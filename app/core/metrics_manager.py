import os
import time
import asyncio
import psutil
from pathlib import Path
from collections import deque
from typing import Dict, Any, List, Optional, Set

from app.config import settings
from app.core.process_manager import process_manager
from app.core.process_utils import find_ark_processes
from app.core.fs_utils import get_dir_size_cached


def get_cgroup_memory_limit() -> Optional[int]:
    """Lee el límite de memoria asignado al contenedor en cgroups v2 o v1."""
    cgroup2_max = Path("/sys/fs/cgroup/memory.max")
    if cgroup2_max.exists():
        try:
            val = cgroup2_max.read_text().strip()
            if val != "max" and val.isdigit():
                return int(val)
        except Exception:
            pass

    cgroup1_limit = Path("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    if cgroup1_limit.exists():
        try:
            val = int(cgroup1_limit.read_text().strip())
            if val < 10**15:
                return val
        except Exception:
            pass

    mem_env = os.getenv("MEM_LIMIT", "").strip().lower()
    if mem_env:
        try:
            if mem_env.endswith("g"):
                return int(float(mem_env[:-1]) * (1024**3))
            elif mem_env.endswith("m"):
                return int(float(mem_env[:-1]) * (1024**2))
        except Exception:
            pass

    return None


def get_cgroup_memory_usage() -> Optional[int]:
    """Lee el consumo real de memoria del contenedor en cgroups."""
    cgroup2_cur = Path("/sys/fs/cgroup/memory.current")
    if cgroup2_cur.exists():
        try:
            val = cgroup2_cur.read_text().strip()
            if val.isdigit():
                return int(val)
        except Exception:
            pass

    cgroup1_usage = Path("/sys/fs/cgroup/memory/memory.usage_in_bytes")
    if cgroup1_usage.exists():
        try:
            return int(cgroup1_usage.read_text().strip())
        except Exception:
            pass

    return None


class MetricsManager:
    """
    Monitorea en tiempo real el consumo de CPU, Memoria RAM (respetando cgroups de Docker)
    y almacenamiento en disco del servidor y del contenedor, con serie histórica y alertas.
    """
    def __init__(self, max_history: int = 60):
        self.max_history = max_history
        self.history: deque = deque(maxlen=max_history)
        self.disk_history: deque = deque(maxlen=max_history)
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._proc_cache: Dict[int, psutil.Process] = {}
        self._last_metrics: Optional[Dict[str, Any]] = None
        self._last_collected_at: float = 0.0
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._poll_loop())

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _poll_loop(self):
        while self._running:
            try:
                data = await asyncio.to_thread(self._collect_metrics)
                self._last_metrics = data
                self._last_collected_at = time.time()
                ts = time.strftime("%H:%M:%S")
                point = {
                    "timestamp": ts,
                    "cpu_percent": data["cpu_percent"],
                    "ram_used_gb": data["ram_used_gb"],
                    "ram_percent": data["ram_percent"],
                    "ark_ram_gb": data["ark_ram_gb"],
                    "disk_used_gb": data["disk_used_gb"],
                    "disk_total_gb": data["disk_total_gb"],
                    "disk_percent": data["disk_percent"],
                }
                self.history.append(point)
                self.disk_history.append({
                    "timestamp": ts,
                    "disk_used_gb": data["disk_used_gb"],
                    "disk_total_gb": data["disk_total_gb"],
                    "disk_percent": data["disk_percent"],
                })
            except Exception:
                pass
            await asyncio.sleep(2)

    def get_current_metrics(self) -> Dict[str, Any]:
        """Devuelve el estado actual de recursos con caché de intervalo mínimo."""
        now = time.time()
        if self._last_metrics is None or (now - self._last_collected_at >= 1.5):
            self._last_metrics = self._collect_metrics()
            self._last_collected_at = now
        return self._last_metrics

    async def get_current_metrics_async(self) -> Dict[str, Any]:
        """Versión asíncrona no bloqueante de get_current_metrics."""
        now = time.time()
        if self._last_metrics is None or (now - self._last_collected_at >= 1.5):
            self._last_metrics = await asyncio.to_thread(self._collect_metrics)
            self._last_collected_at = now
        return self._last_metrics

    def _collect_metrics(self) -> Dict[str, Any]:
        """Calcula el estado actual de recursos e inspecciona procesos de ARK."""
        vm = psutil.virtual_memory()
        cpu_pct = psutil.cpu_percent(interval=None)

        # 1. Medir memoria del contenedor respetando cgroups
        cgroup_limit = get_cgroup_memory_limit()
        cgroup_usage = get_cgroup_memory_usage()

        if cgroup_limit and cgroup_limit < vm.total:
            total_ram_bytes = cgroup_limit
            used_ram_bytes = cgroup_usage if cgroup_usage else min(vm.used, cgroup_limit)
        else:
            total_ram_bytes = vm.total
            used_ram_bytes = vm.used

        ram_total_gb = round(total_ram_bytes / (1024**3), 2)
        ram_used_gb = round(used_ram_bytes / (1024**3), 2)
        ram_pct = round((used_ram_bytes / total_ram_bytes) * 100, 1) if total_ram_bytes > 0 else 0.0

        # 2. Localizar procesos pertenecientes al servidor de ARK
        target_pids: Set[int] = set()
        status = process_manager.get_status()

        if status not in ("OFFLINE", "INSTALLING"):
            if process_manager.process and process_manager.process.returncode is None:
                runner_pid = process_manager.process.pid
                target_pids.add(runner_pid)
                try:
                    runner_proc = self._proc_cache.get(runner_pid) or psutil.Process(runner_pid)
                    for child in runner_proc.children(recursive=True):
                        target_pids.add(child.pid)
                except Exception:
                    pass

            for proc in find_ark_processes(ttl=1.5):
                target_pids.add(proc.pid)

        ark_ram_bytes = 0
        ark_raw_cpu = 0.0

        for pid in target_pids:
            try:
                if pid not in self._proc_cache:
                    proc = psutil.Process(pid)
                    proc.cpu_percent(interval=None)
                    self._proc_cache[pid] = proc
                else:
                    proc = self._proc_cache[pid]

                minfo = proc.memory_info()
                if minfo:
                    ark_ram_bytes += minfo.rss

                c_cpu = proc.cpu_percent(interval=None)
                if c_cpu is not None and c_cpu > 0:
                    ark_raw_cpu += c_cpu
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                self._proc_cache.pop(pid, None)

        for cached_pid in list(self._proc_cache.keys()):
            if cached_pid not in target_pids:
                self._proc_cache.pop(cached_pid, None)

        # 3. Espacio en disco (con soporte de cuota STORAGE_LIMIT_GB y caché TTL)
        disk_total_gb = 0.0
        disk_used_gb = 0.0
        disk_free_gb = 0.0
        disk_pct = 0.0
        try:
            storage_limit_env = os.getenv("STORAGE_LIMIT_GB", "").strip()
            if storage_limit_env and float(storage_limit_env) > 0:
                limit_bytes = int(float(storage_limit_env) * (1024**3))
                used_bytes = get_dir_size_cached(settings.ark_data_dir, ttl_seconds=30.0)
                disk_total_gb = round(limit_bytes / (1024**3), 1)
                disk_used_gb = round(used_bytes / (1024**3), 2)
                disk_free_gb = round(max(0, limit_bytes - used_bytes) / (1024**3), 1)
                disk_pct = round(min(100.0, (used_bytes / limit_bytes) * 100), 1)
            else:
                disk = psutil.disk_usage(str(settings.ark_data_dir))
                disk_total_gb = round(disk.total / (1024**3), 1)
                disk_used_gb = round(disk.used / (1024**3), 1)
                disk_free_gb = round(disk.free / (1024**3), 1)
                disk_pct = round(disk.percent, 1)
        except Exception:
            pass

        if disk_pct >= 90.0:
            disk_alert_level = "critical"
        elif disk_pct >= 75.0:
            disk_alert_level = "warning"
        else:
            disk_alert_level = "normal"

        # 4. Uptime y cálculo de CPU de ARK
        uptime_seconds = 0
        if process_manager.started_at and status == "RUNNING":
            uptime_seconds = int(time.time() - process_manager.started_at)

        num_cores = psutil.cpu_count() or 1
        ark_cpu_pct = min(100.0, ark_raw_cpu / num_cores)

        if status in ("OFFLINE", "INSTALLING"):
            cpu_display = 0.0
            ark_ram_bytes = 0
            self._proc_cache.clear()
        else:
            cpu_display = round(ark_cpu_pct, 1)

        return {
            "status": status,
            "cpu_percent": cpu_display,
            "ark_cpu_percent": cpu_display,
            "ark_cpu_raw": round(ark_raw_cpu, 1),
            "host_cpu_percent": round(cpu_pct, 1),
            "num_cores": num_cores,
            "ram_total_gb": ram_total_gb,
            "ram_used_gb": ram_used_gb,
            "ram_percent": ram_pct,
            "ark_ram_gb": round(ark_ram_bytes / (1024**3), 2),
            "disk_total_gb": disk_total_gb,
            "disk_used_gb": disk_used_gb,
            "disk_free_gb": disk_free_gb,
            "disk_percent": disk_pct,
            "disk_alert_level": disk_alert_level,
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": self._format_uptime(uptime_seconds)
        }

    def _format_uptime(self, total_seconds: int) -> str:
        if total_seconds <= 0:
            return "Inactivo"
        hours, rem = divmod(total_seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        return f"{minutes}m {seconds}s"

    def get_history(self) -> List[Dict[str, Any]]:
        if not self.history:
            cur = self.get_current_metrics()
            return [{
                "timestamp": time.strftime("%H:%M:%S"),
                "cpu_percent": cur["cpu_percent"],
                "ram_used_gb": cur["ram_used_gb"],
                "ram_percent": cur["ram_percent"],
                "ark_ram_gb": cur["ark_ram_gb"],
                "disk_used_gb": cur["disk_used_gb"],
                "disk_total_gb": cur["disk_total_gb"],
                "disk_percent": cur["disk_percent"],
            }]
        return list(self.history)

    def get_disk_history(self) -> List[Dict[str, Any]]:
        if not self.disk_history:
            cur = self.get_current_metrics()
            return [{
                "timestamp": time.strftime("%H:%M:%S"),
                "disk_used_gb": cur["disk_used_gb"],
                "disk_total_gb": cur["disk_total_gb"],
                "disk_percent": cur["disk_percent"],
            }]
        return list(self.disk_history)


metrics_manager = MetricsManager()
