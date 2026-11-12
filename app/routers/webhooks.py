import os
from typing import Dict, Any
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.security import require_auth
from app.core.webhook_manager import webhook_manager, is_safe_webhook_url, mask_webhook_url, SECRET_MASK
from app.core.activity_manager import activity_manager

router = APIRouter(tags=["webhooks"], dependencies=[Depends(require_auth)])


@router.get("/api/webhooks")
async def api_get_webhooks():
    cfg = settings.runtime_config
    events = cfg.get("discord_events", {
        "start": True,
        "starting": True,
        "shutdown": True,
        "shutdown_warn": True,
        "backup": True,
        "dino_wipe": True,
        "restart": True,
        "players": False
    })
    raw_url = cfg.get("discord_webhook_url", "") or os.getenv("DISCORD_WEBHOOK_URL", "")
    return {
        "url": mask_webhook_url(raw_url),
        "has_url": bool(raw_url),
        "language": cfg.get("discord_language", "es"),
        "events": events
    }


@router.post("/api/webhooks")
async def api_save_webhooks(req: Dict[str, Any]):
    url = req.get("url", "").strip()
    lang = req.get("language", "es").strip().lower()
    events = req.get("events", {})

    if SECRET_MASK in url or "••••" in url:
        url = settings.runtime_config.get("discord_webhook_url", "") or os.getenv("DISCORD_WEBHOOK_URL", "")
    elif url and not is_safe_webhook_url(url):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "URL de Webhook no válida o bloqueada por seguridad (SSRF)."}
        )

    settings.save_runtime_config({
        "discord_webhook_url": url,
        "discord_language": lang,
        "discord_events": events
    })
    activity_manager.log("Webhooks", f"Configuración de Webhook guardada (Idioma: {lang})")
    return {"success": True}


@router.post("/api/webhooks/test")
async def api_test_webhook():
    ok = await webhook_manager.send_discord_embed(
        "TEST",
        "¡Notificación de prueba entregada con éxito desde el panel web de ARK Server Manager!"
    )
    if ok:
        activity_manager.log("Webhooks", "Notificación de prueba enviada a Discord con éxito")
        return {"success": True}
    return {"success": False, "error": "No se pudo entregar el mensaje. Verifica que la URL del Webhook sea válida."}
