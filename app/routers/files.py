import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Form, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.security import require_auth
from app.core.file_manager import file_manager
from app.core.ark_settings_manager import ark_settings_manager
from app.core.activity_manager import activity_manager

logger = logging.getLogger("arkserver.files.router")
router = APIRouter(tags=["files"], dependencies=[Depends(require_auth)])


class FileSaveRequest(BaseModel):
    path: str
    content: str


class FolderCreateRequest(BaseModel):
    path: str


class UnzipRequest(BaseModel):
    path: str
    target_dir: str = ""


class FileRenameRequest(BaseModel):
    path: str
    new_name: str


class FileDuplicateRequest(BaseModel):
    path: str


class FileCompressRequest(BaseModel):
    path: str


class FileCreateRequest(BaseModel):
    path: str


@router.get("/api/files/list")
async def file_list(path: str = Query("")):
    try:
        return await asyncio.to_thread(file_manager.list_directory, path)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error listando directorio '%s': %s", path, e)
        raise HTTPException(status_code=500, detail="Error interno al listar directorio.")


@router.get("/api/files/content")
async def file_content(path: str = Query(...)):
    # Asegurar que existan GameUserSettings.ini y Game.ini si se solicitan directamente
    if path.endswith(("GameUserSettings.ini", "Game.ini")):
        ark_settings_manager._ensure_paths()
    return await asyncio.to_thread(file_manager.read_file, path)


@router.post("/api/files/save")
async def file_save(req: FileSaveRequest):
    res = await asyncio.to_thread(file_manager.write_file, req.path, req.content)
    activity_manager.log("Archivos", f"Archivo guardado: {req.path}")
    return res


@router.post("/api/files/folder")
async def file_folder(req: FolderCreateRequest):
    res = await asyncio.to_thread(file_manager.create_folder, req.path)
    activity_manager.log("Archivos", f"Carpeta creada: {req.path}")
    return res


@router.delete("/api/files/delete")
async def file_delete(path: str = Query(...)):
    res = await asyncio.to_thread(file_manager.delete_item, path)
    activity_manager.log("Archivos", f"Elemento eliminado: {path}")
    return res


@router.post("/api/files/upload")
async def file_upload(path: str = Form(""), file: UploadFile = File(...)):
    res = await file_manager.save_upload(path, file)
    activity_manager.log("Archivos", f"Archivo subido: {file.filename}")
    return res


@router.post("/api/files/unzip")
async def file_unzip(req: UnzipRequest):
    res = await asyncio.to_thread(file_manager.extract_zip, req.path, req.target_dir)
    activity_manager.log("Archivos", f"Archivo extraído: {req.path}")
    return res


@router.get("/api/files/download")
async def file_download(path: str = Query(...)):
    safe_path = file_manager.resolve_download(path)
    return FileResponse(
        str(safe_path),
        filename=safe_path.name,
        media_type="application/octet-stream"
    )


@router.post("/api/files/create")
async def file_create(req: FileCreateRequest):
    res = await asyncio.to_thread(file_manager.create_file, req.path)
    activity_manager.log("Archivos", f"Archivo creado: {req.path}")
    return res


@router.post("/api/files/duplicate")
async def file_duplicate(req: FileDuplicateRequest):
    res = await asyncio.to_thread(file_manager.duplicate_item, req.path)
    activity_manager.log("Archivos", f"Elemento duplicado: {req.path}")
    return res


@router.post("/api/files/compress")
async def file_compress(req: FileCompressRequest):
    res = await asyncio.to_thread(file_manager.compress_item, req.path)
    activity_manager.log("Archivos", f"Elemento comprimido: {req.path}")
    return res


@router.post("/api/files/rename")
async def file_rename(req: FileRenameRequest):
    res = await asyncio.to_thread(file_manager.rename_item, req.path, req.new_name)
    activity_manager.log("Archivos", f"Elemento renombrado a {req.new_name}")
    return res


# Retrocompatibilidad para llamadas previas
@router.get("/api/files/read")
async def api_files_read(path: str = Query(...)):
    return await asyncio.to_thread(file_manager.read_file, path)


@router.post("/api/files/write")
async def api_files_write(req: FileSaveRequest):
    return await asyncio.to_thread(file_manager.write_file, req.path, req.content)
