import time
import json
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import (
    FastAPI, WebSocket, WebSocketDisconnect, Depends,
    HTTPException, Request, Response, Form, status
)
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from pydantic import BaseModel

from app.config import settings, BASE_DIR
from app.core.security import (
    create_session_token, verify_session_token, revoke_session_token,
    verify_admin_credentials, is_authenticated, is_auth_bypassed, is_request_secure,
    require_auth, require_api_rate_limit, check_login_rate_limit, record_failed_login, reset_failed_login,
    SESSION_COOKIE_NAME
)
from app.core.process_manager import process_manager
from app.core.rcon_client import redact_rcon_command
from app.core.player_manager import player_manager
from app.core.metrics_manager import metrics_manager
from app.core.ark_settings_manager import ark_settings_manager
from app.core.task_scheduler import task_scheduler
from app.core.webhook_manager import webhook_manager
from app.core.activity_manager import activity_manager
from app.core.cluster_manager import cluster_manager

from app.routers import (
    backups as backups_router,
    cluster as cluster_router,
    files as files_router,
    mods as mods_router,
    players as players_router,
    settings as settings_router,
    tasks as tasks_router,
    webhooks as webhooks_router,
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net/npm/chart.js@4.4.2/; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'"
        )
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación ARK Server Manager."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    sec_logger = logging.getLogger("arkserver.security")
    if not (settings.admin_password or "").strip():
        if is_auth_bypassed():
            sec_logger.warning("[SEGURIDAD] PANEL_PASSWORD está vacío con ALLOW_EMPTY_PASSWORD=true. El panel es accesible sin contraseña.")
        else:
            sec_logger.critical("[SEGURIDAD] CRÍTICO: PANEL_PASSWORD está vacío. El acceso al panel queda BLOQUEADO (fail-closed) hasta configurar PANEL_PASSWORD.")
    elif settings.admin_password == "adminpassword":
        sec_logger.warning("[SEGURIDAD] PANEL_PASSWORD usa el valor por defecto ('adminpassword'). Cámbielo en .env / docker-compose.yml.")
    if settings.admin_ark_password == "adminpass":
        sec_logger.warning("[SEGURIDAD] ADMIN_PASSWORD usa el valor por defecto ('adminpass'). Cámbielo en .env / docker-compose.yml.")
    metrics_manager.start()
    task_scheduler.start_loop()
    player_manager.start_monitor()

    if await asyncio.to_thread(process_manager._is_ark_process_running):
        if await process_manager.is_server_ready():
            process_manager.status = "RUNNING"
        else:
            process_manager.status = "STARTING"
            asyncio.create_task(process_manager._watch_server_readiness())

    autostart_cfg = settings.runtime_config.get(
        "autostart_server",
        os.getenv("AUTOSTART_SERVER", "true").lower() in ("true", "1", "yes")
    )
    if autostart_cfg and process_manager.is_installed():
        async def _autostart():
            await asyncio.sleep(2)
            if process_manager.get_status() == "OFFLINE":
                activity_manager.log("Servidor", "Inicio automático activado al arrancar ARK Server Manager")
                await webhook_manager.notify_starting()
                await process_manager.start_server()
        asyncio.create_task(_autostart())

    yield
    player_manager.stop_monitor()
    task_scheduler.stop_loop()
    metrics_manager.stop()
    if await asyncio.to_thread(process_manager._is_ark_process_running):
        try:
            print("[ARK Server Manager] [SEGURIDAD] Contenedor deteniéndose. Ejecutando guardado de mundo (SaveWorld)...")
            await process_manager.stop_server(grace_seconds=15)
        except Exception as e:
            print(f"[ARK Server Manager] Error durante guardado seguro al apagar: {e}")
    await process_manager.rcon.disconnect()
    activity_manager.flush()


