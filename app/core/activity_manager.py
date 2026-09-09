import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from app.core.fs_utils import atomic_write_json

from app.config import settings

RETENTION_SECONDS = 7 * 24 * 3600  # 7 días de retención máxima

class ActivityManager:
    """Registra, persiste y purga actividades de auditoría con retención automática de 7 días."""
    def __init__(self):
        self._file: Path = settings.base_dir / "data" / "activity_logs.json"
        self._logs: List[Dict[str, Any]] = []
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
            self._purge_old()
            atomic_write_json(self._file, self._logs, indent=2)
        except Exception:
            pass

    def log(self, category: str, message: str, user: str = "Sistema"):
        now = time.time()
        item = {
            "timestamp": datetime.fromtimestamp(now).strftime("%d/%m/%Y %H:%M:%S"),
            "unix_time": now,
            "category": category,
            "message": message,
            "user": user
        }
        self._logs.insert(0, item)
        self._save()

    def get_recent(self) -> List[Dict[str, Any]]:
        self._purge_old()
        return list(self._logs)

activity_manager = ActivityManager()
