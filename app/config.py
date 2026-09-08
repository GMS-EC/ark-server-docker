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

        # ARK Server settings
        self.session_name: str = os.getenv("SESSION_NAME", "ARK Server")
        self.server_password: str = os.getenv("SERVER_PASSWORD", "")
        self.admin_ark_password: str = os.getenv("ADMIN_PASSWORD", "adminpass")
        self.max_players: int = int(os.getenv("MAX_PLAYERS", "20"))
        self.world: str = os.getenv("WORLD", "TheIsland")
        self.server_port: int = int(os.getenv("SERVER_PORT", "7777"))
        self.query_port: int = int(os.getenv("QUERY_PORT", "27015"))
        self.rcon_port: int = int(os.getenv("RCON_PORT", "27020"))
        self.rcon_host: str = os.getenv("RCON_HOST", "127.0.0.1")
        self.rcon_enabled: bool = os.getenv("RCON_ENABLED", "true").lower() in ("true", "1", "yes")

    def _load_runtime_config(self) -> Dict[str, Any]:
        if self._config_file.exists():
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "autostart_server": os.getenv("AUTOSTART_SERVER", "true").lower() in ("true", "1", "yes"),
            "theme": "dark",
            "lang": "es",
            "auto_backup_enabled": True,
            "auto_backup_interval_hours": 6,
            "auto_dino_wipe_enabled": False,
            "auto_dino_wipe_hours": 24,
            "discord_webhook_url": os.getenv("DISCORD_WEBHOOK_URL", ""),
            "discord_language": os.getenv("DISCORD_LANGUAGE", "es")
        }

    def save_runtime_config(self, new_config: Dict[str, Any]) -> None:
        self.runtime_config.update(new_config)
        try:
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self.runtime_config, f, indent=2)
        except Exception as e:
            print(f"[Config] Error guardando ark_panel_config.json: {e}")

settings = Settings()