app = FastAPI(
    title="ARK Server Manager",
    description="Panel Web Ultra-ligero para Servidor de ARK: Survival Evolved",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

web_dir = BASE_DIR / "web"
templates_dir = web_dir / "templates"
static_dir = web_dir / "static"

templates = Jinja2Templates(directory=str(templates_dir))
templates.env.globals["get_app_version"] = lambda: settings.app_version
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Registrar Routers Modulares
app.include_router(backups_router.router)
app.include_router(cluster_router.router)
app.include_router(files_router.router)
app.include_router(mods_router.router)
app.include_router(players_router.router)
app.include_router(settings_router.router)
app.include_router(tasks_router.router)
app.include_router(webhooks_router.router)


@app.get("/health")
async def health_check():
    """Healthcheck endpoint para Docker."""
    return {
        "status": "ok",
        "server_status": process_manager.get_status(),
        "installed": process_manager.is_installed()
    }


# --- Modelos Pydantic para Control del Servidor ---
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


class RestartCountdownRequest(BaseModel):
    minutes: int = 5


# --- Rutas de Vistas HTML y Autenticación ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    settings_data = await asyncio.to_thread(ark_settings_manager.get_all_settings)
    current_metrics = await metrics_manager.get_current_metrics_async()
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
            "theme": settings.runtime_config.get("theme", "dark"),
            "timezone": os.getenv("TZ", "America/Guayaquil"),
            "server_port": settings.server_port,
            "rcon_port": settings.rcon_port,
            "query_port": settings.query_port
        }
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    err = None
    if not (settings.admin_password or "").strip() and not is_auth_bypassed():
        err = "PANEL_PASSWORD está vacío. Configure una contraseña válida en el entorno para habilitar el acceso."
    return templates.TemplateResponse(request=request, name="login.html", context={"error": err})


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
            secure=is_request_secure(request),
            samesite="lax",
            max_age=3600
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
@app.post("/logout")
async def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        revoke_session_token(token)
    res = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    res.delete_cookie(SESSION_COOKIE_NAME)
    return res


# --- WebSocket de Consola en Tiempo Real (Soporta Instancia de Clúster) ---
@app.websocket("/ws/console")
async def websocket_console(websocket: WebSocket, instance: str = "main"):
    if not is_auth_bypassed():
        token = websocket.cookies.get(SESSION_COOKIE_NAME)
        if not token or not verify_session_token(token):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await websocket.accept()
    if instance == "main":
        process_manager.connected_websockets.add(websocket)
        for line in list(process_manager.log_buffer):
            try:
                await websocket.send_text(line)
            except Exception:
                break
        try:
            await _console_relay(websocket, process_manager.send_command)
        finally:
            process_manager.connected_websockets.discard(websocket)
    else:
        if instance not in cluster_manager.connected_websockets:
            cluster_manager.connected_websockets[instance] = set()
        cluster_manager.connected_websockets[instance].add(websocket)

        logs = cluster_manager.get_log_buffer(instance)
        for line in logs:
            try:
                await websocket.send_text(line)
            except Exception:
                break
        try:
            await _console_relay(
                websocket,
                lambda cmd: cluster_manager.send_command(instance, cmd)
            )
        finally:
            if instance in cluster_manager.connected_websockets:
                cluster_manager.connected_websockets[instance].discard(websocket)


WS_HEARTBEAT_TOKEN = "\u200b"
WS_HEARTBEAT_IDLE_SECONDS = 25


async def _console_relay(websocket: WebSocket, on_command) -> None:
    stop = asyncio.Event()

    async def _heartbeat():
        while not stop.is_set():
            try:
                await asyncio.sleep(WS_HEARTBEAT_IDLE_SECONDS)
                if stop.is_set():
                    return
                await websocket.send_text(WS_HEARTBEAT_TOKEN)
            except Exception:
                stop.set()
                return

    hb = asyncio.create_task(_heartbeat())
    try:
        while not stop.is_set():
            try:
                cmd = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception:
                break
            if stop.is_set():
                break
            if cmd:
                try:
                    await on_command(cmd)
                except Exception:
                    break
    finally:
        stop.set()
        hb.cancel()


