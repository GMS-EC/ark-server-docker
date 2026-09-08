import os
import time
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from app.config import settings
from app.core.process_manager import process_manager
from app.core.backup_manager import backup_manager
from app.core.webhook_manager import webhook_manager

logger = logging.getLogger("arkserver.tasks")

class TaskScheduler:
    """
    Planificador de tareas y automatizaciones para ARK con paridad total con ark-server-docker:
    - Control de Horario de Encendido/Apagado (Power Schedule) respetando jugadores activos y avisos in-game.
    - Reinicio automático periódico cada X horas (AUTO_RESTART_HOURS) con cuenta regresiva.
    - Copias de seguridad automáticas con rotación (BACKUP_INTERVAL_HOURS).
    - Repoblación periódica de dinosaurios salvajes (Dino Wipe).
    - Limpieza automática de logs antiguos y crash dumps (>7 días).
    """
    def __init__(self):
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._last_backup_time = time.time()
        self._last_dino_wipe_time = time.time()
        self._last_restart_time = time.time()
        self._last_cleanup_time = time.time()
        self._schedule_warn_sent = False

    def start_loop(self):
        if not self._running:
            self._running = True
            self._loop_task = asyncio.create_task(self._scheduler_loop())

    def stop_loop(self):
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()

    async def _scheduler_loop(self):
        while self._running:
            try:
                now = time.time()
                cfg = settings.runtime_config

                # 1. Horario de Encendido / Apagado (Power Schedule)
                await self._check_power_schedule()

                # 2. Copia de seguridad automática
                backup_enabled = cfg.get("auto_backup_enabled", True) and os.getenv("BACKUP_ENABLED", "true").lower() in ("true", "1", "yes")
                if backup_enabled:
                    interval_sec = int(cfg.get("auto_backup_interval_hours", os.getenv("BACKUP_INTERVAL_HOURS", 6))) * 3600
                    if now - self._last_backup_time >= interval_sec:
                        self._last_backup_time = now
                        logger.info("Ejecutando copia de seguridad programada...")
                        await backup_manager.create_backup("auto")

                # 3. Dino Wipe automático
                if cfg.get("auto_dino_wipe_enabled", False):
                    wipe_interval_sec = int(cfg.get("auto_dino_wipe_hours", 24)) * 3600
                    if now - self._last_dino_wipe_time >= wipe_interval_sec:
                        self._last_dino_wipe_time = now
                        if process_manager.get_status() == "RUNNING":
                            logger.info("Ejecutando Dino Wipe programado...")
                            await process_manager.broadcast_log("[ARK Server Manager] Tarea automática: Ejecutando DestroyWildDinos...")
                            await process_manager.rcon.wipe_wild_dinos()
                            await webhook_manager.notify_dino_wipe()

                # 4. Reinicio automático periódico (AUTO_RESTART_HOURS)
                restart_hours = int(cfg.get("auto_restart_hours", os.getenv("AUTO_RESTART_HOURS", 0)))
                if restart_hours > 0:
                    restart_interval_sec = restart_hours * 3600
                    if now - self._last_restart_time >= restart_interval_sec:
                        self._last_restart_time = now
                        if process_manager.get_status() == "RUNNING":
                            logger.info(f"Iniciando reinicio automático periódico (cada {restart_hours}h)...")
                            await webhook_manager.notify_restart(restart_hours)
                            asyncio.create_task(self.trigger_safe_restart(countdown_minutes=5))

                # 5. Limpieza periódica de logs antiguos y crash dumps (>7 días)
                if now - self._last_cleanup_time >= 86400:
                    self._last_cleanup_time = now
                    self._cleanup_old_logs()

            except Exception as e:
                logger.error(f"Error en bucle de tareas: {e}")

            await asyncio.sleep(30)

    async def _check_power_schedule(self):
        """Monitorea la ventana de horario de juego configurada."""
        cfg = settings.runtime_config
        schedule_enabled = str(cfg.get("schedule_enabled", os.getenv("SCHEDULE_ENABLED", "false"))).lower() in ("true", "1", "yes")
        if not schedule_enabled:
            return

        start_str = cfg.get("schedule_start", os.getenv("SCHEDULE_START", "20:00"))
        stop_str = cfg.get("schedule_stop", os.getenv("SCHEDULE_STOP", "00:00"))
        warn_mins = int(cfg.get("schedule_warn_minutes", os.getenv("SCHEDULE_WARN_MINUTES", 10)))

        try:
            now_dt = datetime.now()
            now_minutes = now_dt.hour * 60 + now_dt.minute

            s_h, s_m = map(int, start_str.split(":"))
            start_minutes = s_h * 60 + s_m

            e_h, e_m = map(int, stop_str.split(":"))
            stop_minutes = e_h * 60 + e_m

            if start_minutes <= stop_minutes:
                in_window = start_minutes <= now_minutes < stop_minutes
                mins_until_stop = stop_minutes - now_minutes
            else:
                in_window = (now_minutes >= start_minutes) or (now_minutes < stop_minutes)
                if now_minutes >= start_minutes:
                    mins_until_stop = 1440 - now_minutes + stop_minutes
                else:
                    mins_until_stop = stop_minutes - now_minutes

            server_status = process_manager.get_status()

            # Caso A: Dentro de la ventana y el servidor está apagado -> autoencender
            if in_window:
                self._schedule_warn_sent = False
                if server_status == "OFFLINE" and process_manager.is_installed():
                    await process_manager.broadcast_log(f"[Horario] Dentro de horario activo ({start_str} - {stop_str}). Encendiendo servidor...")
                    await webhook_manager.notify_starting()
                    await process_manager.start_server()

            # Caso B: Servidor corriendo y aproximándose al límite de parada
            elif server_status == "RUNNING":
                if 0 < mins_until_stop <= warn_mins and not self._schedule_warn_sent:
                    warn_msg = f"[HORARIO] El horario activo finaliza en {mins_until_stop} min. El servidor se apagara en {stop_str}."
                    await process_manager.broadcast_log(f"[Horario] {warn_msg}")
                    await process_manager.rcon.broadcast(warn_msg)
                    await webhook_manager.notify_shutdown_warn(mins_until_stop)
                    self._schedule_warn_sent = True

                # Al llegar a la hora de parada, verificar jugadores activos
                if mins_until_stop <= 0 or not in_window:
                    # Consultar si hay jugadores
                    players = await process_manager.rcon.list_players()
                    if len(players) > 0:
                        await process_manager.broadcast_log(f"[Horario] Hora de apagado ({stop_str}) alcanzada pero hay {len(players)} superviviente(s) conectados. Posponiendo...")
                    else:
                        await process_manager.broadcast_log(f"[Horario] Hora de apagado ({stop_str}) alcanzada y 0 jugadores. Deteniendo servidor...")
                        await webhook_manager.send_discord_embed("SHUTDOWN")
                        await process_manager.stop_server()
                        self._schedule_warn_sent = False

        except Exception as e:
            logger.debug(f"Error evaluando horario programado: {e}")

    def _cleanup_old_logs(self):
        """Purga crash dumps (.dmp) y logs antiguos de más de 7 días."""
        cutoff = time.time() - (7 * 86400)
        logs_dirs = [
            settings.ark_data_dir / "ShooterGame" / "Saved" / "Logs",
            Path("/var/log/arktools")
        ]
        for ldir in logs_dirs:
            if ldir.exists() and ldir.is_dir():
                try:
                    for item in ldir.iterdir():
                        if item.is_file() and item.stat().st_mtime < cutoff:
                            if item.suffix in (".dmp", ".log", ".crashdump"):
                                item.unlink()
                except Exception:
                    pass

    async def trigger_safe_restart(self, countdown_minutes: int = 5):
        """Inicia un reinicio seguro con avisos in-game y guardado de mundo."""
        if process_manager.get_status() != "RUNNING":
            await process_manager.restart_server()
            return

        minutes_left = countdown_minutes
        while minutes_left > 0:
            msg = f"ATENCION: El servidor se reiniciara en {minutes_left} minuto{'s' if minutes_left > 1 else ''}."
            await process_manager.broadcast_log(f"[ARK Server Manager] {msg}")
            await process_manager.rcon.broadcast(msg)

            if minutes_left > 1:
                await asyncio.sleep(60)
                minutes_left -= 1
            else:
                await asyncio.sleep(50)
                await process_manager.rcon.broadcast("El servidor se reinicia en 10 segundos! Guardando...")
                await asyncio.sleep(10)
                minutes_left = 0

        await process_manager.restart_server()

task_scheduler = TaskScheduler()
