from typing import Dict, Any
from fastapi import APIRouter, Depends

from app.config import settings
from app.core.security import require_auth
from app.core.task_scheduler import task_scheduler
from app.core.activity_manager import activity_manager

router = APIRouter(tags=["tasks"], dependencies=[Depends(require_auth)])


@router.get("/api/tasks/config")
async def api_get_tasks_config():
    cfg = settings.runtime_config
    return {
        "schedule_enabled": cfg.get("schedule_enabled", False),
        "schedule_start": cfg.get("schedule_start", "20:00"),
        "schedule_stop": cfg.get("schedule_stop", "00:00"),
        "schedule_warn_mins": int(cfg.get("schedule_warn_mins", 10)),
        "auto_backup_enabled": cfg.get("auto_backup_enabled", True),
        "auto_backup_interval_hours": int(cfg.get("auto_backup_interval_hours", 6)),
        "backup_max_count": int(cfg.get("backup_max_count", 10)),
        "auto_dino_wipe_enabled": cfg.get("auto_dino_wipe_enabled", False),
        "auto_dino_wipe_hours": int(cfg.get("auto_dino_wipe_hours", 24)),
        "auto_restart_hours": int(cfg.get("auto_restart_hours", 0))
    }


@router.post("/api/tasks/config")
async def api_save_tasks_config(payload: Dict[str, Any]):
    settings.save_runtime_config(payload)
    activity_manager.log("Tareas", "Configuración de horarios y tareas automáticas actualizada")
    return {"success": True}


@router.get("/api/tasks/status")
async def api_tasks_status():
    """Estado en tiempo real del planificador: bucle activo, últimas ejecuciones y próximas."""
    return task_scheduler.get_status()
