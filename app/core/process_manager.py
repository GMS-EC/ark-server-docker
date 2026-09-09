import os
import sys
import time
import shutil
import asyncio
import psutil
from collections import deque
from pathlib import Path
from typing import Set, List, Deque, Dict, Any, Optional
from fastapi import WebSocket

from app.config import settings
from app.core.rcon_client import ArkRconClient

class ProcessManager:
    """
    Controlador del ciclo de vida del servidor dedicado de ARK.
    Maneja la instalación previa bajo demanda con SteamCMD, el inicio,
    la detención segura con guardado de mundo (SaveWorld),
    monitoreo de logs en tiempo real vía WebSockets y ejecución de comandos RCON.
    """
    def __init__(self):
        self.process: Optional[asyncio.subprocess.Process] = None
        self.status: str = "OFFLINE"  # OFFLINE, STARTING, RUNNING, STOPPING, INSTALLING
        self.connected_websockets: Set[WebSocket] = set()
        self.log_buffer: Deque[str] = deque(maxlen=1000)
        self._reader_task: Optional[asyncio.Task] = None
        self._log_file_task: Optional[asyncio.Task] = None
        self.started_at: Optional[float] = None
        self._intentional_stop: bool = False
        self._server_up_detected: bool = False
        
        # Cliente RCON dedicado
        self.rcon = ArkRconClient(
            host=settings.rcon_host,
            port=settings.rcon_port,
            password=settings.admin_ark_password
        )

    def is_installed(self) -> bool:
        """Verifica si los binarios del servidor de ARK están instalados."""
        bin_path = settings.ark_data_dir / "ShooterGame" / "Binaries" / "Linux" / "ShooterGameServer"
        return bin_path.exists()

    def get_status(self) -> str:
        if self.status in ("INSTALLING", "STOPPING"):
            return self.status

        # Si se encuentra en fase de arranque (STARTING), se mantiene fielmente en STARTING
        # hasta que _watch_server_readiness() termine de certificar que el servidor cargó el mapa
        if self.status == "STARTING":
            if self.process and self.process.returncode is not None:
                self.status = "OFFLINE"
                return "OFFLINE"
            return "STARTING"

        is_running = self._is_ark_process_running()

        if not is_running:
            self.status = "OFFLINE"
            return "OFFLINE"

        if self.status == "OFFLINE":
            self.status = "RUNNING"
            return "RUNNING"

        return self.status

    def _is_ark_process_running(self) -> bool:
        if self.process and self.process.returncode is None:
            return True
        try:
            main_port_str = f"Port={settings.server_port}"
            for p in psutil.process_iter(['name', 'cmdline']):
                name = p.info.get('name') or ''
                cmdline_list = p.info.get('cmdline') or []
                cmdline = ' '.join(cmdline_list)
                if 'ShooterGameServer' in name or 'ShooterGameServer' in cmdline:
                    has_other_port = any("Port=" in arg and main_port_str not in arg for arg in cmdline_list)
                    if not has_other_port:
                        return True
        except Exception:
            pass
        return False

    def get_server_pid(self) -> Optional[int]:
        if self.process and self.process.returncode is None:
            return self.process.pid
        try:
            main_port_str = f"Port={settings.server_port}"
            for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                name = p.info.get('name') or ''
                cmdline_list = p.info.get('cmdline') or []
                cmdline = ' '.join(cmdline_list)
                if 'ShooterGameServer' in name or 'ShooterGameServer' in cmdline:
                    has_other_port = any("Port=" in arg and main_port_str not in arg for arg in cmdline_list)
                    if not has_other_port:
                        return p.info['pid']
        except Exception:
            pass
        return None

    async def broadcast_log(self, message: str) -> None:
        """Añade un log al buffer y lo difunde a todos los clientes web conectados."""
        clean_line = message.rstrip("\r\n")
        if not clean_line:
            return
        self.log_buffer.append(clean_line)
        dead_ws = set()
        for ws in self.connected_websockets:
            try:
                await ws.send_text(clean_line)
            except Exception:
                dead_ws.add(ws)
        self.connected_websockets.difference_update(dead_ws)

    async def install_server(self) -> bool:
        """
        Descarga e instala el servidor de ARK usando SteamCMD o arkmanager bajo demanda.
        Transmite en tiempo real el progreso de descarga a la consola web.
        """
        if self.status in ("RUNNING", "STARTING", "INSTALLING"):
            await self.broadcast_log("[ARK Server Manager] Ya hay una tarea o proceso en ejecución.")
            return False

        self.status = "INSTALLING"
        await self.broadcast_log("=========================================================")
        await self.broadcast_log(" [SteamCMD] INICIANDO INSTALACIÓN DEL SERVIDOR DE ARK ")
        await self.broadcast_log("=========================================================")
        await self.broadcast_log(f"[ARK Server Manager] Directorio destino: {settings.ark_data_dir}")
        await self.broadcast_log("[ARK Server Manager] Descargando AppID 376030 vía SteamCMD. Esto puede demorar varios minutos...")

        cmd = []
        if shutil.which("arkmanager"):
            cmd = ["arkmanager", "install", "@main"]
        elif shutil.which("steamcmd"):
            cmd = [
                "steamcmd",
                "+force_install_dir", str(settings.ark_data_dir),
                "+login", "anonymous",
                "+app_update", "376030", "validate",
                "+quit"
            ]
        elif Path("/home/steam/steamcmd/steamcmd.sh").exists():
            cmd = [
                "bash", "/home/steam/steamcmd/steamcmd.sh",
                "+force_install_dir", str(settings.ark_data_dir),
                "+login", "anonymous",
                "+app_update", "376030", "validate",
                "+quit"
            ]
        else:
            # Modo Simulación para desarrollo local
            cmd = [
                sys.executable, "-c",
                "import time, sys\n"
                "print('[SteamCMD] Connecting to Steam Public servers...')\n"
                "time.sleep(1)\n"
                "print('[SteamCMD] Logging in as anonymous... OK')\n"
                "time.sleep(1)\n"
                "print('[SteamCMD] Update state (0x3) downloading, progress: 25.4%')\n"
                "time.sleep(1)\n"
                "print('[SteamCMD] Update state (0x3) downloading, progress: 78.1%')\n"
                "time.sleep(1)\n"
                "print('[SteamCMD] Success! App 376030 fully installed.')\n"
            ]

        try:
            install_proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=os.environ.copy()
            )

            while True:
                line = await install_proc.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace")
                await self.broadcast_log(decoded)

            await install_proc.wait()

            if install_proc.returncode == 0:
                await self.broadcast_log("[ARK Server Manager] [OK] ¡Instalación del servidor completada exitosamente!")
                # Crear binario falso si estábamos simulando para marcar como instalado
                bin_dir = settings.ark_data_dir / "ShooterGame" / "Binaries" / "Linux"
                bin_dir.mkdir(parents=True, exist_ok=True)
                (bin_dir / "ShooterGameServer").touch(exist_ok=True)
                self.status = "OFFLINE"
                return True
            else:
                await self.broadcast_log(f"[ARK Server Manager] [ERROR] Error durante la instalación (Código: {install_proc.returncode}).")
                self.status = "OFFLINE"
                return False
        except Exception as e:
            await self.broadcast_log(f"[ARK Server Manager] Error ejecutando instalador: {e}")
            self.status = "OFFLINE"
            return False

    async def start_server(self) -> bool:
        """Arranca el servidor de ARK."""
        if self.status in ("RUNNING", "STARTING", "INSTALLING") or self._is_ark_process_running():
            await self.broadcast_log("[ARK Server Manager] El servidor ya se encuentra en ejecución o iniciando.")
            return False

        if not self.is_installed() and shutil.which("arkmanager"):
            await self.broadcast_log("[ARK Server Manager] [AVISO] El servidor no está instalado. Por favor configúralo e inicia la descarga desde el Asistente de Instalación.")
            return False

        self.status = "STARTING"
        self._intentional_stop = False
        self.started_at = time.time()
        await self.broadcast_log(f"[ARK Server Manager] Iniciando servidor de ARK ({settings.session_name} - Mapa: {settings.world})...")

        start_script = settings.base_dir / "scripts" / "start.sh"
        global_script = Path("/home/steam/scripts/start.sh")
        cmd = []
        if global_script.exists():
            cmd = ["bash", str(global_script)]
        elif start_script.exists():
            cmd = ["bash", str(start_script)]
        elif shutil.which("arkmanager"):
            cmd = ["arkmanager", "run", "@main"]
        else:
            cmd = [sys.executable, "-c", "import time; print('[ShooterGame] ARK Server Simulation Running...'); [time.sleep(2) for _ in range(300)]"]

        try:
            start_env = os.environ.copy()
            start_env["SESSION_NAME"] = settings.session_name
            start_env["SERVER_PASSWORD"] = settings.server_password
            start_env["ADMIN_PASSWORD"] = settings.admin_ark_password
            start_env["MAX_PLAYERS"] = str(settings.max_players)
            start_env["WORLD"] = settings.world
            start_env["MOD_IDS"] = str(settings.runtime_config.get("mod_ids", os.getenv("MOD_IDS", "")))
            start_env["CLUSTER_ID"] = str(settings.runtime_config.get("cluster_id", os.getenv("CLUSTER_ID", "")))
            start_env["ADDITIONAL_ARGS"] = str(settings.runtime_config.get("additional_args", os.getenv("ADDITIONAL_ARGS", "")))
            start_env["UPDATE_ON_START"] = "true" if settings.runtime_config.get("update_on_start", True) else "false"
            start_env["BATTLEEYE"] = "true" if settings.runtime_config.get("battleeye", False) else "false"
            start_env["SERVER_PORT"] = str(settings.server_port)
            start_env["QUERY_PORT"] = str(settings.query_port)
            start_env["RCON_PORT"] = str(settings.rcon_port)
            start_env["RCON_ENABLED"] = "True" if settings.rcon_enabled else "False"
            start_env["CLUSTER_DIR_OVERRIDE"] = str(settings.cluster_dir)

            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=start_env
            )
            self._reader_task = asyncio.create_task(self._stream_output(self.process))
            self._log_file_task = asyncio.create_task(self._stream_log_file())
            self.status = "STARTING"
            await self.broadcast_log(f"[ARK Server Manager] Proceso de arranque iniciado (PID: {self.process.pid}). Cargando mundo y mods en memoria...")
            asyncio.create_task(self._watch_server_readiness())
            return True
        except Exception as e:
            self.status = "OFFLINE"
            await self.broadcast_log(f"[ARK Server Manager] Error al iniciar el servidor: {e}")
            return False

    async def _stream_output(self, process: asyncio.subprocess.Process):
        while True:
            if process.stdout is None:
                break
            line = await process.stdout.readline()
            if not line:
                break
            decoded = line.decode("utf-8", errors="replace")
            if "Server is up" in decoded or "Server is ready" in decoded:
                self._server_up_detected = True
            await self.broadcast_log(decoded)

        await process.wait()
        
        # Si arkmanager arrancó ShooterGameServer en segundo plano (demonio), monitorearlo activamente
        if self._is_ark_process_running():
            self.status = "RUNNING"
            while self._is_ark_process_running():
                await asyncio.sleep(2)

        if not self._intentional_stop:
            await self.broadcast_log(f"[ARK Server Manager] El servidor de ARK se ha detenido.")
        self.status = "OFFLINE"
        await self.rcon.disconnect()

    async def _stream_log_file(self):
        log_path = settings.log_file
        for _ in range(60):
            if log_path.exists():
                break
            await asyncio.sleep(1)

        if not log_path.exists():
            return

        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(0, os.SEEK_END)
                while self.status in ("STARTING", "RUNNING"):
                    line = f.readline()
                    if line:
                        clean_l = line.rstrip("\r\n")
                        if clean_l:
                            await self.broadcast_log(f"[ShooterGame] {clean_l}")
                    else:
                        await asyncio.sleep(0.5)
                        f.seek(f.tell())
        except Exception:
            pass

    async def is_server_ready(self) -> bool:
        """Comprueba si el servidor de ARK está listo conectándose al puerto RCON o por detección directa."""
        if getattr(self, "_server_up_detected", False):
            return True
        # 1. Intentar conectar al puerto RCON vía TCP
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", settings.rcon_port),
                timeout=1.5
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            pass

        # 2. Intentar autenticar con cliente RCON
        try:
            if self.rcon:
                ok = await self.rcon.connect(timeout=2.0)
                if ok:
                    chat = await self.rcon.get_chat()
                    if chat is not None:
                        return True
        except Exception:
            pass

        return False

    async def _watch_server_readiness(self):
        """Monitorea hasta que ShooterGameServer responda a RCON o complete la carga."""
        start_time = time.time()
        last_heartbeat = start_time
        await self.broadcast_log("[ARK Server Manager] [INFO] Monitor de disponibilidad activo. Verificando inicio de ShooterGameServer...")

        while self.status == "STARTING" and self._is_ark_process_running():
            await asyncio.sleep(3.0)
            if self.status != "STARTING":
                return

            now = time.time()
            elapsed_sec = int(now - start_time)

            # Comprobación de disponibilidad (async await)
            is_ready = await self.is_server_ready()

            if is_ready:
                self.status = "RUNNING"
                await self.broadcast_log("========================================================================")
                await self.broadcast_log("[ARK Server Manager] [OK] ¡SERVIDOR DE ARK 100% ONLINE Y DISPONIBLE!")
                await self.broadcast_log(f"[ARK Server Manager] Nombre de Sesión: {settings.session_name}")
                await self.broadcast_log(f"[ARK Server Manager] Mapa: {settings.world} | Puerto de Juego: {settings.server_port} (UDP)")
                await self.broadcast_log(f"[ARK Server Manager] RCON: {settings.rcon_port} (Activo) | Supervivientes: 0/{settings.max_players}")
                await self.broadcast_log(f"[ARK Server Manager] Tiempo total de carga: {elapsed_sec // 60}m {elapsed_sec % 60}s.")
                await self.broadcast_log("========================================================================")
                from app.core.webhook_manager import webhook_manager
                await webhook_manager.send_discord_embed("START")
                return

            # Mensaje periódico de progreso en la consola cada 45 segundos para dar tranquilidad
            if now - last_heartbeat >= 45:
                last_heartbeat = now
                mins = elapsed_sec // 60
                secs = elapsed_sec % 60
                await self.broadcast_log(f"[ARK Server Manager] [EN PROCESO] Servidor iniciando... Cargando mundo y mods en RAM ({mins}m {secs}s transcurridos). Por favor espera...")

        # Si el bucle terminó y el proceso sigue vivo
        if self._is_ark_process_running() and self.status == "STARTING":
            self.status = "RUNNING"
            await self.broadcast_log("[ARK Server Manager] [OK] Servidor de ARK operativo en segundo plano.")

    async def stop_server(self, grace_seconds: int = 10) -> bool:
        if self.status == "OFFLINE" and not self._is_ark_process_running():
            await self.broadcast_log("[ARK Server Manager] El servidor ya está apagado.")
            return False

        self.status = "STOPPING"
        self._intentional_stop = True
        await self.broadcast_log(f"[ARK Server Manager] Guardando mundo antes de apagar...")

        try:
            if self.rcon:
                await self.rcon.broadcast("El servidor se apagara en 10 segundos. Guardando mundo...")
                await self.rcon.save_world()
                await asyncio.sleep(2)
        except Exception:
            pass

        if shutil.which("arkmanager"):
            try:
                proc = await asyncio.create_subprocess_exec("arkmanager", "stop", "--saveworld", "@main")
                await proc.wait()
                self.status = "OFFLINE"
                await self.broadcast_log("[ARK Server Manager] Servidor detenido exitosamente mediante arkmanager.")
                return True
            except Exception:
                pass

        if self.process and self.process.returncode is None:
            try:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=grace_seconds)
                except asyncio.TimeoutError:
                    self.process.kill()
            except Exception as e:
                await self.broadcast_log(f"[ARK Server Manager] Error finalizando proceso: {e}")

        try:
            for p in psutil.process_iter(['name', 'cmdline']):
                name = p.info.get('name') or ''
                if 'ShooterGameServer' in name:
                    p.terminate()
        except Exception:
            pass

        self.status = "OFFLINE"
        self.started_at = None
        await self.rcon.disconnect()
        await self.broadcast_log("[ARK Server Manager] Servidor de ARK detenido.")
        return True

    async def restart_server(self) -> bool:
        await self.stop_server()
        await asyncio.sleep(3)
        return await self.start_server()

    async def send_command(self, command: str) -> str:
        if not command.strip():
            return ""
        await self.broadcast_log(f"> {command}")
        resp = await self.rcon.send_command(command)
        if resp:
            for line in resp.splitlines():
                await self.broadcast_log(line)
        return resp

process_manager = ProcessManager()
