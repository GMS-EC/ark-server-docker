import os
import time
import asyncio
import psutil
from pathlib import Path
from collections import deque
from typing import Dict, Any, List, Optional

from app.config import settings
from app.core.process_manager import process_manager

def get_cgroup_memory_limit() -> Optional[int]:
    """Lee el límite de memoria asignado al contenedor en cgroups v2 o v1."""
    # 1. Cgroups v2
    cgroup2_max = Path("/sys/fs/cgroup/memory.max")
    if cgroup2_max.exists():
        try:
            val = cgroup2_max.read_text().strip()
            if val != "max" and val.isdigit():
                return int(val)
        except Exception:
            pass

    # 2. Cgroups v1
    cgroup1_limit = Path("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    if cgroup1_limit.exists():
        try:
            val = int(cgroup1_limit.read_text().strip())
            if val < 10**15:  # Si no hay límite suele ser ~2^63 - 1
                return val
        except Exception:
            pass

    # 3. Fallback variable de entorno MEM_LIMIT (ej: 8192M, 8G)
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
    y almacenamiento en disco del servidor y del contenedor.
    """
    def __init__(self, max_history: int = 60):
        self.max_history = max_history
        self.history: deque = deque(maxlen=max_history)
        self._task: Optional[asyncio.Task] = None
        self._running = False

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
                data = self.get_current_metrics()
                self.history.append({
                    "timestamp": time.strftime("%H:%M:%S"),
                    "cpu_percent": data["cpu_percent"],
                    "ram_used_gb": data["ram_used_gb"],
                    "ram_percent": data["ram_percent"],
                    "ark_ram_gb": data["ark_ram_gb"]
                })
            except Exception:
                pass
            await asyncio.sleep(2)

    def get_current_metrics(self) -> Dict[str, Any]:
        """Calcula el estado actual de recursos."""
        vm = psutil.virtual_memory()
        cpu_pct = psutil.cpu_percent(interval=None)

        # 1. Medir memoria del contenedor respetando cgroups (límites de Docker / CasaOS)
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

        # 2. Medir memoria y CPU del proceso real ShooterGameServer (compatible con comm de 15 caracteres en Linux)
        ark_ram_bytes = 0
        ark_cpu_pct = 0.0

        # Prioridad A: Árbol de procesos del subproceso runner de ARK
        if process_manager.process and process_manager.process.returncode is None:
            try:
                parent = psutil.Process(process_manager.process.pid)
                for child in parent.children(recursive=True):
                    try:
                        c_name = (child.name() or '').lower()
                        c_cmd = (' '.join(child.cmdline() or [])).lower()
                        if 'shootergame' in c_name or 'shootergame' in c_cmd:
                            minfo = child.memory_info()
                            if minfo:
                                ark_ram_bytes += minfo.rss
                            c_cpu = child.cpu_percent(interval=None)
                            if c_cpu:
                                ark_cpu_pct += c_cpu
                    except Exception:
                        pass
            except Exception:
                pass

        # Prioridad B: Búsqueda global en process_iter con coincidencia case-insensitive
        if ark_ram_bytes == 0:
            for p in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']):
                try:
                    pname = (p.info.get('name') or '').lower()
                    pcmd = (' '.join(p.info.get('cmdline') or [])).lower()
                    if 'shootergame' in pname or 'shootergame' in pcmd:
                        minfo = p.info.get('memory_info')
                        if minfo:
                            ark_ram_bytes += minfo.rss
                        try:
                            p_cpu = p.cpu_percent(interval=None)
                            if p_cpu:
                                ark_cpu_pct += p_cpu
                        except Exception:
                            pass
                except Exception:
                    pass

        # 3. Espacio en disco
        disk_total_gb = 0.0
        disk_used_gb = 0.0
        disk_pct = 0.0
        try:
            disk = psutil.disk_usage(str(settings.ark_data_dir))
            disk_total_gb = round(disk.total / (1024**3), 1)
            disk_used_gb = round(disk.used / (1024**3), 1)
            disk_pct = disk.percent
        except Exception:
            pass

        # 4. Uptime y cálculo exclusivo de CPU de ARK
        uptime_seconds = 0
        status = process_manager.get_status()
        if process_manager.started_at and status == "RUNNING":
            uptime_seconds = int(time.time() - process_manager.started_at)

        # Si el servidor de ARK está apagado, su consumo es estrictamente 0.0%
        # No caer al host_cpu_percent para evitar brincos del VPS en la interfaz
        if status in ("OFFLINE", "INSTALLING"):
            cpu_display = 0.0
            ark_ram_bytes = 0
        else:
            cpu_display = round(ark_cpu_pct, 1)

        return {
            "status": status,
            "cpu_percent": cpu_display,
            "ark_cpu_percent": round(ark_cpu_pct, 1),
            "host_cpu_percent": round(cpu_pct, 1),
            "ram_total_gb": ram_total_gb,
            "ram_used_gb": ram_used_gb,
            "ram_percent": ram_pct,
            "ark_ram_gb": round(ark_ram_bytes / (1024**3), 2),
            "disk_total_gb": disk_total_gb,
            "disk_used_gb": disk_used_gb,
            "disk_percent": disk_pct,
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
        return list(self.history)

metrics_manager = MetricsManager()
