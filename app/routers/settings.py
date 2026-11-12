from typing import Dict, Any
from fastapi import APIRouter, Depends, Query

from app.core.security import require_auth
from app.core.ark_settings_manager import ark_settings_manager
from app.core.activity_manager import activity_manager

router = APIRouter(tags=["settings"], dependencies=[Depends(require_auth)])


@router.get("/api/settings")
async def api_get_settings(instance: str = Query("main")):
    return ark_settings_manager.get_all_settings(instance_id=instance)


@router.get("/api/server/settings")
async def api_get_server_settings_alias(instance: str = Query("main")):
    return ark_settings_manager.get_all_settings(instance_id=instance)


@router.post("/api/settings")
async def api_save_settings(payload: Dict[str, Any], instance: str = Query("main")):
    target_inst = payload.get("instance_id") or instance or "main"
    ok = ark_settings_manager.save_settings(payload, instance_id=str(target_inst))
    activity_manager.log("Configuración", f"Configuraciones de ARK actualizadas (instancia: {target_inst})")
    return {"success": ok, "instance_id": target_inst}
