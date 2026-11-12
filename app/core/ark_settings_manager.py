import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from app.config import settings
from app.core.cluster_manager import cluster_manager
from app.core.fs_utils import atomic_write_text

# Expresiones regulares precompiladas para parseo y actualización de archivos .ini
_SECTION_REGEX = re.compile(r"^\s*\[(.*)\]\s*$")
_KV_REGEX = re.compile(r"^\s*([^=;#]+?)\s*=\s*(.*?)\s*$")


class ArkSettingsManager:
    """
    Gestor de configuraciones para ARK: Survival Evolved.
    Lee y modifica de manera segura las directivas de GameUserSettings.ini y Game.ini,
    soportando tanto la instancia principal como instancias secundarias del Clúster.
    """
    def __init__(self):
        self.config_dir: Path = settings.ark_data_dir / "ShooterGame" / "Saved" / "Config" / "LinuxServer"
        self.gus_file: Path = self.config_dir / "GameUserSettings.ini"
        self.game_file: Path = self.config_dir / "Game.ini"

    def _ensure_paths(self, gus_path: Optional[Path] = None, game_path: Optional[Path] = None, inst_meta: Optional[Dict[str, Any]] = None):
        target_gus = gus_path or self.gus_file
        target_game = game_path or self.game_file
        target_gus.parent.mkdir(parents=True, exist_ok=True)
        target_game.parent.mkdir(parents=True, exist_ok=True)

        sess_name = (inst_meta or {}).get("session_name", settings.session_name)
        srv_pass = (inst_meta or {}).get("server_password", settings.server_password)
        adm_pass = (inst_meta or {}).get("rcon_password", settings.admin_ark_password)
        rcon_port = (inst_meta or {}).get("rcon_port", settings.rcon_port)
        srv_port = (inst_meta or {}).get("server_port", settings.server_port)
        qry_port = (inst_meta or {}).get("query_port", settings.query_port)
        max_pl = (inst_meta or {}).get("max_players", settings.max_players)

        if not target_gus.exists():
            if target_gus != self.gus_file and self.gus_file.exists():
                try:
                    shutil.copy2(self.gus_file, target_gus)
                except Exception:
                    pass
            if not target_gus.exists():
                default_gus = (
                    "[ServerSettings]\n"
                    f"SessionName={sess_name}\n"
                    f"ServerPassword={srv_pass}\n"
                    f"ServerAdminPassword={adm_pass}\n"
                    f"RCONEnabled={str(settings.rcon_enabled).capitalize()}\n"
                    f"RCONPort={rcon_port}\n"
                    f"Port={srv_port}\n"
                    f"QueryPort={qry_port}\n"
                    f"MaxPlayers={max_pl}\n"
                    "DifficultyOffset=1.0\n"
                    "XPMultiplier=1.0\n"
                    "TamingSpeedMultiplier=1.0\n"
                    "HarvestAmountMultiplier=1.0\n"
                    "ShowMapPlayerLocation=True\n"
                    "AllowThirdPersonPlayer=True\n"
                    "ServerCrosshair=True\n"
                    "EnablePvPGamma=True\n"
                    "\n[SessionSettings]\n"
                    f"SessionName={sess_name}\n"
                )
                atomic_write_text(target_gus, default_gus)

        if not target_game.exists():
            if target_game != self.game_file and self.game_file.exists():
                try:
                    shutil.copy2(self.game_file, target_game)
                except Exception:
                    pass
            if not target_game.exists():
                default_game = (
                    "[/script/shootergame.shootergamemode]\n"
                    "MatingIntervalMultiplier=1.0\n"
                    "EggHatchSpeedMultiplier=1.0\n"
                    "BabyMatureSpeedMultiplier=1.0\n"
                    "BabyCuddleIntervalMultiplier=1.0\n"
                )
                atomic_write_text(target_game, default_game)

    def _resolve_instance_targets(self, instance_id: str = "main") -> Tuple[Path, Path, Optional[Dict[str, Any]]]:
        """Resuelve las rutas de GameUserSettings.ini y Game.ini para la instancia dada."""
        clean_id = (instance_id or "main").strip()
        if not clean_id or clean_id == "main":
            self._ensure_paths()
            return self.gus_file, self.game_file, None

        inst = cluster_manager._instances.get(clean_id)
        if not inst:
            self._ensure_paths()
            return self.gus_file, self.game_file, None

        alt_save = Path(str(inst.get("alt_save_dir") or inst.get("map") or clean_id)).name
        inst_config_dir = settings.ark_data_dir / "ShooterGame" / "Saved" / alt_save / "Config" / "LinuxServer"
        inst_gus = inst_config_dir / "GameUserSettings.ini"
        inst_game = inst_config_dir / "Game.ini"
        self._ensure_paths(inst_gus, inst_game, inst)
        return inst_gus, inst_game, inst

    def read_ini_section(self, file_path: Path, target_section: str) -> Dict[str, str]:
        """Lee una sección específica de un archivo .ini preservando mayúsculas y minúsculas."""
        if not file_path.exists():
            return {}
        result = {}
        in_section = False

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    sec_match = _SECTION_REGEX.match(line)
                    if sec_match:
                        current_sec = sec_match.group(1).strip()
                        in_section = (current_sec.lower() == target_section.lower())
                        continue

                    if in_section:
                        kv_match = _KV_REGEX.match(line)
                        if kv_match:
                            key = kv_match.group(1).strip()
                            val = kv_match.group(2).strip()
                            result[key] = val
        except Exception:
            pass
        return result

    def update_ini_section(self, file_path: Path, target_section: str, updates: Dict[str, str]) -> bool:
        """Actualiza o añade claves en una sección .ini manteniendo comentarios y el resto de secciones."""
        self._ensure_paths()
        if not file_path.exists():
            lines = [f"[{target_section}]\n"]
            for k, v in updates.items():
                lines.append(f"{k}={v}\n")
            atomic_write_text(file_path, "".join(lines))
            return True

        new_lines = []
        in_section = False
        section_found = False
        keys_written = set()

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                sec_match = _SECTION_REGEX.match(line)
                if sec_match:
                    if in_section:
                        for k, v in updates.items():
                            if k.lower() not in keys_written:
                                new_lines.append(f"{k}={v}\n")
                                keys_written.add(k.lower())
                    current_sec = sec_match.group(1).strip()
                    in_section = (current_sec.lower() == target_section.lower())
                    if in_section:
                        section_found = True
                    new_lines.append(line)
                    continue

                if in_section:
                    kv_match = _KV_REGEX.match(line)
                    if kv_match:
                        key = kv_match.group(1).strip()
                        key_lower = key.lower()
                        matched_update_key = next((uk for uk in updates if uk.lower() == key_lower), None)
                        if matched_update_key:
                            new_val = updates[matched_update_key]
                            new_lines.append(f"{matched_update_key}={new_val}\n")
                            keys_written.add(key_lower)
                            continue
                new_lines.append(line)

        if in_section:
            for k, v in updates.items():
                if k.lower() not in keys_written:
                    new_lines.append(f"{k}={v}\n")
                    keys_written.add(k.lower())

        if not section_found:
            new_lines.append(f"\n[{target_section}]\n")
            for k, v in updates.items():
                new_lines.append(f"{k}={v}\n")

        atomic_write_text(file_path, "".join(new_lines))
        return True

    def get_all_settings(self, instance_id: str = "main") -> Dict[str, Any]:
        """Obtiene una vista consolidada y limpia de todas las configuraciones de ARK para la instancia."""
        gus_file, game_file, inst = self._resolve_instance_targets(instance_id)
        gus_settings = self.read_ini_section(gus_file, "ServerSettings")
        game_settings = self.read_ini_section(game_file, "/script/shootergame.shootergamemode")

        default_session = inst.get("session_name", settings.session_name) if inst else settings.session_name
        default_srv_pass = inst.get("server_password", settings.server_password) if inst else settings.server_password
        default_adm_pass = inst.get("rcon_password", settings.admin_ark_password) if inst else settings.admin_ark_password
        default_max_p = str(inst.get("max_players", settings.max_players)) if inst else str(settings.max_players)
        default_world = inst.get("map", settings.world) if inst else settings.world

        return {
            "instance_id": instance_id if inst else "main",
            "instance_name": inst.get("name", "Principal") if inst else "Principal",
            "server": {
                "session_name": gus_settings.get("SessionName", default_session),
                "server_password": gus_settings.get("ServerPassword", default_srv_pass),
                "admin_password": gus_settings.get("ServerAdminPassword", default_adm_pass),
                "max_players": gus_settings.get("MaxPlayers", default_max_p),
                "world": default_world,
                "mod_ids": settings.runtime_config.get("mod_ids", os.getenv("MOD_IDS", "")),
                "cluster_id": settings.runtime_config.get("cluster_id", os.getenv("CLUSTER_ID", "")),
                "cluster_dir_override": settings.runtime_config.get("cluster_dir_override", os.getenv("CLUSTER_DIR_OVERRIDE", "/home/steam/clusters")),
                "additional_args": settings.runtime_config.get("additional_args", os.getenv("ADDITIONAL_ARGS", "")),
                "beta": settings.runtime_config.get("beta", os.getenv("BETA", "public")),
                "update_on_start": settings.runtime_config.get("update_on_start", os.getenv("UPDATE_ON_START", "true").lower() in ("true", "1", "yes")),
                "battleeye": settings.runtime_config.get("battleeye", os.getenv("BATTLEEYE", "false").lower() in ("true", "1", "yes")),
                "autostart_server": settings.runtime_config.get("autostart_server", os.getenv("AUTOSTART_SERVER", "true").lower() in ("true", "1", "yes"))
            },
            "multipliers": {
                "xp": gus_settings.get("XPMultiplier", os.getenv("XP_MULTIPLIER", "1.0")),
                "taming": gus_settings.get("TamingSpeedMultiplier", os.getenv("TAME_SPEED_MULTIPLIER", "1.0")),
                "harvest": gus_settings.get("HarvestAmountMultiplier", os.getenv("HARVEST_AMOUNT_MULTIPLIER", "1.0")),
                "mating": game_settings.get("MatingIntervalMultiplier", os.getenv("MATING_INTERVAL_MULTIPLIER", "1.0")),
                "hatch": game_settings.get("EggHatchSpeedMultiplier", os.getenv("HATCH_SPEED_MULTIPLIER", "1.0")),
                "mature": game_settings.get("BabyMatureSpeedMultiplier", os.getenv("MATURATION_SPEED_MULTIPLIER", "1.0")),
                "crafting": gus_settings.get("CraftingSpeedMultiplier", os.getenv("CRAFT_SPEED_MULTIPLIER", "1.0")),
                "cuddle": game_settings.get("BabyCuddleIntervalMultiplier", "1.0"),
                "day_cycle": gus_settings.get("DayCycleSpeedScale", "1.0"),
                "day_time": gus_settings.get("DayTimeSpeedScale", "1.0"),
                "night_time": gus_settings.get("NightTimeSpeedScale", "1.0")
            },
            "rules": {
                "show_map_player": gus_settings.get("ShowMapPlayerLocation", "True").lower() == "true",
                "third_person": gus_settings.get("AllowThirdPersonPlayer", "True").lower() == "true",
                "crosshair": gus_settings.get("ServerCrosshair", "True").lower() == "true",
                "pvp_gamma": gus_settings.get("EnablePvPGamma", "True").lower() == "true",
                "pve_mode": gus_settings.get("ServerPVE", os.getenv("SERVER_PVE", "false")).lower() == "true"
            }
        }

    def save_settings(self, payload: Dict[str, Any], instance_id: str = "main") -> bool:
        """Aplica y guarda los cambios en GameUserSettings.ini y Game.ini para la instancia."""
        gus_file, game_file, inst = self._resolve_instance_targets(instance_id)
        gus_updates = {}
        game_updates = {}

        if "server" in payload:
            srv = payload["server"]
            if inst is not None and instance_id != "main":
                # Actualizar metadatos de la instancia secundaria de clúster
                inst_updates: Dict[str, Any] = {}
                if "world" in srv:
                    inst["map"] = srv["world"]
                if "session_name" in srv:
                    inst_updates["session_name"] = srv["session_name"]
                    gus_updates["SessionName"] = srv["session_name"]
                if "server_password" in srv:
                    inst_updates["server_password"] = srv["server_password"]
                    gus_updates["ServerPassword"] = srv["server_password"]
                if "admin_password" in srv:
                    inst_updates["rcon_password"] = srv["admin_password"]
                    gus_updates["ServerAdminPassword"] = srv["admin_password"]
                if "max_players" in srv:
                    try:
                        inst_updates["max_players"] = int(srv["max_players"])
                        gus_updates["MaxPlayers"] = str(srv["max_players"])
                    except Exception:
                        pass
                if inst_updates:
                    cluster_manager.update_instance(instance_id, inst_updates)
            else:
                runtime_updates = {}
                if "world" in srv:
                    settings.world = srv["world"]
                    runtime_updates["world"] = srv["world"]
                if "session_name" in srv:
                    settings.session_name = srv["session_name"]
                    runtime_updates["session_name"] = srv["session_name"]
                    gus_updates["SessionName"] = srv["session_name"]
                if "server_password" in srv:
                    settings.server_password = srv["server_password"]
                    runtime_updates["server_password"] = srv["server_password"]
                    gus_updates["ServerPassword"] = srv["server_password"]
                if "admin_password" in srv:
                    settings.admin_ark_password = srv["admin_password"]
                    runtime_updates["admin_ark_password"] = srv["admin_password"]
                    gus_updates["ServerAdminPassword"] = srv["admin_password"]
                if "max_players" in srv:
                    try:
                        settings.max_players = int(srv["max_players"])
                        runtime_updates["max_players"] = int(srv["max_players"])
                        gus_updates["MaxPlayers"] = str(srv["max_players"])
                    except Exception:
                        pass

                for k in ["mod_ids", "cluster_id", "cluster_dir_override", "additional_args", "beta", "update_on_start", "battleeye", "autostart_server"]:
                    if k in srv:
                        runtime_updates[k] = srv[k]
                if runtime_updates:
                    settings.save_runtime_config(runtime_updates)

        if "multipliers" in payload:
            m = payload["multipliers"]
            if "xp" in m:
                gus_updates["XPMultiplier"] = str(m["xp"])
            if "taming" in m:
                gus_updates["TamingSpeedMultiplier"] = str(m["taming"])
            if "harvest" in m:
                gus_updates["HarvestAmountMultiplier"] = str(m["harvest"])
            if "crafting" in m:
                gus_updates["CraftingSpeedMultiplier"] = str(m["crafting"])
            if "day_cycle" in m:
                gus_updates["DayCycleSpeedScale"] = str(m["day_cycle"])
            if "day_time" in m:
                gus_updates["DayTimeSpeedScale"] = str(m["day_time"])
            if "night_time" in m:
                gus_updates["NightTimeSpeedScale"] = str(m["night_time"])
            if "mating" in m:
                game_updates["MatingIntervalMultiplier"] = str(m["mating"])
            if "hatch" in m:
                game_updates["EggHatchSpeedMultiplier"] = str(m["hatch"])
            if "mature" in m:
                game_updates["BabyMatureSpeedMultiplier"] = str(m["mature"])
            if "cuddle" in m:
                game_updates["BabyCuddleIntervalMultiplier"] = str(m["cuddle"])

        if "rules" in payload:
            r = payload["rules"]
            if "show_map_player" in r:
                gus_updates["ShowMapPlayerLocation"] = "True" if r["show_map_player"] else "False"
            if "third_person" in r:
                gus_updates["AllowThirdPersonPlayer"] = "True" if r["third_person"] else "False"
            if "crosshair" in r:
                gus_updates["ServerCrosshair"] = "True" if r["crosshair"] else "False"
            if "pvp_gamma" in r:
                gus_updates["EnablePvPGamma"] = "True" if r["pvp_gamma"] else "False"
            if "pve_mode" in r:
                gus_updates["ServerPVE"] = "True" if r["pve_mode"] else "False"

        ok1 = self.update_ini_section(gus_file, "ServerSettings", gus_updates)
        ok2 = self.update_ini_section(game_file, "/script/shootergame.shootergamemode", game_updates)
        return ok1 and ok2

    def sync_rates_to_all(self, rates: Dict[str, Any]) -> Dict[str, Any]:
        """Sincroniza multiplicadores a todos los archivos .ini de las instancias del clúster."""
        ok_main = self.save_settings({"multipliers": rates}, instance_id="main")
        count = 1 if ok_main else 0
        for inst_id in cluster_manager.list_instance_ids():
            if inst_id == "main":
                continue
            if self.save_settings({"multipliers": rates}, instance_id=inst_id):
                count += 1
        return {"success": True, "synced_nodes": count}


ark_settings_manager = ArkSettingsManager()
