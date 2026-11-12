from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.security import require_auth, require_api_rate_limit
from app.core.backup_manager import backup_manager
from app.core.activity_manager import activity_manager

router = APIRouter(tags=["backups"], dependencies=[Depends(require_auth)])


class BackupCreateRequest(BaseModel):
    name: Optional[str] = None


class BackupRestoreRequest(BaseModel):
    filename: str


@router.get("/api/backups")
async def api_backups_list():
    return {"backups": backup_manager.list_backups()}


@router.post(
    "/api/backups/create",
    dependencies=[Depends(require_api_rate_limit("backup_create", max_requests=5, window_seconds=60))],
)
async def api_backup_create(req: BackupCreateRequest):
    res = await backup_manager.create_backup(req.name)
    if res.get("success"):
        activity_manager.log("Backups", f"Copia creada: {res.get('filename')}")
    return res


@router.post("/api/backups/restore")
async def api_backup_restore(req: BackupRestoreRequest):
    res = await backup_manager.restore_backup(req.filename)
    if res.get("success"):
        activity_manager.log("Backups", f"Copia restaurada: {req.filename}")
    return res


@router.post("/api/backups/delete")
async def api_backup_delete(req: BackupRestoreRequest):
    ok = backup_manager.delete_backup(req.filename)
    if ok:
        activity_manager.log("Backups", f"Copia eliminada: {req.filename}")
    return {"success": ok}


@router.get("/api/backups/download/{filename}")
async def api_backup_download(filename: str):
    path = backup_manager.get_backup_path(filename)
    if not path:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path=str(path), filename=filename, media_type="application/gzip")
