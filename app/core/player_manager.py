import os
import json
import time
import socket
import struct
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.config import settings
from app.core.process_manager import process_manager
from app.core.fs_utils import atomic_write_json
from app.core.webhook_manager import webhook_manager

logger = logging.getLogger("arkserver.players")

class PlayerManager:
    """
    Gestor de supervivientes para ARK: Survival Evolved.
    Obtiene los jugadores en línea mediante RCON (listplayers) y Steam A2S Query.
    Guarda historial persistente de conexiones, SteamIDs y tiempos de juego.
    """
    def __init__(self):
        self._history_file = settings.ark_data_dir / "ark_players.json"
        self._player_history: Dict[str, Dict[str, Any]] = {}
        self._current_online: Dict[str, str] = {}
        self._monitor_running: bool = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._load_history()

    def start_monitor(self):
        if not self._monitor_running:
            self._monitor_running = True
            self._monitor_task = asyncio.create_task(self._monitor_loop())

    def stop_monitor(self):
        self._monitor_running = False
        if self._monitor_task:
            self._monitor_task.cancel()

    async def _monitor_loop(self):
        while self._monitor_running:
            try:
                if process_manager.get_status() == "RUNNING":
                    current_players = await self.get_online_players()
                    new_online = {p["steam_id"]: p["name"] for p in current_players}

                    # Detectar nuevos supervivientes conectados
                    for steam_id, name in new_online.items():
                        if steam_id not in self._current_online:
                            msg = f"[ARK] 👤 Superviviente conectado: {name} (SteamID: {steam_id})"
                            await process_manager.broadcast_log(msg)
                            await webhook_manager.send_discord_embed(
                                "PLAYER_JOIN",
                                f"El superviviente **{name}** (`{steam_id}`) se ha unido a la partida."
                            )

                    # Detectar supervivientes desconectados
                    for steam_id, name in self._current_online.items():
                        if steam_id not in new_online:
                            msg = f"[ARK] 👋 Superviviente desconectado: {name} (SteamID: {steam_id})"
                            await process_manager.broadcast_log(msg)
                            await webhook_manager.send_discord_embed(
                                "PLAYER_LEAVE",
                                f"El superviviente **{name}** (`{steam_id}`) ha salido de la partida."
                            )

                    self._current_online = new_online
                else:
                    if self._current_online:
                        self._current_online.clear()
            except Exception as e:
                logger.debug(f"Error en monitor de supervivientes: {e}")

            await asyncio.sleep(10)

    def _load_history(self) -> None:
        if self._history_file.exists():
            try:
                with open(self._history_file, "r", encoding="utf-8") as f:
                    self._player_history = json.load(f)
            except Exception as e:
                logger.debug(f"Error cargando historial de jugadores: {e}")
                self._player_history = {}

    def _save_history(self) -> None:
        try:
            atomic_write_json(self._history_file, self._player_history, indent=2)
        except Exception as e:
            logger.debug(f"Error guardando historial de jugadores: {e}")

    async def get_online_players(self) -> List[Dict[str, Any]]:
        """Devuelve la lista de jugadores conectados actualmente."""
        if process_manager.get_status() != "RUNNING":
            return []

        # Intentar obtener vía RCON (fuente de verdad autoritativa en vivo)
        players = []
        try:
            rcon_players = await process_manager.rcon.list_players()
            now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
            now_ts = time.time()
            history_updated = False
            for p in rcon_players:
                name = p.get("name", "").strip()
                steam_id = p.get("steam_id", "").strip()
                if not name and not steam_id:
                    continue

                # Actualizar historial persistente
                if steam_id and steam_id != "Desconocido":
                    if steam_id not in self._player_history:
                        self._player_history[steam_id] = {
                            "name": name or "Superviviente",
                            "steam_id": steam_id,
                            "first_seen": now_str,
                            "last_seen": now_str,
                            "last_ts": now_ts,
                            "banned": False
                        }
                        history_updated = True
                    else:
                        self._player_history[steam_id]["name"] = name or self._player_history[steam_id].get("name", "Superviviente")
                        self._player_history[steam_id]["last_seen"] = now_str
                        self._player_history[steam_id]["last_ts"] = now_ts
                        history_updated = True

                players.append({
                    "name": name or "Superviviente",
                    "steam_id": steam_id or "Desconocido",
                    "status": "online",
                    "last_seen": now_str
                })

            if history_updated:
                self._save_history()
            # Si RCON respondió con éxito (incluso si está vacío con 0 jugadores), es la verdad autoritativa
            return players
        except Exception as e:
            logger.debug(f"RCON listplayers no disponible, intentando fallback A2S: {e}")

        # Fallback opcional: Steam A2S Query ÚNICAMENTE si RCON arrojó excepción o no responde
        try:
            a2s_players = await self._query_a2s_players()
            if a2s_players:
                return a2s_players
        except Exception as e:
            logger.debug(f"A2S query error: {e}")

        return []

    async def _query_a2s_players(self) -> List[Dict[str, Any]]:
        """Consulta UDP al puerto Steam Query (27015) para A2S_PLAYER."""
        loop = asyncio.get_running_loop()
        def _sync_a2s():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(1.5)
                # Packet A2S_PLAYER request challenge
                req = b"\xFF\xFF\xFF\xFF\x55\xFF\xFF\xFF\xFF"
                sock.sendto(req, (settings.rcon_host, settings.query_port))
                data, _ = sock.recvfrom(1400)
                if len(data) >= 9 and data[4] == 0x41:
                    # Received challenge token
                    challenge = data[5:9]
                    req2 = b"\xFF\xFF\xFF\xFF\x55" + challenge
                    sock.sendto(req2, (settings.rcon_host, settings.query_port))
                    data2, _ = sock.recvfrom(4096)
                    if len(data2) >= 6 and data2[4] == 0x44:
                        num_players = data2[5]
                        offset = 6
                        results = []
                        for _ in range(num_players):
                            if offset >= len(data2):
                                break
                            # index byte
                            offset += 1
                            # string name null terminated
                            name_end = data2.find(b"\x00", offset)
                            if name_end == -1:
                                break
                            p_name = data2[offset:name_end].decode("utf-8", errors="replace").strip()
                            offset = name_end + 1 + 4 + 4  # skip name, score (int32), duration (float)
                            if p_name and p_name != "0":
                                results.append({
                                    "name": p_name,
                                    "steam_id": "N/A",
                                    "status": "online",
                                    "last_seen": datetime.now().strftime("%d/%m/%Y %H:%M")
                                })
                        return results
            except Exception:
                pass
            finally:
                try:
                    sock.close()
                except Exception:
                    pass
            return []

        try:
            return await loop.run_in_executor(None, _sync_a2s)
        except Exception:
            return []

    def get_all_history(self) -> List[Dict[str, Any]]:
        """Devuelve el historial completo de todos los jugadores que han ingresado."""
        return list(self._player_history.values())

    async def kick(self, steam_id: str) -> str:
        """Expulsa a un superviviente mediante RCON."""
        return await process_manager.rcon.kick_player(steam_id)

    async def ban(self, steam_id: str) -> str:
        """Banea a un superviviente mediante RCON y lo marca en el historial."""
        if steam_id in self._player_history:
            self._player_history[steam_id]["banned"] = True
            self._save_history()
        return await process_manager.rcon.ban_player(steam_id)

    async def message_player(self, steam_id: str, message: str) -> str:
        """Envía un mensaje privado in-game al superviviente vía RCON."""
        safe_msg = message.replace('"', '\"')
        return await process_manager.rcon.send_command(f'ServerChatToPlayer "{steam_id}" {safe_msg}')

    async def unban(self, steam_id: str) -> str:
        """Desbanea a un superviviente."""
        if steam_id in self._player_history:
            self._player_history[steam_id]["banned"] = False
            self._save_history()
        return await process_manager.rcon.unban_player(steam_id)

player_manager = PlayerManager()
