import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import settings
from app.core.security import require_auth, require_api_rate_limit
from app.core.ark_settings_manager import ark_settings_manager
from app.core.cluster_manager import cluster_manager
from app.core.activity_manager import activity_manager

router = APIRouter(tags=["cluster"], dependencies=[Depends(require_auth)])


class ClusterInstanceCreateRequest(BaseModel):
    name: str
    map: str
    session_name: Optional[str] = None
    server_port: Optional[int] = None
    query_port: Optional[int] = None
    rcon_port: Optional[int] = None
    rcon_password: Optional[str] = None
    server_password: Optional[str] = None
    max_players: Optional[int] = None
    alt_save_dir: Optional[str] = None


class ClusterInstanceUpdateRequest(BaseModel):
    name: Optional[str] = None
    session_name: Optional[str] = None
    server_password: Optional[str] = None
    rcon_password: Optional[str] = None
    max_players: Optional[int] = None
    enabled: Optional[bool] = None
    server_port: Optional[int] = None
    query_port: Optional[int] = None
    rcon_port: Optional[int] = None


class ClusterRatesSyncRequest(BaseModel):
    rates: Dict[str, Any]


@router.get("/api/cluster/status")
async def api_cluster_status():
    instances = await asyncio.to_thread(cluster_manager.list_instances)
    online_nodes = sum(1 for i in instances if i.get("status") == "RUNNING")
    tributes = await asyncio.to_thread(cluster_manager.list_cluster_tributes)
    return {
        "cluster_id": settings.cluster_id,
        "cluster_dir": str(settings.cluster_dir),
        "total_nodes": len(instances),
        "online_nodes": online_nodes,
        "tributes_count": len(tributes),
        "instances": instances
    }


@router.get("/api/cluster/instances")
async def api_cluster_instances():
    instances = await asyncio.to_thread(cluster_manager.list_instances)
    return {
        "instances": instances,
        "maps": cluster_manager.get_official_maps(),
        "suggested_ports": cluster_manager.suggest_next_ports(),
        "cluster_id": settings.cluster_id
    }


@router.post("/api/cluster/instances")
async def api_cluster_instance_create(req: ClusterInstanceCreateRequest):
    res = cluster_manager.create_instance(req.model_dump())
    if res.get("success"):
        activity_manager.log("Clúster", f"Nuevo mapa añadido al clúster: {req.name} ({req.map})")
    return res


@router.put("/api/cluster/instances/{instance_id}")
async def api_cluster_instance_update(instance_id: str, req: ClusterInstanceUpdateRequest):
    res = cluster_manager.update_instance(instance_id, req.model_dump(exclude_unset=True))
    if res.get("success"):
        activity_manager.log("Clúster", f"Instancia {instance_id} actualizada")
    return res


@router.delete("/api/cluster/instances/{instance_id}")
async def api_cluster_instance_delete(instance_id: str):
    res = cluster_manager.delete_instance(instance_id)
    if res.get("success"):
        activity_manager.log("Clúster", f"Instancia {instance_id} eliminada del clúster")
    return res


@router.post("/api/cluster/instances/{instance_id}/start")
async def api_cluster_instance_start(instance_id: str):
    ok = await cluster_manager.start_instance(instance_id)
    activity_manager.log("Clúster", f"Iniciando nodo {instance_id}...")
    status_val = await asyncio.to_thread(cluster_manager.get_instance_status, instance_id)
    return {"success": ok, "status": status_val}


@router.post("/api/cluster/instances/{instance_id}/stop")
async def api_cluster_instance_stop(instance_id: str):
    ok = await cluster_manager.stop_instance(instance_id)
    activity_manager.log("Clúster", f"Deteniendo nodo {instance_id}...")
    status_val = await asyncio.to_thread(cluster_manager.get_instance_status, instance_id)
    return {"success": ok, "status": status_val}


@router.post("/api/cluster/instances/{instance_id}/restart")
async def api_cluster_instance_restart(instance_id: str):
    ok = await cluster_manager.restart_instance(instance_id)
    activity_manager.log("Clúster", f"Reiniciando nodo {instance_id}...")
    status_val = await asyncio.to_thread(cluster_manager.get_instance_status, instance_id)
    return {"success": ok, "status": status_val}


@router.post(
    "/api/cluster/instances/{instance_id}/command",
    dependencies=[Depends(require_api_rate_limit("cluster_command", max_requests=30, window_seconds=60))],
)
async def api_cluster_instance_command(instance_id: str, payload: Dict[str, str]):
    cmd = payload.get("command", "")
    if not cmd:
        return {"success": False, "error": "Comando vacío"}
    status_val = await asyncio.to_thread(cluster_manager.get_instance_status, instance_id)
    if status_val != "RUNNING":
        return {
            "success": False,
            "error": f"El nodo '{instance_id}' no está en ejecución",
            "response": f"[AVISO] El nodo '{instance_id}' está apagado o iniciando. Los comandos RCON solo están disponibles cuando está RUNNING."
        }
    resp = await cluster_manager.send_command(instance_id, cmd)
    return {"success": True, "response": resp}


@router.get("/api/cluster/tributes")
async def api_cluster_tributes():
    tributes = await asyncio.to_thread(cluster_manager.list_cluster_tributes)
    return {
        "cluster_id": settings.cluster_id,
        "tributes": tributes
    }


@router.delete("/api/cluster/tributes/{filename}")
async def api_cluster_tribute_delete(filename: str):
    ok = cluster_manager.delete_cluster_tribute(filename)
    if ok:
        activity_manager.log("Clúster", f"Archivo de tributo/obelisco eliminado: {filename}")
    return {"success": ok}


@router.post("/api/cluster/start_all")
async def api_cluster_start_all():
    activity_manager.log("Clúster", "Iniciando todos los mapas del clúster...")
    return await cluster_manager.start_all()


@router.post("/api/cluster/stop_all")
async def api_cluster_stop_all():
    activity_manager.log("Clúster", "Deteniendo todos los mapas del clúster...")
    return await cluster_manager.stop_all()


@router.post("/api/cluster/sync_rates")
async def api_cluster_sync_rates(req: ClusterRatesSyncRequest):
    res = ark_settings_manager.sync_rates_to_all(req.rates)
    activity_manager.log("Clúster", f"Multiplicadores sincronizados en {res.get('synced_nodes', 0)} nodos")
    return res
