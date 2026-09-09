from collections import deque
import os
import re
import json
import time
import shutil
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.config import settings
from app.core.rcon_client import ArkRconClient
from app.core.process_manager import process_manager

logger = logging.getLogger("arkserver.cluster")

OFFICIAL_MAPS = [
    {"id": "TheIsland", "name": "The Island", "server_port": 7777, "query_port": 27015, "rcon_port": 27020, "alt_save_dir": "TheIsland"},
    {"id": "ScorchedEarth_P", "name": "Scorched Earth", "server_port": 7779, "query_port": 27016, "rcon_port": 27021, "alt_save_dir": "ScorchedEarth"},
    {"id": "Aberration_P", "name": "Aberration", "server_port": 7781, "query_port": 27017, "rcon_port": 27022, "alt_save_dir": "Aberration"},
    {"id": "Extinction", "name": "Extinction", "server_port": 7783, "query_port": 27018, "rcon_port": 27023, "alt_save_dir": "Extinction"},
    {"id": "Ragnarok", "name": "Ragnarok", "server_port": 7785, "query_port": 27019, "rcon_port": 27024, "alt_save_dir": "Ragnarok"},
    {"id": "Valguero_P", "name": "Valguero", "server_port": 7787, "query_port": 27020, "rcon_port": 27025, "alt_save_dir": "Valguero"},
    {"id": "Genesis", "name": "Genesis: Parte 1", "server_port": 7789, "query_port": 27021, "rcon_port": 27026, "alt_save_dir": "Genesis1"},
    {"id": "Gen2", "name": "Genesis: Parte 2", "server_port": 7791, "query_port": 27022, "rcon_port": 27027, "alt_save_dir": "Genesis2"},
    {"id": "CrystalIsles", "name": "Crystal Isles", "server_port": 7793, "query_port": 27023, "rcon_port": 27028, "alt_save_dir": "CrystalIsles"},
    {"id": "LostIsland", "name": "Lost Island", "server_port": 7795, "query_port": 27024, "rcon_port": 27029, "alt_save_dir": "LostIsland"},
    {"id": "Fjordur", "name": "Fjordur", "server_port": 7797, "query_port": 27025, "rcon_port": 27030, "alt_save_dir": "Fjordur"},
    {"id": "TheCenter", "name": "The Center", "server_port": 7799, "query_port": 27026, "rcon_port": 27031, "alt_save_dir": "TheCenter"}
]


