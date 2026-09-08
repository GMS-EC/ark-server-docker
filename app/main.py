import shutil
import os
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List

from fastapi import (
    FastAPI, WebSocket, WebSocketDisconnect, Depends,
    HTTPException, Request, Response, Form, status,
    UploadFile, File, Query
)
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from pydantic import BaseModel

from app.config import settings, BASE_DIR
from app.core.security import (
    create_session_token, verify_admin_credentials, is_authenticated,
    require_auth, check_login_rate_limit, record_failed_login, reset_failed_login,
    SESSION_COOKIE_NAME
)
from app.core.process_manager import process_manager
from app.core.player_manager import player_manager
from app.core.metrics_manager import metrics_manager
from app.core.ark_settings_manager import ark_settings_manager
from app.core.backup_manager import backup_manager
from app.core.file_manager import file_manager
from app.core.task_scheduler import task_scheduler
from app.core.webhook_manager import webhook_manager
from app.core.activity_manager import activity_manager
from app.core.cluster_manager import cluster_manager


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación ARK Server Manager."""
    metrics_manager.start()
    task_scheduler.start_loop()

    # Autoinicio si el servidor ya está instalado (producción) o si está activo en runtime_config
    autostart_cfg = settings.runtime_config.get("autostart_server", os.getenv("AUTOSTART_SERVER", "true").lower() in ("true", "1", "yes"))
    if autostart_cfg and process_manager.is_installed():
        async def _autostart():
            await asyncio.sleep(2)
            if process_manager.get_status() == "OFFLINE":
                activity_manager.log("Servidor", "Inicio automático activado al arrancar ARK Server Manager")
                await process_manager.start_server()
        asyncio.create_task(_autostart())

    yield
    task_scheduler.stop_loop()
    metrics_manager.stop()
    await process_manager.rcon.disconnect()


app = FastAPI(
    title="ARK Server Manager",
    description="Panel Web Ultra-ligero para Servidor de ARK: Survival Evolved",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Rutas estáticas y plantillas
web_dir = BASE_DIR / "web"
templates_dir = web_dir / "templates"
static_dir = web_dir / "static"

templates = Jinja2Templates(directory=str(templates_dir))
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/health")
async def health_check():
    """Healthcheck endpoint para Docker."""
    return {
        "status": "ok",
        "server_status": process_manager.get_status(),
        "installed": process_manager.is_installed()
    }


# --- Modelos Pydantic para API ---
class InstallServerRequest(BaseModel):
    world: str = "TheIsland"
    session_name: str = "ARK Server"
    server_password: Optional[str] = ""
    admin_password: str = "adminpass"
    max_players: int = 20
    server_pve: bool = False
    xp_multiplier: str = "1.0"
    taming_multiplier: str = "1.0"
    harvest_multiplier: str = "1.0"
    hatch_multiplier: str = "1.0"
    mature_multiplier: str = "1.0"
    mod_ids: Optional[str] = ""

class CommandRequest(BaseModel):
    command: str

class BroadcastRequest(BaseModel):
    message: str

class KickBanRequest(BaseModel):
    steam_id: str

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

class ModsUpdateRequest(BaseModel):
    mod_ids: str

class FileCompressRequest(BaseModel):
    path: str

class FileCreateRequest(BaseModel):
    path: str

# Retrocompatibilidad
FileWriteRequest = FileSaveRequest
class FileDeleteRequest(BaseModel):
    path: str

class BackupCreateRequest(BaseModel):
    name: Optional[str] = None

class BackupRestoreRequest(BaseModel):
    filename: str

class RestartCountdownRequest(BaseModel):
    minutes: int = 5

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


# --- Rutas de Vistas HTML ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    settings_data = ark_settings_manager.get_all_settings()
    current_metrics = metrics_manager.get_current_metrics()
    is_installed = process_manager.is_installed()
    
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "session_name": settings_data["server"]["session_name"],
            "world": settings_data["server"]["world"],
            "status": process_manager.get_status(),
            "is_installed": is_installed,
            "metrics": current_metrics,
            "max_players": settings_data["server"]["max_players"],
            "theme": settings.runtime_config.get("theme", "dark")
        }
    )

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})

@app.post("/login")
async def login_post(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    client_ip = request.client.host if request.client else "unknown"
    is_allowed, remaining_sec = check_login_rate_limit(client_ip)
    if not is_allowed:
        remaining_min = max(1, (remaining_sec + 59) // 60)
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": f"Demasiados intentos fallidos. Su IP ha sido bloqueada temporalmente. Intente nuevamente en {remaining_min} minuto(s)."},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )

    if verify_admin_credentials(username, password):
        reset_failed_login(client_ip)
        token = create_session_token(username)
        activity_manager.log("Seguridad", f"Inicio de sesión correcto para '{username}'", username)
        redirect = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        redirect.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            max_age=3600  # 60 minutos de caducidad
        )
        return redirect

    lockout_sec = record_failed_login(client_ip)
    if lockout_sec > 0:
        err_msg = "Ha superado el límite de 5 intentos fallidos. Su IP ha sido bloqueada por 10 minutos."
        activity_manager.log("Seguridad", f"IP {client_ip} bloqueada por 10 minutos tras 5 intentos fallidos", "Sistema")
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
    else:
        err_msg = "Usuario o contraseña incorrectos."
        activity_manager.log("Seguridad", f"Fallo de contraseña desde IP {client_ip}", "Anónimo")
        status_code = status.HTTP_401_UNAUTHORIZED

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": err_msg},
        status_code=status_code
    )

@app.get("/logout")
async def logout():
    res = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    res.delete_cookie(SESSION_COOKIE_NAME)
    return res


# --- WebSocket de Consola en Tiempo Real ---
@app.websocket("/ws/console")
async def websocket_console(websocket: WebSocket):
    await websocket.accept()
    process_manager.connected_websockets.add(websocket)

    # Enviar historial reciente del buffer de logs
    for line in list(process_manager.log_buffer):
        try:
            await websocket.send_text(line)
        except Exception:
            break

    try:
        while True:
            cmd = await websocket.receive_text()
            if cmd:
                await process_manager.send_command(cmd)
    except WebSocketDisconnect:
        pass
    finally:
        process_manager.connected_websockets.discard(websocket)


# --- Endpoints de API (Control de Servidor) ---
@app.get("/api/status", dependencies=[Depends(require_auth)])
async def api_status():
    players = await player_manager.get_online_players()
    metrics = metrics_manager.get_current_metrics()
    return {
        "status": process_manager.get_status(),
        "is_installed": process_manager.is_installed(),
        "players_online": len(players),
        "max_players": settings.max_players,
        "world": settings.world,
        "session_name": settings.session_name,
        "metrics": metrics
    }

@app.post("/api/server/install", dependencies=[Depends(require_auth)])
async def api_server_install(req: InstallServerRequest):
    """Guarda la configuración personalizada y comienza la descarga e instalación del servidor."""
    settings.world = req.world
    settings.session_name = req.session_name
    settings.server_password = req.server_password or ""
    settings.admin_ark_password = req.admin_password
    settings.max_players = req.max_players

    # Guardar en GameUserSettings.ini y Game.ini
    ark_settings_manager.save_settings({
        "server": {
            "session_name": req.session_name,
            "server_password": req.server_password or "",
            "admin_password": req.admin_password,
            "max_players": req.max_players
        },
        "multipliers": {
            "xp": req.xp_multiplier,
            "taming": req.taming_multiplier,
            "harvest": req.harvest_multiplier,
            "hatch": req.hatch_multiplier,
            "mature": req.mature_multiplier
        },
        "rules": {
            "pve_mode": req.server_pve
        }
    })

    activity_manager.log("Instalación", f"Iniciando instalación del servidor en mapa '{req.world}'...")
    asyncio.create_task(process_manager.install_server())
    return {"success": True, "message": "Instalación del servidor de ARK iniciada."}

@app.post("/api/server/start", dependencies=[Depends(require_auth)])
async def api_server_start():
    activity_manager.log("Servidor", "Iniciando servidor de ARK...")
    ok = await process_manager.start_server()
    if ok:
        await webhook_manager.notify_server_status(True)
    return {"success": ok, "status": process_manager.get_status()}

@app.post("/api/server/stop", dependencies=[Depends(require_auth)])
async def api_server_stop():
    activity_manager.log("Servidor", "Deteniendo servidor de ARK...")
    ok = await process_manager.stop_server()
    if ok:
        await webhook_manager.notify_server_status(False)
    return {"success": ok, "status": process_manager.get_status()}

@app.post("/api/server/restart", dependencies=[Depends(require_auth)])
async def api_server_restart():
    activity_manager.log("Servidor", "Reiniciando servidor de ARK...")
    ok = await process_manager.restart_server()
    return {"success": ok, "status": process_manager.get_status()}

@app.post("/api/server/restart_safe", dependencies=[Depends(require_auth)])
async def api_server_restart_safe(req: RestartCountdownRequest):
    activity_manager.log("Servidor", f"Reinicio seguro programado en {req.minutes} minutos...")
    asyncio.create_task(task_scheduler.trigger_safe_restart(req.minutes))
    return {"success": True, "message": f"Reinicio iniciado con cuenta regresiva de {req.minutes} min."}

@app.post("/api/server/command", dependencies=[Depends(require_auth)])
async def api_server_command(req: CommandRequest):
    resp = await process_manager.send_command(req.command)
    activity_manager.log("Consola", f"Comando: {req.command}")
    return {"response": resp}

@app.post("/api/server/saveworld", dependencies=[Depends(require_auth)])
async def api_server_saveworld():
    resp = await process_manager.rcon.save_world()
    activity_manager.log("ARK", "SaveWorld ejecutado")
    return {"success": True, "response": resp}

@app.post("/api/server/dinowipe", dependencies=[Depends(require_auth)])
async def api_server_dinowipe():
    resp = await process_manager.rcon.wipe_wild_dinos()
    activity_manager.log("ARK", "DestroyWildDinos (Dino Wipe) ejecutado")
    await webhook_manager.notify_dino_wipe()
    return {"success": True, "response": resp}

@app.post("/api/server/broadcast", dependencies=[Depends(require_auth)])
async def api_server_broadcast(req: BroadcastRequest):
    resp = await process_manager.rcon.broadcast(req.message)
    activity_manager.log("ARK", f"Broadcast: '{req.message}'")
    return {"success": True, "response": resp}


# --- Endpoints de Auditoría, Logs y Mods ---
@app.get("/api/activity", dependencies=[Depends(require_auth)])
async def api_activity():
    """Retorna el historial de eventos recientes de auditoría."""
    return {"activities": activity_manager.get_recent()}

@app.get("/api/server/logs/download", dependencies=[Depends(require_auth)])
async def api_download_logs():
    """Permite descargar el log completo del servidor de ARK."""
    log_path = settings.log_file
    if log_path.exists():
        return FileResponse(
            path=str(log_path),
            filename="ShooterGame.log",
            media_type="text/plain"
        )
    content = "\n".join(process_manager.log_buffer) if process_manager.log_buffer else "[ARK Server Manager] No hay registros disponibles aún."
    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=ShooterGame.log"}
    )

@app.get("/api/mods", dependencies=[Depends(require_auth)])
async def api_get_mods():
    """Obtiene la lista de mods configurados."""
    cfg = settings.runtime_config
    mod_ids_str = cfg.get("mod_ids", os.getenv("MOD_IDS", "")).strip()
    mods = [m.strip() for m in mod_ids_str.split(",") if m.strip()]
    return {
        "mod_ids_raw": mod_ids_str,
        "mods": mods,
        "count": len(mods)
    }

@app.post("/api/mods", dependencies=[Depends(require_auth)])
async def api_save_mods(req: ModsUpdateRequest):
    """Guarda la lista de mods en la configuración activa y arkmanager.cfg."""
    raw_mods = ",".join([m.strip() for m in req.mod_ids.split(",") if m.strip()])
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

@app.post("/api/mods/update", dependencies=[Depends(require_auth)])
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


# --- Endpoints de Jugadores ---
@app.get("/api/players", dependencies=[Depends(require_auth)])
async def api_players():
    online = await player_manager.get_online_players()
    history = player_manager.get_all_history()
    return {
        "online": online,
        "online_count": len(online),
        "history": history
    }

@app.post("/api/players/kick", dependencies=[Depends(require_auth)])
async def api_player_kick(req: KickBanRequest):
    resp = await player_manager.kick(req.steam_id)
    activity_manager.log("Jugadores", f"Superviviente expulsado: {req.steam_id}")
    return {"success": True, "response": resp}

@app.post("/api/players/ban", dependencies=[Depends(require_auth)])
async def api_player_ban(req: KickBanRequest):
    resp = await player_manager.ban(req.steam_id)
    activity_manager.log("Jugadores", f"Superviviente baneado: {req.steam_id}")
    return {"success": True, "response": resp}

@app.post("/api/players/unban", dependencies=[Depends(require_auth)])
async def api_player_unban(req: KickBanRequest):
    resp = await player_manager.unban(req.steam_id)
    activity_manager.log("Jugadores", f"Superviviente desbaneado: {req.steam_id}")
    return {"success": True, "response": resp}


# --- Endpoints de Métricas ---
@app.get("/api/metrics", dependencies=[Depends(require_auth)])
async def api_metrics():
    return {
        "current": metrics_manager.get_current_metrics(),
        "history": metrics_manager.get_history()
    }


# --- Endpoints de Configuración ---
@app.get("/api/settings", dependencies=[Depends(require_auth)])
async def api_get_settings():
    return ark_settings_manager.get_all_settings()

@app.post("/api/settings", dependencies=[Depends(require_auth)])
async def api_save_settings(payload: Dict[str, Any]):
    ok = ark_settings_manager.save_settings(payload)
    activity_manager.log("Configuración", "Configuraciones de ARK actualizadas")
    return {"success": ok}


# --- Endpoints de Tareas y Automatizaciones ---
@app.get("/api/tasks/config", dependencies=[Depends(require_auth)])
async def api_get_tasks_config():
    cfg = settings.runtime_config
    return {
        "schedule_enabled": cfg.get("schedule_enabled", False),
        "schedule_start": cfg.get("schedule_start", "20:00"),
        "schedule_stop": cfg.get("schedule_stop", "00:00"),
        "schedule_warn_mins": int(cfg.get("schedule_warn_mins", 10)),
        "auto_backup_enabled": cfg.get("auto_backup_enabled", True),
        "auto_backup_interval_hours": int(cfg.get("auto_backup_interval_hours", 6)),
        "auto_dino_wipe_enabled": cfg.get("auto_dino_wipe_enabled", False),
        "auto_restart_hours": int(cfg.get("auto_restart_hours", 0))
    }

@app.post("/api/tasks/config", dependencies=[Depends(require_auth)])
async def api_save_tasks_config(payload: Dict[str, Any]):
    settings.save_runtime_config(payload)
    activity_manager.log("Tareas", "Configuración de horarios y tareas automáticas actualizada")
    return {"success": True}



# --- Endpoints de Backups ---
@app.get("/api/backups", dependencies=[Depends(require_auth)])
async def api_backups_list():
    return {"backups": backup_manager.list_backups()}

@app.post("/api/backups/create", dependencies=[Depends(require_auth)])
async def api_backup_create(req: BackupCreateRequest):
    res = await backup_manager.create_backup(req.name)
    if res.get("success"):
        activity_manager.log("Backups", f"Copia creada: {res.get('filename')}")
        await webhook_manager.notify_backup(res.get("filename", ""), res.get("size_mb", 0.0))
    return res

@app.post("/api/backups/restore", dependencies=[Depends(require_auth)])
async def api_backup_restore(req: BackupRestoreRequest):
    res = await backup_manager.restore_backup(req.filename)
    activity_manager.log("Backups", f"Copia restaurada: {req.filename}")
    return res

@app.post("/api/backups/delete", dependencies=[Depends(require_auth)])
async def api_backup_delete(req: BackupRestoreRequest):
    ok = backup_manager.delete_backup(req.filename)
    activity_manager.log("Backups", f"Copia eliminada: {req.filename}")
    return {"success": ok}

@app.get("/api/backups/download/{filename}", dependencies=[Depends(require_auth)])
async def api_backup_download(filename: str):
    path = backup_manager.get_backup_path(filename)
    if not path:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path=str(path), filename=filename, media_type="application/gzip")


# --- Endpoints de Archivos (Dockraft Replicated Suite) ---
@app.get("/api/files/list", dependencies=[Depends(require_auth)])
async def file_list(path: str = Query("")):
    return file_manager.list_directory(path)

@app.get("/api/files/content", dependencies=[Depends(require_auth)])
async def file_content(path: str = Query(...)):
    return file_manager.read_file(path)

@app.post("/api/files/save", dependencies=[Depends(require_auth)])
async def file_save(req: FileSaveRequest):
    res = file_manager.write_file(req.path, req.content)
    activity_manager.log("Archivos", f"Archivo guardado: {req.path}")
    return res

@app.post("/api/files/folder", dependencies=[Depends(require_auth)])
async def file_folder(req: FolderCreateRequest):
    res = file_manager.create_folder(req.path)
    activity_manager.log("Archivos", f"Carpeta creada: {req.path}")
    return res

@app.delete("/api/files/delete", dependencies=[Depends(require_auth)])
async def file_delete(path: str = Query(...)):
    res = file_manager.delete_item(path)
    activity_manager.log("Archivos", f"Elemento eliminado: {path}")
    return res

@app.post("/api/files/upload", dependencies=[Depends(require_auth)])
async def file_upload(path: str = Form(""), file: UploadFile = File(...)):
    res = await file_manager.save_upload(path, file)
    activity_manager.log("Archivos", f"Archivo subido: {file.filename}")
    return res

@app.post("/api/files/unzip", dependencies=[Depends(require_auth)])
async def file_unzip(req: UnzipRequest):
    res = file_manager.extract_zip(req.path, req.target_dir)
    activity_manager.log("Archivos", f"Archivo extraído: {req.path}")
    return res

@app.get("/api/files/download", dependencies=[Depends(require_auth)])
async def file_download(path: str = Query(...)):
    safe_path = file_manager._resolve_safe_path(path)
    if not safe_path.exists() or not safe_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(
        str(safe_path),
        filename=safe_path.name,
        media_type="application/octet-stream"
    )

@app.post("/api/files/rename", dependencies=[Depends(require_auth)])
async def file_rename(req: FileRenameRequest):
    res = file_manager.rename_item(req.path, req.new_name)
    activity_manager.log("Archivos", f"Elemento renombrado a {req.new_name}")
    return res

@app.post("/api/files/duplicate", dependencies=[Depends(require_auth)])
async def file_duplicate(req: FileDuplicateRequest):
    res = file_manager.duplicate_item(req.path)
    activity_manager.log("Archivos", f"Elemento duplicado: {req.path}")
    return res

@app.post("/api/files/compress", dependencies=[Depends(require_auth)])
async def file_compress(req: FileCompressRequest):
    res = file_manager.compress_item(req.path)
    activity_manager.log("Archivos", f"Elemento comprimido: {req.path}")
    return res

@app.post("/api/files/create", dependencies=[Depends(require_auth)])
async def file_create(req: FileCreateRequest):
    res = file_manager.create_file(req.path)
    activity_manager.log("Archivos", f"Archivo creado: {req.path}")
    return res

# Retrocompatibilidad para llamadas previas
@app.get("/api/files/read", dependencies=[Depends(require_auth)])
async def api_files_read(path: str = Query(...)):
    return file_manager.read_file(path)

@app.post("/api/files/write", dependencies=[Depends(require_auth)])
async def api_files_write(req: FileSaveRequest):
    return file_manager.write_file(req.path, req.content)


# --- Endpoints de Actividad ---
@app.get("/api/activity", dependencies=[Depends(require_auth)])
async def api_activity():
    return {"items": activity_manager.get_recent()}


# --- Endpoints de Clúster & Multi-Instancia ---
@app.get("/api/cluster/status", dependencies=[Depends(require_auth)])
async def api_cluster_status():
    instances = cluster_manager.list_instances()
    online_nodes = sum(1 for i in instances if i.get("status") == "RUNNING")
    tributes = cluster_manager.list_cluster_tributes()
    return {
        "cluster_id": settings.cluster_id,
        "cluster_dir": str(settings.cluster_dir),
        "total_nodes": len(instances),
        "online_nodes": online_nodes,
        "tributes_count": len(tributes),
        "instances": instances
    }

@app.get("/api/cluster/instances", dependencies=[Depends(require_auth)])
async def api_cluster_instances():
    return {
        "instances": cluster_manager.list_instances(),
        "maps": cluster_manager.get_official_maps(),
        "suggested_ports": cluster_manager.suggest_next_ports(),
        "cluster_id": settings.cluster_id
    }

@app.post("/api/cluster/instances", dependencies=[Depends(require_auth)])
async def api_cluster_instance_create(req: ClusterInstanceCreateRequest):
    res = cluster_manager.create_instance(req.model_dump())
    if res.get("success"):
        activity_manager.log("Clúster", f"Nuevo mapa añadido al clúster: {req.name} ({req.map})")
    return res

@app.put("/api/cluster/instances/{instance_id}", dependencies=[Depends(require_auth)])
async def api_cluster_instance_update(instance_id: str, req: ClusterInstanceUpdateRequest):
    res = cluster_manager.update_instance(instance_id, req.model_dump(exclude_unset=True))
    if res.get("success"):
        activity_manager.log("Clúster", f"Instancia {instance_id} actualizada")
    return res

@app.delete("/api/cluster/instances/{instance_id}", dependencies=[Depends(require_auth)])
async def api_cluster_instance_delete(instance_id: str):
    res = cluster_manager.delete_instance(instance_id)
    if res.get("success"):
        activity_manager.log("Clúster", f"Instancia {instance_id} eliminada del clúster")
    return res

@app.post("/api/cluster/instances/{instance_id}/start", dependencies=[Depends(require_auth)])
async def api_cluster_instance_start(instance_id: str):
    ok = await cluster_manager.start_instance(instance_id)
    activity_manager.log("Clúster", f"Iniciando nodo {instance_id}...")
    return {"success": ok, "status": cluster_manager.get_instance_status(instance_id)}

@app.post("/api/cluster/instances/{instance_id}/stop", dependencies=[Depends(require_auth)])
async def api_cluster_instance_stop(instance_id: str):
    ok = await cluster_manager.stop_instance(instance_id)
    activity_manager.log("Clúster", f"Deteniendo nodo {instance_id}...")
    return {"success": ok, "status": cluster_manager.get_instance_status(instance_id)}

@app.post("/api/cluster/instances/{instance_id}/restart", dependencies=[Depends(require_auth)])
async def api_cluster_instance_restart(instance_id: str):
    ok = await cluster_manager.restart_instance(instance_id)
    activity_manager.log("Clúster", f"Reiniciando nodo {instance_id}...")
    return {"success": ok, "status": cluster_manager.get_instance_status(instance_id)}

@app.get("/api/cluster/tributes", dependencies=[Depends(require_auth)])
async def api_cluster_tributes():
    return {
        "cluster_id": settings.cluster_id,
        "tributes": cluster_manager.list_cluster_tributes()
    }

@app.delete("/api/cluster/tributes/{filename}", dependencies=[Depends(require_auth)])
async def api_cluster_tribute_delete(filename: str):
    ok = cluster_manager.delete_cluster_tribute(filename)
    if ok:
        activity_manager.log("Clúster", f"Archivo de tributo/obelisco eliminado: {filename}")
    return {"success": ok}

@app.post("/api/cluster/start_all", dependencies=[Depends(require_auth)])
async def api_cluster_start_all():
    activity_manager.log("Clúster", "Iniciando todos los mapas del clúster...")
    return await cluster_manager.start_all()

@app.post("/api/cluster/stop_all", dependencies=[Depends(require_auth)])
async def api_cluster_stop_all():
    activity_manager.log("Clúster", "Deteniendo todos los mapas del clúster...")
    return await cluster_manager.stop_all()

@app.post("/api/cluster/sync_rates", dependencies=[Depends(require_auth)])
async def api_cluster_sync_rates(req: ClusterRatesSyncRequest):
    res = cluster_manager.sync_rates_to_all(req.rates)
    activity_manager.log("Clúster", f"Multiplicadores sincronizados en {res.get('synced_nodes', 0)} nodos")
    return res

