import atexit
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.fs_utils import atomic_write_json

from app.config import settings

RETENTION_SECONDS = 7 * 24 * 3600  # 7 días de retención máxima


class ActivityManager:
    """Registra, persiste con escritura diferida y purga actividades con retención de 7 días."""
    def __init__(self, debounce_seconds: float = 1.5):
        self._file: Path = settings.ark_data_dir / "activity_logs.json"
        self._logs: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._io_lock = threading.Lock()
        self._dirty: bool = False
        self._flush_timer: Optional[threading.Timer] = None
        self._debounce_seconds: float = debounce_seconds
        self._load()

    def _load(self):
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            if self._file.exists():
                with open(self._file, "r", encoding="utf-8") as f:
                    self._logs = json.load(f)
                self._purge_old()
        except Exception:
            self._logs = []

    def _purge_old(self):
        now = time.time()
        # Conservar solo los últimos 7 días
        self._logs = [
            item for item in self._logs
            if (now - item.get("unix_time", now)) <= RETENTION_SECONDS
        ]

    def _save(self):
        try:
            with self._io_lock:
                with self._lock:
                    self._purge_old()
                    snapshot = list(self._logs)
                    target_file = self._file
                target_file.parent.mkdir(parents=True, exist_ok=True)
                atomic_write_json(target_file, snapshot, indent=2)
        except Exception:
            pass

    def _schedule_save(self):
        if self._debounce_seconds <= 0:
            self.flush()
            return
        with self._lock:
            if self._flush_timer is None:
                timer = threading.Timer(self._debounce_seconds, self.flush)
                timer.daemon = True
                self._flush_timer = timer
                timer.start()

    def flush(self):
        """Vuelca a disco los registros pendientes cancelando el temporizador activo."""
        with self._lock:
            if self._flush_timer is not None:
                self._flush_timer.cancel()
                self._flush_timer = None
            if not self._dirty:
                return
            self._dirty = False
        self._save()

    def log(self, category: str, message: str, user: str = "Sistema"):
        now = time.time()
        item = {
            "timestamp": datetime.fromtimestamp(now).strftime("%d/%m/%Y %H:%M:%S"),
            "unix_time": now,
            "category": category,
            "message": message,
            "user": user
        }
        with self._lock:
            self._logs.insert(0, item)
            self._dirty = True
            self._schedule_save()

    def get_recent(self) -> List[Dict[str, Any]]:
        with self._lock:
            self._purge_old()
            return list(self._logs)


activity_manager = ActivityManager()
atexit.register(activity_manager.flush)
