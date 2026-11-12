import os
import time
import shutil
import asyncio
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.config import settings
from app.core.security import require_auth
from app.core.process_manager import process_manager
from app.core.activity_manager import activity_manager

router = APIRouter(prefix="/api/mods", tags=["mods"], dependencies=[Depends(require_auth)])

STEAM_WORKSHOP_API = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
_WORKSHOP_CACHE: Dict[str, Tuple[Dict[str, Any], float]] = {}
_WORKSHOP_CACHE_TTL = 600.0  # 10 minutos


class ModsUpdateRequest(BaseModel):
    mod_ids: str


def _get_local_mod_info(mod_id: str) -> Dict[str, Any]:
    """Inspecciona ShooterGame/Content/Mods/<mod_id> para verificar instalación local y fecha."""
    mods_dir = settings.ark_data_dir / "ShooterGame" / "Content" / "Mods"
    mod_folder = mods_dir / str(mod_id)
    mod_meta = mods_dir / f"{mod_id}.mod"
    installed = mod_folder.exists() or mod_meta.exists()
    local_mtime = 0
    if mod_meta.exists():
        try:
            local_mtime = int(mod_meta.stat().st_mtime)
        except OSError:
            pass
    if mod_folder.exists():
        try:
            folder_mtime = int(mod_folder.stat().st_mtime)
            local_mtime = max(local_mtime, folder_mtime)
        except OSError:
            pass
    return {
        "installed_locally": installed,
        "local_updated_ts": local_mtime,
        "local_updated_str": datetime.fromtimestamp(local_mtime).strftime("%d/%m/%Y %H:%M") if local_mtime > 0 else None
    }


async def fetch_workshop_details(mod_ids: List[str], force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
    """Consulta la API pública de Steam Workshop para enriquecer mods con nombre, miniatura y actualizaciones."""
    clean_ids = [m.strip() for m in mod_ids if m.strip().isdigit()]
    if not clean_ids:
        return {}

    now = time.time()
    results: Dict[str, Dict[str, Any]] = {}
    to_fetch: List[str] = []

    for mid in clean_ids:
        cached = _WORKSHOP_CACHE.get(mid)
        if not force_refresh and cached and (now - cached[1] < _WORKSHOP_CACHE_TTL):
            results[mid] = dict(cached[0])
        else:
            to_fetch.append(mid)

    if to_fetch:
        form_data: Dict[str, str] = {"itemcount": str(len(to_fetch))}
        for idx, mid in enumerate(to_fetch):
            form_data[f"publishedfileids[{idx}]"] = mid

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.post(STEAM_WORKSHOP_API, data=form_data)
                if resp.status_code == 200:
                    payload = resp.json()
                    details_list = payload.get("response", {}).get("publishedfiledetails", [])
                    for item in details_list:
                        mid = str(item.get("publishedfileid", ""))
                        if not mid:
                            continue
                        time_updated = int(item.get("time_updated", 0) or 0)
                        file_size = int(item.get("file_size", 0) or 0)
                        info = {
                            "id": mid,
                            "title": item.get("title") or f"Workshop Mod #{mid}",
                            "preview_url": item.get("preview_url") or "",
                            "creator": item.get("creator") or "",
                            "file_size_mb": round(file_size / (1024 * 1024), 2) if file_size > 0 else 0.0,
                            "time_updated": time_updated,
                            "remote_updated_str": datetime.fromtimestamp(time_updated).strftime("%d/%m/%Y %H:%M") if time_updated > 0 else None,
                            "subscriptions": int(item.get("subscriptions", 0) or 0),
                            "Banned": bool(item.get("banned", 0)),
                        }
                        _WORKSHOP_CACHE[mid] = (info, now)
                        results[mid] = dict(info)
        except Exception:
            pass

    # Enriquecer con estado local y detección de actualizaciones pendientes
    for mid in clean_ids:
        base = results.get(mid, {
            "id": mid,
            "title": f"Steam Workshop Mod #{mid}",
            "preview_url": "",
            "creator": "",
            "file_size_mb": 0.0,
            "time_updated": 0,
            "remote_updated_str": None,
            "subscriptions": 0,
        })
        local_info = _get_local_mod_info(mid)
        base.update(local_info)
        remote_ts = int(base.get("time_updated") or 0)
        local_ts = int(local_info.get("local_updated_ts") or 0)
        # Si está instalado localmente y Steam tiene una versión más reciente (>60s de margen)
        base["update_available"] = bool(local_info["installed_locally"] and remote_ts > 0 and local_ts > 0 and remote_ts > local_ts + 60)
        results[mid] = base

    return results


@router.get("")
async def api_get_mods(enrich: bool = Query(True), refresh: bool = Query(False)):
    """Obtiene la lista de mods configurados y sus metadatos enriquecidos de Steam Workshop."""
    cfg = settings.runtime_config
    mod_ids_str = cfg.get("mod_ids", os.getenv("MOD_IDS", "")).strip()
    mods = [m.strip() for m in mod_ids_str.split(",") if m.strip()]
    details: Dict[str, Dict[str, Any]] = {}
    if enrich and mods:
        details = await fetch_workshop_details(mods, force_refresh=refresh)

    updates_count = sum(1 for d in details.values() if d.get("update_available"))
    return {
        "mod_ids_raw": mod_ids_str,
        "mods": mods,
        "count": len(mods),
        "details": details,
        "updates_available": updates_count
    }


@router.post("")
async def api_save_mods(req: ModsUpdateRequest):
    """Guarda la lista de mods en la configuración activa y arkmanager.cfg."""
    raw_mods = ",".join([m.strip() for m in req.mod_ids.split(",") if m.strip()])
    if raw_mods:
        for token in raw_mods.split(","):
            if not token.strip().isdigit():
                return {"success": False, "error": "La lista de mods solo puede contener IDs numéricos separados por comas."}

    settings.runtime_config["mod_ids"] = raw_mods
    settings.save_runtime_config({"mod_ids": raw_mods})

    cfg_file = Path("/etc/arkmanager/arkmanager.cfg")
    if cfg_file.exists():
        try:
            lines = cfg_file.read_text(encoding="utf-8").splitlines()
            new_lines = [line for line in lines if not line.startswith("ark_GameModIds=")]
            if raw_mods:
                new_lines.append(f'ark_GameModIds="{raw_mods}"')
            cfg_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        except Exception:
            pass

    count = len(raw_mods.split(",")) if raw_mods else 0
    activity_manager.log("Mods", f"Lista de mods actualizada ({count} mods configurados)")
    return {"success": True, "mod_ids": raw_mods, "count": count}


@router.post("/update")
async def api_update_mods():
    """Ejecuta la actualización y descarga de mods en segundo plano."""
    activity_manager.log("Mods", "Iniciando verificación y actualización de mods...")
    await process_manager.broadcast_log("[ARK Server Manager] Comprobando y actualizando mods de Steam Workshop...")
    if shutil.which("arkmanager"):
        async def _run_update():
            proc = await asyncio.create_subprocess_exec(
                "arkmanager", "update", "--no-background", "--update-mods", "@main",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                await process_manager.broadcast_log(f"[ArkManager] {line.decode('utf-8', errors='replace').rstrip()}")
            await proc.wait()
            await process_manager.broadcast_log("[ARK Server Manager] Actualización de mods finalizada.")
        asyncio.create_task(_run_update())
        return {"success": True, "message": "Actualización de mods iniciada en segundo plano."}
    else:
        await process_manager.broadcast_log("[ARK Server Manager] Simulación: Mods actualizados correctamente.")
        return {"success": True, "message": "Simulación: Mods actualizados."}
