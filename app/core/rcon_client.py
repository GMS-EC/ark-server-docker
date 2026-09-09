import re
import asyncio
import struct
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger("arkserver.rcon")

# RCON Packet Types (Source RCON Protocol)
SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_RESPONSE_VALUE = 0

class ArkRconClient:
    """
    Cliente RCON asíncrono nativo para ARK: Survival Evolved.
    Implementa el protocolo Source RCON a través de asyncio sin dependencias externas.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 27020, password: str = "adminpass"):
        self.host = host
        self.port = port
        self.password = password
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._lock = asyncio.Lock()
        self._authenticated = False
        self._req_id = 1

    def is_connected(self) -> bool:
        return self.writer is not None and not self.writer.is_closing() and self._authenticated

    async def connect(self, timeout: float = 3.0) -> bool:
        """Establece conexión TCP y se autentica con el servidor ARK."""
        async with self._lock:
            if self.is_connected():
                return True
            try:
                self.reader, self.writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=timeout
                )
                auth_ok = await self._authenticate(timeout=timeout)
                if not auth_ok:
                    await self._close_internal()
                    return False
                self._authenticated = True
                logger.info(f"Conexión RCON exitosa a {self.host}:{self.port}")
                return True
            except Exception as e:
                logger.debug(f"No se pudo conectar a RCON ({self.host}:{self.port}): {e}")
                await self._close_internal()
                return False

    async def _close_internal(self):
        self._authenticated = False
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
        self.reader = None
        self.writer = None

    async def disconnect(self):
        """Cierra la conexión RCON de manera segura."""
        async with self._lock:
            await self._close_internal()

    def _build_packet(self, req_id: int, packet_type: int, body: str) -> bytes:
        body_encoded = body.encode("utf-8", errors="replace") + b"\x00\x00"
        packet_size = 4 + 4 + len(body_encoded)
        return struct.pack("<iii", packet_size, req_id, packet_type) + body_encoded

    async def _read_packet(self, timeout: float = 4.0) -> Optional[tuple[int, int, str]]:
        if not self.reader:
            return None
        try:
            raw_size = await asyncio.wait_for(self.reader.readexactly(4), timeout=timeout)
            size = struct.unpack("<i", raw_size)[0]
            if size < 10 or size > 65535:
                return None
            data = await asyncio.wait_for(self.reader.readexactly(size), timeout=timeout)
            req_id, packet_type = struct.unpack("<ii", data[:8])
            # Descartar los 2 bytes nulos del final
            body_bytes = data[8:-2]
            body = body_bytes.decode("utf-8", errors="replace")
            return (req_id, packet_type, body)
        except Exception:
            return None

    async def _authenticate(self, timeout: float = 3.0) -> bool:
        self._req_id += 1
        auth_req_id = self._req_id
        packet = self._build_packet(auth_req_id, SERVERDATA_AUTH, self.password)
        self.writer.write(packet)
        await self.writer.drain()

        # El servidor ARK responde primero con un RESPONSE_VALUE vacío y luego con AUTH_RESPONSE
        for _ in range(3):
            resp = await self._read_packet(timeout=timeout)
            if not resp:
                return False
            resp_id, resp_type, _ = resp
            if resp_id == -1:
                logger.error("RCON: Contraseña de administración de ARK incorrecta.")
                return False
            if resp_type == SERVERDATA_AUTH_RESPONSE and resp_id == auth_req_id:
                return True
        return False

    async def send_command(self, command: str, timeout: float = 6.0) -> str:
        """Ejecuta un comando en la consola de ARK y devuelve la respuesta en texto."""
        cmd = command.strip()
        if not cmd:
            return ""

        async with self._lock:
            if not self.is_connected():
                # Intentar conectar automáticamente
                try:
                    self.reader, self.writer = await asyncio.wait_for(
                        asyncio.open_connection(self.host, self.port),
                        timeout=3.0
                    )
                    if not await self._authenticate(timeout=3.0):
                        await self._close_internal()
                        return "Error: Autenticación RCON fallida."
                    self._authenticated = True
                except Exception as e:
                    await self._close_internal()
                    return f"Error de conexión RCON: {e}"

            self._req_id += 1
            cur_req_id = self._req_id
            packet = self._build_packet(cur_req_id, SERVERDATA_EXECCOMMAND, cmd)
            
            try:
                self.writer.write(packet)
                await self.writer.drain()
                resp = await self._read_packet(timeout=timeout)
                if not resp:
                    return ""
                _, _, body = resp
                return body.strip()
            except Exception as e:
                logger.error(f"Fallo enviando comando RCON '{cmd}': {e}")
                await self._close_internal()
                return f"Error ejecutando comando: {e}"

    # Comandos rápidos de ARK
    async def save_world(self) -> str:
        """Guarda el estado del mundo de ARK inmediatamente."""
        return await self.send_command("SaveWorld")

    async def wipe_wild_dinos(self) -> str:
        """Destruye todos los dinosaurios salvajes no domesticados para refrescar spawns."""
        return await self.send_command("DestroyWildDinos")

    async def broadcast(self, message: str) -> str:
        """Envía un mensaje flotante a todos los jugadores conectados."""
        clean_msg = message.replace('"', '\\"')
        return await self.send_command(f'Broadcast "{clean_msg}"')

    async def list_players(self) -> List[Dict[str, str]]:
        """
        Ejecuta 'listplayers' y parsea la salida de supervivientes conectados.
        El formato devuelto por ARK suele ser:
        0. CharacterName, SteamID
        """
        output = await self.send_command("listplayers")
        if not output:
            return []

        # Si send_command retornó un mensaje de error o fallo de conexión, no es un jugador
        if output.startswith("Error") or "Error de conexión RCON" in output or "Error ejecutando comando" in output:
            raise ConnectionError(output)

        if "No Players Connected" in output:
            return []

        players = []
        lines = output.splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.lower().startswith("no players") or line.startswith("Error") or "Connection refused" in line:
                continue
            # Parsear formatos comunes: "0. PlayerName, 76561198xxxxxxxx"
            parts = line.split(",", 1)
            if len(parts) == 2:
                name_part = parts[0].strip()
                steam_part = parts[1].strip()
                # Quitar únicamente prefijo numérico como "0. " sin alterar nombres legítimos con punto (ej: "Dr. Strange")
                name_part = re.sub(r"^\d+\.\s*", "", name_part).strip()
                players.append({
                    "name": name_part,
                    "steam_id": steam_part
                })
            else:
                # Si solo viene un nombre
                players.append({
                    "name": line,
                    "steam_id": "Desconocido"
                })
        return players

    async def kick_player(self, steam_id: str) -> str:
        return await self.send_command(f"KickPlayer {steam_id}")

    async def ban_player(self, steam_id: str) -> str:
        return await self.send_command(f"BanPlayer {steam_id}")

    async def unban_player(self, steam_id: str) -> str:
        return await self.send_command(f"UnbanPlayer {steam_id}")
