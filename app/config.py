import os
import json
import secrets
from pathlib import Path
from typing import Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    def __init__(self):
        # Paths
        self.base_dir: Path = BASE_DIR
        
        # En Docker: /home/steam/steamcmd/ark y /home/steam/ark-backups
        # En local/desarrollo: usar fallback dentro de data y backups
        default_data = Path(os.getenv("ARK_DATA_DIR", "/home/steam/steamcmd/ark"))
        if not default_data.exists() and not os.path.exists("/home/steam"):
            default_data = self.base_dir / "data"
        default_data.mkdir(parents=True, exist_ok=True)
        self.ark_data_dir: Path = default_data

        default_backups = Path(os.getenv("BACKUP_DIR", "/home/steam/ark-backups"))
        if not default_backups.exists() and not os.path.exists("/home/steam"):
            default_backups = self.base_dir / "backups"
        default_backups.mkdir(parents=True, exist_ok=True)
        self.backups_dir: Path = default_backups

        # Cluster shared directory
        default_clusters = Path(os.getenv("CLUSTER_DIR_OVERRIDE", "/home/steam/clusters"))
        if not default_clusters.exists() and not os.path.exists("/home/steam"):
            default_clusters = self.base_dir / "clusters"
        default_clusters.mkdir(parents=True, exist_ok=True)
        self.cluster_dir: Path = default_clusters
        self.cluster_id: str = os.getenv("CLUSTER_ID", "ArkCluster")

        # Log file
        self.log_file: Path = self.ark_data_dir / "ShooterGame" / "Saved" / "Logs" / "ShooterGame.log"

        # Web Panel Auth
        self.panel_port: int = int(os.getenv("PANEL_PORT", "8080"))
        self.admin_user: str = os.getenv("PANEL_USER", "admin")
        self.admin_password: str = os.getenv("PANEL_PASSWORD", "adminpassword")

        # Config file
        self._config_file = self.ark_data_dir / "ark_panel_config.json"
        self.runtime_config: Dict[str, Any] = self._load_runtime_config()

        # Secret Key persistente (prioridad: env -> json en disco -> nuevo)
        env_secret = os.getenv("SECRET_KEY", "").strip()
        if env_secret:
            self.secret_key = env_secret
        else:
            saved_secret = str(self.runtime_config.get("secret_key", "")).strip()
            if saved_secret:
                self.secret_key = saved_secret
            else:
                self.secret_key = secrets.token_hex(32)
                self.runtime_config["secret_key"] = self.secret_key
                self.save_runtime_config({})

        # ARK Server settings (Carga dinámica desde runtime_config con fallback a env vars)
        self.session_name: str = self.runtime_config.get("session_name", os.getenv("SESSION_NAME", "ARK Server"))
        self.server_password: str = self.runtime_config.get("server_password", os.getenv("SERVER_PASSWORD", ""))
        self.admin_ark_password: str = self.runtime_config.get("admin_ark_password", os.getenv("ADMIN_PASSWORD", "adminpass"))
        try:
            self.max_players: int = int(self.runtime_config.get("max_players", os.getenv("MAX_PLAYERS", "20")))
        except Exception:
            self.max_players = 20
        self.world: str = self.runtime_config.get("world", os.getenv("WORLD", "TheIsland"))
        self.server_port: int = int(os.getenv("SERVER_PORT", "7777"))
        self.query_port: int = int(os.getenv("QUERY_PORT", "27015"))
        self.rcon_port: int = int(os.getenv("RCON_PORT", "27020"))
        self.rcon_host: str = os.getenv("RCON_HOST", "127.0.0.1")
        self.rcon_enabled: bool = os.getenv("RCON_ENABLED", "true").lower() in ("true", "1", "yes")

    def _load_runtime_config(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        if self._config_file.exists():
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        # Sincronizar automáticamente variables de entorno para que nunca se pierdan
        if "world" not in data:
            data["world"] = os.getenv("WORLD", "TheIsland")
        if "session_name" not in data:
            data["session_name"] = os.getenv("SESSION_NAME", "ARK Server")
        if "server_password" not in data:
            data["server_password"] = os.getenv("SERVER_PASSWORD", "")
        if "admin_ark_password" not in data:
            data["admin_ark_password"] = os.getenv("ADMIN_PASSWORD", "adminpass")
        if "max_players" not in data:
            try:
                data["max_players"] = int(os.getenv("MAX_PLAYERS", "20"))
            except Exception:
                data["max_players"] = 20
        if not data.get("discord_webhook_url"):
            env_wh = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
            if env_wh:
                data["discord_webhook_url"] = env_wh

        if "discord_language" not in data:
            data["discord_language"] = os.getenv("DISCORD_LANGUAGE", "es")

        if "schedule_enabled" not in data:
            data["schedule_enabled"] = os.getenv("SCHEDULE_ENABLED", "false").lower() in ("true", "1", "yes")

        if "schedule_start" not in data:
            data["schedule_start"] = os.getenv("SCHEDULE_START", "20:00")

        if "schedule_stop" not in data:
            data["schedule_stop"] = os.getenv("SCHEDULE_STOP", "00:00")

        if "schedule_warn_mins" not in data:
            data["schedule_warn_mins"] = int(os.getenv("SCHEDULE_WARN_MINUTES", "10"))

        if "auto_backup_enabled" not in data:
            data["auto_backup_enabled"] = os.getenv("BACKUP_ENABLED", "true").lower() in ("true", "1", "yes")

        if "auto_backup_interval_hours" not in data:
            data["auto_backup_interval_hours"] = int(os.getenv("BACKUP_INTERVAL_HOURS", "6"))

        if "backup_max_count" not in data:
            data["backup_max_count"] = int(os.getenv("BACKUP_MAX_COUNT", "10"))

        if "auto_restart_hours" not in data:
            data["auto_restart_hours"] = int(os.getenv("AUTO_RESTART_HOURS", "0"))

        if "autostart_server" not in data:
            data["autostart_server"] = os.getenv("AUTOSTART_SERVER", "true").lower() in ("true", "1", "yes")

        return data

    def save_runtime_config(self, new_config: Dict[str, Any]) -> None:
        self.runtime_config.update(new_config)
        if "world" in new_config:
            self.world = new_config["world"]
        if "session_name" in new_config:
            self.session_name = new_config["session_name"]
        if "server_password" in new_config:
            self.server_password = new_config["server_password"]
        if "admin_ark_password" in new_config:
            self.admin_ark_password = new_config["admin_ark_password"]
        if "max_players" in new_config:
            try:
                self.max_players = int(new_config["max_players"])
            except Exception:
                pass
        try:
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self.runtime_config, f, indent=2)
        except Exception as e:
            print(f"[Config] Error guardando ark_panel_config.json: {e}")

settings = Settings()