class ClusterManager:
    """
    Gestor centralizado del Clúster y de múltiples instancias de ARK.
    Permite administrar The Island, Scorched Earth, Aberration, etc.,
    desde la misma interfaz, vinculando el directorio de clúster compartido (/clusters)
    para permitir el viaje libre de supervivientes, dinosaurios e inventarios.
    """
    def __init__(self):
        self._config_file = settings.ark_data_dir / "ark_cluster_instances.json"
        self._instances: Dict[str, Dict[str, Any]] = {}
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._rcon_clients: Dict[str, ArkRconClient] = {}
        self._log_buffers: Dict[str, Any] = {}
        self.connected_websockets: Dict[str, set] = {}
        self._load_instances()

    def _load_instances(self):
        """Carga el registro de instancias o crea la instancia principal por defecto."""
        if self._config_file.exists():
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    self._instances = json.load(f)
            except Exception as e:
                logger.error(f"Error cargando ark_cluster_instances.json: {e}")
                self._instances = {}

        # Asegurar instancia principal "main"
        # Normalizar nombre de la instancia principal si tiene formato previo
        if "main" in self._instances:
            curr_name = self._instances["main"].get("name", "")
            if curr_name.startswith("Servidor"):
                map_val = self._instances["main"].get("map", settings.world)
                map_title = "The Island" if map_val.lower() == "theisland" else map_val
                self._instances["main"]["name"] = f"Principal ({map_title})"
                self._save_instances()

        if "main" not in self._instances:
            self._instances["main"] = {
                "id": "main",
                "name": f"Principal ({'The Island' if settings.world.lower() == 'theisland' else settings.world})",
                "map": settings.world,
                "session_name": settings.session_name,
                "server_port": settings.server_port,
                "query_port": settings.query_port,
                "rcon_port": settings.rcon_port,
                "rcon_password": settings.admin_ark_password,
                "server_password": settings.server_password,
                "max_players": settings.max_players,
                "alt_save_dir": settings.world,
                "is_primary": True,
                "enabled": True,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self._save_instances()

        # Configurar clientes RCON y buffers
        for inst_id, inst in self._instances.items():
            if inst_id == "main":
                self._rcon_clients["main"] = process_manager.rcon
            else:
                self._rcon_clients[inst_id] = ArkRconClient(
                    host=settings.rcon_host,
                    port=int(inst.get("rcon_port", 27020)),
                    password=inst.get("rcon_password", settings.admin_ark_password)
                )
            if inst_id not in self._log_buffers:
                self._log_buffers[inst_id] = []

    def _save_instances(self):
        try:
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._instances, f, indent=2)
        except Exception as e:
            logger.error(f"Error guardando ark_cluster_instances.json: {e}")

    def get_official_maps(self) -> List[Dict[str, str]]:
        return OFFICIAL_MAPS

    def suggest_next_ports(self) -> Dict[str, int]:
        """Calcula los siguientes puertos libres para una nueva instancia."""
        used_server = {inst.get("server_port", 7777) for inst in self._instances.values()}
        used_query = {inst.get("query_port", 27015) for inst in self._instances.values()}
        used_rcon = {inst.get("rcon_port", 27020) for inst in self._instances.values()}

        next_server = 7777
        while next_server in used_server:
            next_server += 2  # ARK usa puertos pares para Game + RawUDP (ej: 7777 y 7778)

        next_query = 27015
        while next_query in used_query:
            next_query += 1

        next_rcon = 27020
        while next_rcon in used_rcon:
            next_rcon += 1

        return {
            "server_port": next_server,
            "query_port": next_query,
            "rcon_port": next_rcon
        }

    def list_instances(self) -> List[Dict[str, Any]]:
        """Devuelve la lista de instancias con su estado en vivo."""
        res = []
        for inst_id, inst in self._instances.items():
            item = dict(inst)
            item["status"] = self.get_instance_status(inst_id)
            item["cluster_id"] = settings.cluster_id
            res.append(item)
        return res

    def get_instance(self, instance_id: str) -> Optional[Dict[str, Any]]:
        inst = self._instances.get(instance_id)
        if not inst:
            return None
        res = dict(inst)
        res["status"] = self.get_instance_status(instance_id)
        res["cluster_id"] = settings.cluster_id
        return res

    def get_instance_status(self, instance_id: str) -> str:
        if instance_id == "main":
            return process_manager.get_status()
        proc = self._processes.get(instance_id)
        if proc and proc.returncode is None:
            return "RUNNING"
        inst = self._instances.get(instance_id)
        if inst:
            inst_port = inst.get("server_port")
            if inst_port:
                try:
                    import psutil
                    port_str = f"Port={inst_port}"
                    for p in psutil.process_iter(['name', 'cmdline']):
                        cmdline = ' '.join(p.info.get('cmdline') or [])
                        name = p.info.get('name') or ''
                        if ('ShooterGameServer' in name or 'ShooterGameServer' in cmdline) and port_str in cmdline:
                            return "RUNNING"
                except Exception:
                    pass
        return "OFFLINE"

    def get_instance_pid(self, instance_id: str) -> Optional[int]:
        if instance_id == "main":
            return process_manager.get_server_pid()
        proc = self._processes.get(instance_id)
        if proc and proc.returncode is None:
            return proc.pid
        inst = self._instances.get(instance_id)
        if inst:
            inst_port = inst.get("server_port")
            if inst_port:
                try:
                    import psutil
                    port_str = f"Port={inst_port}"
                    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                        cmdline = ' '.join(p.info.get('cmdline') or [])
                        name = p.info.get('name') or ''
                        if ('ShooterGameServer' in name or 'ShooterGameServer' in cmdline) and port_str in cmdline:
                            return p.info['pid']
                except Exception:
                    pass
        return None

    def get_rcon_client(self, instance_id: str) -> ArkRconClient:
        if instance_id == "main" or instance_id not in self._rcon_clients:
            return process_manager.rcon
        return self._rcon_clients[instance_id]

    def get_log_buffer(self, instance_id: str) -> List[str]:
        if instance_id == "main":
            return list(process_manager.log_buffer)
        buf = self._log_buffers.get(instance_id)
        if buf is None:
            buf = deque(maxlen=500)
            self._log_buffers[instance_id] = buf
        return list(buf)

    async def broadcast_log(self, instance_id: str, message: str):
        if instance_id not in self._log_buffers or not isinstance(self._log_buffers[instance_id], deque):
            self._log_buffers[instance_id] = deque(maxlen=500)
        self._log_buffers[instance_id].append(message)
        ws_set = self.connected_websockets.get(instance_id, set())
        dead = []
        for ws in list(ws_set):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            ws_set.discard(ws)

    async def send_command(self, instance_id: str, command: str) -> str:
        if instance_id == "main":
            return await process_manager.send_command(command)
        rcon = self.get_rcon_client(instance_id)
        await self.broadcast_log(instance_id, f"> {command}")
        resp = await rcon.send_command(command)
        if resp:
            await self.broadcast_log(instance_id, resp)
        return resp

    async def _stream_instance_logs(self, instance_id: str, proc):
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            text = line.decode('utf-8', errors='replace').rstrip()
            await self.broadcast_log(instance_id, text)

    def _write_arkmanager_instance_cfg(self, instance_id: str) -> None:
        """Genera el archivo de configuración de instancia para arkmanager (/etc/arkmanager/instances/<id>.cfg)."""
        if instance_id == "main":
            return

        inst = self._instances.get(instance_id)
        if not inst:
            return

        map_name = inst.get("map", "ScorchedEarth_P")
        server_port = inst.get("server_port", 7779)
        query_port = inst.get("query_port", 27016)
        rcon_port = inst.get("rcon_port", 27021)
        rcon_pass = inst.get("rcon_password", settings.admin_ark_password)
        server_pass = inst.get("server_password", "")
        alt_save = inst.get("alt_save_dir", map_name)
        session_name = inst.get("session_name", f"{settings.session_name} - {inst.get('name')}")
        max_players = inst.get("max_players", settings.max_players)
        cluster_id = settings.cluster_id
        cluster_dir = str(settings.cluster_dir)

        cfg_content = (
            f"# Configuración de Instancia Clúster: {inst.get('name', instance_id)}\n"
            f"serverMap=\"{map_name}\"\n"
            f"ark_SessionName=\"{session_name}\"\n"
            f"ark_ServerPassword=\"{server_pass}\"\n"
            f"ark_ServerAdminPassword=\"{rcon_pass}\"\n"
            f"rconpassword=\"{rcon_pass}\"\n"
            f"ark_RCONEnabled=\"True\"\n"
            f"ark_RCONPort=\"{rcon_port}\"\n"
            f"rconport=\"{rcon_port}\"\n"
            f"ark_Port=\"{server_port}\"\n"
            f"ark_QueryPort=\"{query_port}\"\n"
            f"ark_MaxPlayers=\"{max_players}\"\n"
            f"ark_AltSaveDirectoryName=\"{alt_save}\"\n"
            f"arkopt_clusterid=\"{cluster_id}\"\n"
            f"arkopt_ClusterDirOverride=\"{cluster_dir}\"\n"
            f"arkNoPortDecrement=\"true\"\n"
        )

        instances_dir = Path("/etc/arkmanager/instances")
        try:
            if instances_dir.exists() or os.access("/etc/arkmanager", os.W_OK):
                instances_dir.mkdir(parents=True, exist_ok=True)
                cfg_path = instances_dir / f"{instance_id}.cfg"
                with open(cfg_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(cfg_content)
        except Exception as e:
            logger.debug(f"No se pudo escribir /etc/arkmanager/instances/{instance_id}.cfg: {e}")

    def create_instance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crea un nuevo servidor / mapa dentro del clúster."""
        raw_name = data.get("name", "").strip() or "Nuevo Mapa"
        map_id = data.get("map", "ScorchedEarth_P").strip()

        # Generar ID único amigable
        slug = re.sub(r'[^a-zA-Z0-9]', '', raw_name.lower()) or "map"
        inst_id = slug
        count = 1
        while inst_id in self._instances:
            count += 1
            inst_id = f"{slug}_{count}"

        # Asignar o validar puertos
        ports = self.suggest_next_ports()
        server_port = int(data.get("server_port") or ports["server_port"])
        query_port = int(data.get("query_port") or ports["query_port"])
        rcon_port = int(data.get("rcon_port") or ports["rcon_port"])

        # Validar colisión de puertos
        for existing_id, existing in self._instances.items():
            if existing.get("server_port") == server_port:
                return {"success": False, "error": f"El puerto de juego {server_port} ya está en uso por {existing.get('name')}"}
            if existing.get("query_port") == query_port:
                return {"success": False, "error": f"El puerto query {query_port} ya está en uso por {existing.get('name')}"}
            if existing.get("rcon_port") == rcon_port:
                return {"success": False, "error": f"El puerto RCON {rcon_port} ya está en uso por {existing.get('name')}"}

        alt_save_dir = data.get("alt_save_dir", "").strip() or map_id

        instance_info = {
            "id": inst_id,
            "name": raw_name,
            "map": map_id,
            "session_name": data.get("session_name", f"{settings.session_name} - {raw_name}"),
            "server_port": server_port,
            "query_port": query_port,
            "rcon_port": rcon_port,
            "rcon_password": data.get("rcon_password", settings.admin_ark_password),
            "server_password": data.get("server_password", settings.server_password),
            "max_players": int(data.get("max_players") or settings.max_players),
            "alt_save_dir": alt_save_dir,
            "is_primary": False,
            "enabled": True,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        self._instances[inst_id] = instance_info
        self._save_instances()

        # Inicializar cliente RCON
        self._rcon_clients[inst_id] = ArkRconClient(
            host=settings.rcon_host,
            port=rcon_port,
            password=instance_info["rcon_password"]
        )
        self._log_buffers[inst_id] = [f"[ARK Server Manager] Instancia {raw_name} agregada al clúster."]

        self._write_arkmanager_instance_cfg(inst_id)
        logger.info(f"Instancia de clúster creada: {inst_id} ({map_id})")
        return {"success": True, "instance": instance_info}

    def update_instance(self, instance_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Actualiza parámetros de una instancia existente."""
        if instance_id not in self._instances:
            return {"success": False, "error": "Instancia no encontrada"}

        inst = self._instances[instance_id]
        if "name" in data:
            inst["name"] = data["name"].strip()
        if "session_name" in data:
            inst["session_name"] = data["session_name"].strip()
        if "server_password" in data:
            inst["server_password"] = data["server_password"].strip()
        if "rcon_password" in data:
            inst["rcon_password"] = data["rcon_password"].strip()
        if "max_players" in data:
            inst["max_players"] = int(data["max_players"])
        if "enabled" in data:
            inst["enabled"] = bool(data["enabled"])

        # No permitir cambiar puertos si la instancia está corriendo
        if self.get_instance_status(instance_id) == "RUNNING":
            if any(k in data for k in ("server_port", "query_port", "rcon_port")):
                return {"success": False, "error": "Detén la instancia antes de cambiar sus puertos"}
        else:
            if "server_port" in data:
                inst["server_port"] = int(data["server_port"])
            if "query_port" in data:
                inst["query_port"] = int(data["query_port"])
            if "rcon_port" in data:
                inst["rcon_port"] = int(data["rcon_port"])

        self._save_instances()
        self._write_arkmanager_instance_cfg(instance_id)
        return {"success": True, "instance": inst}

    def delete_instance(self, instance_id: str) -> Dict[str, Any]:
        """Elimina una instancia secundaria del clúster."""
        if instance_id == "main":
            return {"success": False, "error": "No se puede eliminar la instancia principal"}
        if instance_id not in self._instances:
            return {"success": False, "error": "Instancia no encontrada"}

        if self.get_instance_status(instance_id) == "RUNNING":
            return {"success": False, "error": "Detén la instancia antes de eliminarla"}

        del self._instances[instance_id]
        self._processes.pop(instance_id, None)
        self._rcon_clients.pop(instance_id, None)
        self._log_buffers.pop(instance_id, None)
        self._save_instances()

        cfg_path = Path(f"/etc/arkmanager/instances/{instance_id}.cfg")
        if cfg_path.exists():
            try:
                cfg_path.unlink()
            except Exception:
                pass

        return {"success": True}

    async def start_instance(self, instance_id: str) -> bool:
        """Inicia una instancia específica del clúster."""
        if instance_id == "main":
            return await process_manager.start_server()

        inst = self._instances.get(instance_id)
        if not inst:
            return False

        if self.get_instance_status(instance_id) == "RUNNING":
            return True

        map_name = inst.get("map", "ScorchedEarth_P")
        server_port = inst.get("server_port", 7779)
        query_port = inst.get("query_port", 27016)
        rcon_port = inst.get("rcon_port", 27021)
        rcon_pass = inst.get("rcon_password", settings.admin_ark_password)
        alt_save = inst.get("alt_save_dir", map_name)
        session_name = inst.get("session_name", f"ARK Server - {inst.get('name')}")
        cluster_id = settings.cluster_id
        cluster_dir = str(settings.cluster_dir)

        # Asegurar archivo de configuración de instancia para arkmanager
        self._write_arkmanager_instance_cfg(instance_id)

        # Asegurar que el directorio de clúster para obeliscos exista
        cluster_target = settings.cluster_dir / settings.cluster_id
        try:
            cluster_target.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        ark_server_bin = settings.ark_data_dir / "ShooterGame" / "Binaries" / "Linux" / "ShooterGameServer"
        server_pass = inst.get("server_password", "")

        cmd = []
        if shutil.which("arkmanager"):
            cmd = ["arkmanager", "run", f"@{instance_id}"]
        elif ark_server_bin.exists():
            server_args = (
                f"{map_name}?listen?SessionName={session_name}?Port={server_port}"
                f"?QueryPort={query_port}?RCONPort={rcon_port}?RCONEnabled=True"
                f"?ServerAdminPassword={rcon_pass}?MaxPlayers={inst.get('max_players', settings.max_players)}"
                f"?AltSaveDirectoryName={alt_save}"
            )
            if server_pass:
                server_args += f"?ServerPassword={server_pass}"
            cmd = [
                str(ark_server_bin),
                server_args,
                f"-clusterid={cluster_id}",
                f"-ClusterDirOverride={cluster_dir}",
                "-server",
                "-log",
                "-USEALLAVAILABLECORES",
                "-nostallstartup"
            ]
        else:
            sim_code = (
                f"import time; print('[ARK Server Manager] Nodo Clúster {inst.get('name')} ({map_name}) iniciado en puerto {server_port}'); "
                f"[time.sleep(2) for _ in range(300)]"
            )
            cmd = [settings.base_dir / ".venv" / "Scripts" / "python.exe" if (settings.base_dir / ".venv" / "Scripts" / "python.exe").exists() else "python", "-c", sim_code]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=os.environ.copy()
            )
            self._processes[instance_id] = proc
            asyncio.create_task(self._stream_instance_logs(instance_id, proc))
            await self.broadcast_log(instance_id, f"[ARK Server Manager] Nodo {inst.get('name')} iniciado (PID: {proc.pid})...")
            return True
        except Exception as e:
            logger.error(f"Error arrancando instancia {instance_id}: {e}")
            return False

    async def stop_instance(self, instance_id: str) -> bool:
        """Detiene una instancia específica del clúster con guardado de mundo previo."""
        if instance_id == "main":
            return await process_manager.stop_server()

        rcon = self.get_rcon_client(instance_id)
        try:
            await rcon.save_world()
        except Exception:
            pass

        if shutil.which("arkmanager"):
            try:
                stop_proc = await asyncio.create_subprocess_exec("arkmanager", "stop", "--saveworld", f"@{instance_id}")
                await asyncio.wait_for(stop_proc.wait(), timeout=15)
            except Exception:
                pass

        proc = self._processes.get(instance_id)
        if proc and proc.returncode is None:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=15)
            except asyncio.TimeoutError:
                proc.kill()
            self._processes.pop(instance_id, None)

        try:
            await rcon.disconnect()
        except Exception:
            pass

        return True

    async def restart_instance(self, instance_id: str) -> bool:
        await self.stop_instance(instance_id)
        await asyncio.sleep(2)
        return await self.start_instance(instance_id)

    async def start_all(self) -> Dict[str, Any]:
        """Arranca todos los nodos del clúster de forma escalonada."""
        results = {}
        for inst_id, inst in self._instances.items():
            if inst.get("enabled", True):
                ok = await self.start_instance(inst_id)
                results[inst_id] = ok
                await asyncio.sleep(3)
        return {"success": True, "results": results}

    async def stop_all(self) -> Dict[str, Any]:
        """Detiene todos los nodos del clúster de forma segura."""
        results = {}
        for inst_id in self._instances:
            ok = await self.stop_instance(inst_id)
            results[inst_id] = ok
        return {"success": True, "results": results}

    def list_cluster_tributes(self) -> List[Dict[str, Any]]:
        """
        Explora la carpeta compartida del clúster (/home/steam/clusters/<ClusterID> o /clusters).
        Detecta supervivientes, dinosaurios e inventarios subidos a los obeliscos.
        """
        cluster_root = settings.cluster_dir
        target_dir = cluster_root / settings.cluster_id if (cluster_root / settings.cluster_id).exists() else cluster_root

        tributes = []
        if not target_dir.exists():
            return tributes

        try:
            for item in target_dir.iterdir():
                if item.is_file():
                    fname = item.name
                    size_kb = round(item.stat().st_size / 1024, 2)
                    mtime = datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                    steam_id = ""
                    data_type = "Tributo / Objeto"
                    if fname.endswith(".arkprofile"):
                        data_type = "Superviviente (Perfil)"
                        steam_id = fname.replace(".arkprofile", "")
                    elif ".arkpdino" in fname:
                        data_type = "Criatura (Dino)"
                        parts = fname.split("_")
                        if len(parts) > 1 and parts[0].isdigit():
                            steam_id = parts[0]
                    elif fname.isdigit() and len(fname) == 17:
                        data_type = "Inventario de Obelisco"
                        steam_id = fname

                    tributes.append({
                        "filename": fname,
                        "steam_id": steam_id,
                        "data_type": data_type,
                        "size_kb": size_kb,
                        "updated_at": mtime
                    })
        except Exception as e:
            logger.error(f"Error listando tributos de clúster: {e}")

        return sorted(tributes, key=lambda x: x["updated_at"], reverse=True)

    def delete_cluster_tribute(self, filename: str) -> bool:
        """Elimina un archivo corrupto o atascado de la nube de transferencia del clúster."""
        cluster_root = settings.cluster_dir
        target_dir = cluster_root / settings.cluster_id if (cluster_root / settings.cluster_id).exists() else cluster_root
        target_file = target_dir / filename

        try:
            resolved = target_file.resolve()
            if cluster_root.resolve() not in resolved.parents:
                return False
            if resolved.exists() and resolved.is_file():
                resolved.unlink()
                return True
        except Exception:
            pass
        return False

    def sync_rates_to_all(self, rates: Dict[str, Any]) -> Dict[str, Any]:
        """Sincroniza multiplicadores a todos los archivos .ini de las instancias del clúster."""
        from app.core.ark_settings_manager import ark_settings_manager
        ok_main = ark_settings_manager.save_settings({"multipliers": rates})

        saved_root = settings.ark_data_dir / "ShooterGame" / "Saved"
        count = 1 if ok_main else 0
        for inst_id, inst in self._instances.items():
            if inst_id == "main":
                continue
            alt_save = inst.get("alt_save_dir", inst.get("map"))
            alt_config_dir = saved_root / alt_save / "Config" / "LinuxServer"
            alt_config_dir.mkdir(parents=True, exist_ok=True)
            if alt_config_dir.exists():
                gus = alt_config_dir / "GameUserSettings.ini"
                game = alt_config_dir / "Game.ini"
                if gus.exists():
                    gus_updates = {}
                    if "xp" in rates: gus_updates["XPMultiplier"] = str(rates["xp"])
                    if "taming" in rates: gus_updates["TamingSpeedMultiplier"] = str(rates["taming"])
                    if "harvest" in rates: gus_updates["HarvestAmountMultiplier"] = str(rates["harvest"])
                    ark_settings_manager.update_ini_section(gus, "ServerSettings", gus_updates)
                if game.exists():
                    game_updates = {}
                    if "mating" in rates: game_updates["MatingIntervalMultiplier"] = str(rates["mating"])
                    if "hatch" in rates: game_updates["EggHatchSpeedMultiplier"] = str(rates["hatch"])
                    if "mature" in rates: game_updates["BabyMatureSpeedMultiplier"] = str(rates["mature"])
                    ark_settings_manager.update_ini_section(game, "/script/shootergame.shootergamemode", game_updates)
                count += 1

        return {"success": True, "synced_nodes": count}


cluster_manager = ClusterManager()
