import time
import asyncio
import psutil
from collections import deque
from typing import Dict, Any, List, Optional

from app.config import settings
from app.core.process_manager import process_manager

class MetricsManager:
    """
    Monitorea en tiempo real el consumo de CPU, Memoria RAM (crítica para ARK)
    y almacenamiento en disco del servidor y del contenedor.
    Mantiene un historial de puntos para gráficos dinámicos con Chart.js.
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

        # Medir memoria específica del proceso ShooterGameServer
        ark_ram_bytes = 0
        ark_pid = process_manager.get_server_pid()
        if ark_pid:
            try:
                proc = psutil.Process(ark_pid)
                ark_ram_bytes = proc.memory_info().rss
            except Exception:
                pass

        # Espacio en disco
        disk_total_gb = 0.0
        disk_used_gb = 0.0
        disk_pct = 0.0
        try:
            disk = psutil.disk_usage(str(settings.ark_data_dir))
            disk_total_gb = round(disk.total / (1024**3), 2)
            disk_used_gb = round(disk.used / (1024**3), 2)
            disk_pct = disk.percent
        except Exception:
            pass

        # Uptime
        uptime_seconds = 0
        if process_manager.started_at and process_manager.get_status() == "RUNNING":
            uptime_seconds = int(time.time() - process_manager.started_at)

        return {
            "status": process_manager.get_status(),
            "cpu_percent": round(cpu_pct, 1),
            "ram_total_gb": round(vm.total / (1024**3), 2),
            "ram_used_gb": round(vm.used / (1024**3), 2),
            "ram_percent": round(vm.percent, 1),
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
