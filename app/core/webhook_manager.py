import os
import httpx
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from app.config import settings

logger = logging.getLogger("arkserver.webhooks")

class WebhookManager:
    """
    Envía notificaciones enriquecidas con embeds a Discord para todos los eventos de ARK,
    con soporte bilingüe (español e inglés) y filtro granular de eventos estilo Dockraft.
    """
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=6.0)

    def _get_lang(self) -> str:
        return (settings.runtime_config.get("discord_language") or os.getenv("DISCORD_LANGUAGE", "es")).lower()

    def is_event_enabled(self, event_type: str) -> bool:
        """Comprueba si el usuario tiene habilitado este tipo de notificación en el panel."""
        events = settings.runtime_config.get("discord_events")
        if events is None:
            # Valores por defecto
            return True

        mapping = {
            "START": "start",
            "STARTING": "starting",
            "SHUTDOWN": "shutdown",
            "SHUTDOWN_WARN": "shutdown_warn",
            "BACKUP_OK": "backup",
            "BACKUP_FAIL": "backup",
            "RESTART": "restart",
            "WILD_DINOS_WIPED": "dino_wipe",
            "RESTORE_OK": "backup",
            "PLAYER_JOIN": "players",
            "PLAYER_LEAVE": "players",
            "TEST": "test"
        }
        event_key = mapping.get(event_type, "other")
        if event_key == "test":
            return True
        return bool(events.get(event_key, True))

    async def send_discord_embed(self, event_type: str, custom_description: Optional[str] = None) -> bool:
        webhook_url = settings.runtime_config.get("discord_webhook_url", "") or os.getenv("DISCORD_WEBHOOK_URL", "")
        if not webhook_url:
            return False

        if not self.is_event_enabled(event_type):
            logger.debug(f"Notificación de Discord para evento {event_type} deshabilitada por configuración del usuario.")
            return True

        lang = self._get_lang()
        color = 3447003
        title = "ℹ️ Notificación de ARK"
        status_text = "🟢 Online"

        if event_type == "STARTING":
            color = 15844367  # Yellow (#F1C40F)
            status_text = "⏳ Cargando / Starting"
            title = "⏳ Starting ARK Server" if lang == "en" else "⏳ Cargando Servidor de ARK"
            desc = custom_description or ("ARK server process started. Loading map and mods into memory..." if lang == "en" else "Proceso de ARK iniciado. Cargando mapa y mods en memoria...")
        elif event_type == "START":
            color = 3066993  # Green (#2ECC71)
            status_text = "🟢 Online"
            title = "🚀 ARK Server 100% Online" if lang == "en" else "🚀 Servidor de ARK Online"
            desc = custom_description or ("Server load complete! ARK server is 100% online and ready for players." if lang == "en" else "¡Carga completada! El servidor está 100% Online y disponible para jugar.")
        elif event_type == "SHUTDOWN_WARN":
            color = 15844367
            status_text = "⚠️ Programado / Scheduled"
            title = "⚠️ Scheduled Shutdown Warning" if lang == "en" else "⚠️ Aviso de Apagado Programado"
            desc = custom_description or ("Server will save and shut down soon according to schedule." if lang == "en" else "El servidor se guardará y apagará pronto según el horario programado.")
        elif event_type == "SHUTDOWN":
            color = 15158332  # Red (#E74C3C)
            status_text = "🔴 Offline"
            title = "🛑 ARK Server Offline" if lang == "en" else "🛑 Servidor de ARK Apagado"
            desc = custom_description or ("The server has shut down successfully." if lang == "en" else "El servidor se ha apagado correctamente.")
        elif event_type == "BACKUP_OK":
            color = 3447003  # Blue (#3498DB)
            status_text = "📦 Backup OK"
            title = "📦 Backup Created Successfully" if lang == "en" else "📦 Copia de Seguridad Completada"
            desc = custom_description or ("Backup completed successfully." if lang == "en" else "Copia de seguridad completada con éxito.")
        elif event_type == "BACKUP_FAIL":
            color = 15158332
            status_text = "⚠️ Backup Error"
            title = "⚠️ Backup Creation Failed" if lang == "en" else "⚠️ Fallo en Copia de Seguridad"
            desc = custom_description or ("Backup creation failed." if lang == "en" else "Falló la creación de la copia de seguridad.")
        elif event_type == "RESTART":
            color = 10181046  # Purple (#9B59B6)
            status_text = "🔄 Reiniciando / Restarting"
            title = "🔄 Server Restart Sequence" if lang == "en" else "🔄 Secuencia de Reinicio Programado"
            desc = custom_description or ("Server restart sequence initiated with in-game warnings." if lang == "en" else "Secuencia de reinicio iniciada con avisos in-game.")
        elif event_type == "WILD_DINOS_WIPED":
            color = 15105570  # Orange (#E67E22)
            status_text = "🦕 Dino Wipe"
            title = "🦕 Wild Dinos Wiped" if lang == "en" else "🦕 Repoblación de Dinos Salvajes"
            desc = custom_description or ("Wild dino population was wiped for fresh repopulation. Tamed dinos are safe." if lang == "en" else "Se reinició la fauna salvaje para repoblación limpia. Los dinos domesticados están a salvo.")
        elif event_type == "RESTORE_OK":
            color = 3066993
            status_text = "🔄 Restore OK"
            title = "🔄 Server Restored Successfully" if lang == "en" else "🔄 Servidor Restaurado con Éxito"
            desc = custom_description or ("Server save successfully restored from backup." if lang == "en" else "Servidor de ARK restaurado exitosamente desde la copia.")
        elif event_type == "PLAYER_JOIN":
            color = 3066993
            status_text = "👤 Superviviente / Player Joined"
            title = "👤 Player Connected" if lang == "en" else "👤 Superviviente Conectado"
            desc = custom_description or "Un superviviente se ha unido a la partida."
        elif event_type == "PLAYER_LEAVE":
            color = 9807270
            status_text = "👋 Superviviente / Player Left"
            title = "👋 Player Disconnected" if lang == "en" else "👋 Superviviente Desconectado"
            desc = custom_description or "Un superviviente ha salido de la partida."
        elif event_type == "TEST":
            color = 5814783  # Teal (#58B1FF)
            status_text = "🧪 Test / Prueba"
            title = "🧪 Discord Webhook Test" if lang == "en" else "🧪 Prueba de Webhook de Discord"
            desc = custom_description or ("This is a test notification sent from the ARK Server Manager web panel." if lang == "en" else "Esta es una notificación de prueba enviada exitosamente desde el panel web de ARK Server Manager.")
        else:
            desc = custom_description or "Evento de servidor"

        session_name = settings.session_name
        world = settings.world
        timestamp_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        payload = {
            "username": f"{session_name} - ARK Server",
            "avatar_url": "https://raw.githubusercontent.com/GMS-EC/ark-server-docker/main/Documents/logo.png",
            "embeds": [{
                "title": title,
                "description": desc,
                "color": color,
                "fields": [
                    {"name": "🎮 Servidor", "value": f"`{session_name}`", "inline": True},
                    {"name": "🗺️ Mapa", "value": f"`{world}`", "inline": True},
                    {"name": "📊 Estado", "value": status_text, "inline": True}
                ],
                "footer": {
                    "text": "ARK: Survival Evolved • ARK Server Manager",
                    "icon_url": "https://raw.githubusercontent.com/GMS-EC/ark-server-docker/main/Documents/logo.png"
                },
                "timestamp": timestamp_iso
            }]
        }

        try:
            resp = await self.client.post(webhook_url, json=payload)
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.debug(f"Error enviando webhook a Discord: {e}")
            return False

    async def notify_server_status(self, is_online: bool):
        await self.send_discord_embed("START" if is_online else "SHUTDOWN")

    async def notify_starting(self):
        await self.send_discord_embed("STARTING")

    async def notify_backup(self, filename: str, size_mb: float):
        lang = self._get_lang()
        msg = f"Backup `{filename}` ({size_mb} MB) completed successfully." if lang == "en" else f"Copia de seguridad `{filename}` ({size_mb} MB) completada exitosamente."
        await self.send_discord_embed("BACKUP_OK", msg)

    async def notify_backup_fail(self, error: str):
        lang = self._get_lang()
        msg = f"Backup failed: {error}" if lang == "en" else f"Error al generar respaldo: {error}"
        await self.send_discord_embed("BACKUP_FAIL", msg)

    notify_backup_failed = notify_backup_fail

    async def notify_restore(self, filename: str):
        lang = self._get_lang()
        msg = f"Server save successfully restored from `{filename}`." if lang == "en" else f"Servidor de ARK restaurado exitosamente desde `{filename}`."
        await self.send_discord_embed("RESTORE_OK", msg)

    async def notify_shutdown_warn(self, minutes_left: int):
        lang = self._get_lang()
        msg = f"Automatic scheduled shutdown in {minutes_left} minutes. Save your belongings!" if lang == "en" else f"Apagado automático programado en {minutes_left} minutos. ¡Guarda tus pertenencias!"
        await self.send_discord_embed("SHUTDOWN_WARN", msg)

    async def notify_restart(self, interval_hours: int):
        lang = self._get_lang()
        msg = f"Scheduled restart (every {interval_hours}h) initiated. 5 minutes in-game warning countdown." if lang == "en" else f"Reinicio periódico (cada {interval_hours}h) iniciado. Cuenta atrás de 5 minutos con avisos in-game."
        await self.send_discord_embed("RESTART", msg)

    async def notify_dino_wipe(self):
        await self.send_discord_embed("WILD_DINOS_WIPED")

webhook_manager = WebhookManager()
