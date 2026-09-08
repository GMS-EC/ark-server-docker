import time
from collections import deque
from typing import List, Dict, Any

class ActivityManager:
    """Registra y almacena las actividades recientes realizadas en el panel web."""
    def __init__(self, max_items: int = 100):
        self.logs: deque = deque(maxlen=max_items)

    def log(self, category: str, message: str, user: str = "Sistema"):
        self.logs.appendleft({
            "timestamp": time.strftime("%d/%m %H:%M:%S"),
            "category": category,
            "message": message,
            "user": user
        })

    def get_recent(self) -> List[Dict[str, Any]]:
        return list(self.logs)

activity_manager = ActivityManager()