# --- Endpoints de API (Control de Servidor, Métricas y Auditoría) ---
@app.get("/api/status", dependencies=[Depends(require_auth)])
async def api_status():
    players = await player_manager.get_online_players()
    metrics = await metrics_manager.get_current_metrics_async()
    return {
        "status": process_manager.get_status(),
        "is_installed": process_manager.is_installed(),
        "players_online": len(players),
        "max_players": settings.max_players,
        "world": settings.world,
        "session_name": settings.session_name,
        "metrics": metrics
    }


@app.post(
    "/api/server/install",
    dependencies=[Depends(require_auth), Depends(require_api_rate_limit("server_install", max_requests=3, window_seconds=60))],
)
async def api_server_install(req: InstallServerRequest):
    settings.world = req.world
    settings.session_name = req.session_name
    settings.server_password = req.server_password or ""
    settings.admin_ark_password = req.admin_password
    settings.max_players = req.max_players

    await asyncio.to_thread(
        ark_settings_manager.save_settings,
        {
            "server": {
                "world": req.world,
                "session_name": req.session_name,
                "server_password": req.server_password or "",
                "admin_password": req.admin_password,
                "max_players": req.max_players,
                "mod_ids": req.mod_ids or ""
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
        }
    )

    if "main" in cluster_manager._instances:
        map_title = "The Island" if req.world.lower() == "theisland" else req.world
        cluster_manager._instances["main"]["map"] = req.world
        cluster_manager._instances["main"]["name"] = f"Principal ({map_title})"
        cluster_manager._instances["main"]["session_name"] = req.session_name
        cluster_manager._instances["main"]["max_players"] = req.max_players
        cluster_manager._save_instances()

    activity_manager.log("Instalación", f"Iniciando instalación del servidor en mapa '{req.world}'...")
    asyncio.create_task(process_manager.install_server())
    return {"success": True, "message": "Instalación del servidor de ARK iniciada."}


@app.post("/api/server/start", dependencies=[Depends(require_auth)])
async def api_server_start():
    activity_manager.log("Servidor", "Iniciando servidor de ARK...")
    ok = await process_manager.start_server()
    if ok:
        await webhook_manager.notify_starting()
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


@app.post(
    "/api/server/command",
    dependencies=[Depends(require_auth), Depends(require_api_rate_limit("server_command", max_requests=30, window_seconds=60))],
)
async def api_server_command(req: CommandRequest):
    resp = await process_manager.send_command(req.command)
    activity_manager.log("Consola", f"Comando: {redact_rcon_command(req.command)}")
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


@app.post(
    "/api/server/broadcast",
    dependencies=[Depends(require_auth), Depends(require_api_rate_limit("server_broadcast", max_requests=20, window_seconds=60))],
)
async def api_server_broadcast(req: BroadcastRequest):
    try:
        resp = await process_manager.rcon.broadcast(req.message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    activity_manager.log("ARK", f"Broadcast: '{req.message}'")
    return {"success": True, "response": resp}


@app.get("/api/activity", dependencies=[Depends(require_auth)])
async def api_activity():
    return {"activities": activity_manager.get_recent()}


@app.get("/api/activity/download", dependencies=[Depends(require_auth)])
async def api_activity_download():
    logs = activity_manager.get_recent()
    content = json.dumps(logs, indent=2, ensure_ascii=False)
    filename = f"auditoria_ark_{time.strftime('%Y%m%d_%H%M%S')}.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/api/server/logs/download", dependencies=[Depends(require_auth)])
async def api_download_logs():
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


@app.get("/api/metrics", dependencies=[Depends(require_auth)])
async def api_metrics():
    curr = dict(await metrics_manager.get_current_metrics_async())
    try:
        players = await player_manager.get_online_players()
        curr["players_online"] = len(players)
    except Exception:
        curr["players_online"] = 0
    curr["max_players"] = settings.max_players
    return {
        "current": curr,
        "history": metrics_manager.get_history(),
        "disk_history": metrics_manager.get_disk_history(),
    }
