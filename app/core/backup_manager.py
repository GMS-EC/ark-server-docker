import os
import time
import tarfile
import shutil
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.config import settings
from app.core.process_manager import process_manager
from app.core.webhook_manager import webhook_manager

class BackupManager:
    """
    Gestiona la creación, restauración, rotación y descarga de copias de seguridad de ARK
    conservando la jerarquía nativa organizada idéntica a ark-server-docker:
    Saved/
      ├── SavedArks/ (Map.ark, *.arkprofile, *.arktribe)
      ├── Config/LinuxServer/ (Game.ini, GameUserSettings.ini)
      └── SaveGames/
    """
    def __init__(self):
        self.backup_dir: Path = settings.backups_dir
        self.saved_dir: Path = settings.ark_data_dir / "ShooterGame" / "Saved"

    def _resolve_backup(self, filename: str) -> Optional[Path]:
        """Resuelve un nombre de backup dentro de backup_dir rechazando path traversal."""
        if not filename or "/" in filename or "\\" in filename or ".." in filename:
            return None
        target = (self.backup_dir / Path(filename).name).resolve()
        if not self._is_subpath(target, self.backup_dir):
            return None
        return target if target.exists() and target.is_file() else None

    @staticmethod
    def _is_subpath(path: Path, parent: Path) -> bool:
        try:
            path.resolve().relative_to(parent.resolve())
            return True
        except (ValueError, AttributeError):
            return False

    def list_backups(self) -> List[Dict[str, Any]]:
        """Lista todos los archivos de respaldo (.tar.gz, .tar.bz2, .zip, .tgz) en orden cronológico."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        results = []
        valid_exts = (".tar.gz", ".tar.bz2", ".tgz", ".zip")
        try:
            for item in self.backup_dir.iterdir():
                if item.is_file() and any(item.name.endswith(ext) for ext in valid_exts):
                    stat = item.stat()
                    size_mb = round(stat.st_size / (1024 * 1024), 2)
                    created_str = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
                    results.append({
                        "filename": item.name,
                        "size_mb": size_mb,
                        "created_at": created_str,
                        "timestamp": stat.st_mtime
                    })
        except Exception:
            pass
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results

    async def create_backup(self, custom_name: Optional[str] = None) -> Dict[str, Any]:
        """Crea una copia de seguridad estructurada compatible con ark-server-docker."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # 1. Forzar guardado del mundo si el servidor está corriendo
        if process_manager.get_status() == "RUNNING":
            try:
                await process_manager.rcon.save_world()
                await asyncio.sleep(2)
            except Exception:
                pass

        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"ark_backup_{custom_name.strip()}" if custom_name and custom_name.strip() != "auto" else f"ark_backup_{now_str}"
        clean_name = "".join(c for c in prefix if c.isalnum() or c in ("-", "_")) + ".tar.gz"
        out_path = self.backup_dir / clean_name

        loop = asyncio.get_running_loop()

        def _do_compress():
            # Crear directorio temporal para organizar el respaldo idéntico a ark-server-docker
            staging = self.backup_dir / f".staging_{int(time.time())}"
            staging.mkdir(parents=True, exist_ok=True)

            target_saved = staging / "Saved"
            target_arks = target_saved / "SavedArks"
            target_config = target_saved / "Config" / "LinuxServer"
            target_savegames = target_saved / "SaveGames"
            target_arks.mkdir(parents=True, exist_ok=True)
            target_config.mkdir(parents=True, exist_ok=True)

            source_config = self.saved_dir / "Config" / "LinuxServer"
            source_savegames = self.saved_dir / "SaveGames"

            # Copiar archivos de mapa, perfiles y tribus desde cualquier directorio de guardado válido
            possible_ark_dirs = [
                self.saved_dir / "SavedArks",
                self.saved_dir / f"{settings.world}SavedArks",
                self.saved_dir / f"{settings.world.replace('_P', '')}SavedArks",
                self.saved_dir / settings.world / "SavedArks",
                self.saved_dir / settings.world,
            ]
            if self.saved_dir.exists():
                for sub in self.saved_dir.iterdir():
                    if sub.is_dir() and (sub.name.endswith("SavedArks") or sub.name == settings.world):
                        if sub not in possible_ark_dirs:
                            possible_ark_dirs.append(sub)

            copied_save_files = set()
            for s_dir in possible_ark_dirs:
                if s_dir.exists() and s_dir.is_dir():
                    for f in s_dir.iterdir():
                        if f.is_file():
                            if f.name.endswith((".ark", ".arkprofile", ".arktribe", ".profilebak", ".tribebak")):
                                if f.name not in copied_save_files:
                                    shutil.copy2(f, target_arks / f.name)
                                    copied_save_files.add(f.name)

            # Copiar Game.ini y GameUserSettings.ini
            if source_config.exists():
                for ini in ("Game.ini", "GameUserSettings.ini"):
                    src_ini = source_config / ini
                    if src_ini.exists():
                        shutil.copy2(src_ini, target_config / ini)

            # Copiar SaveGames si existe
            if source_savegames.exists():
                target_savegames.mkdir(parents=True, exist_ok=True)
                for item in source_savegames.iterdir():
                    if item.is_file():
                        shutil.copy2(item, target_savegames / item.name)

            # Agregar README de restauración idéntico a ark-server-docker
            readme_text = (
                "================================================================================\n"
                "          COPIA DE SEGURIDAD ORGANIZADA DE ARK: SURVIVAL EVOLVED\n"
                "================================================================================\n"
                "Estructura:\n"
                "Saved/\n"
                "  ├── SavedArks/ (Mapas, dinosaurios y personajes)\n"
                "  ├── Config/LinuxServer/ (Game.ini y GameUserSettings.ini)\n"
                "  └── SaveGames/\n"
            )
            with open(staging / "LEEME_RESTAURACION.txt", "w", encoding="utf-8") as rf:
                rf.write(readme_text)

            # Empaquetar en tar.gz
            with tarfile.open(out_path, "w:gz") as tar:
                tar.add(target_saved, arcname="Saved")
                tar.add(staging / "LEEME_RESTAURACION.txt", arcname="LEEME_RESTAURACION.txt")

            shutil.rmtree(staging, ignore_errors=True)
            return out_path.stat().st_size

        try:
            file_size = await loop.run_in_executor(None, _do_compress)
            size_mb = round(file_size / (1024 * 1024), 2)
            max_keep = int(os.getenv("BACKUP_MAX_COUNT", "10"))
            self._rotate_backups(max_keep)
            await process_manager.broadcast_log(f"[ARK Server Manager] Copia de seguridad '{clean_name}' completada ({size_mb} MB).")
            await webhook_manager.notify_backup(clean_name, size_mb)
            return {"success": True, "filename": clean_name, "size_mb": size_mb}
        except Exception as e:
            await process_manager.broadcast_log(f"[ARK Server Manager] Error en copia de seguridad: {e}")
            await webhook_manager.notify_backup_fail(str(e))
            return {"success": False, "error": str(e)}

    async def restore_backup(self, filename: str) -> Dict[str, Any]:
        """Restaura una copia de seguridad soportando tanto formato organizado como legado."""
        target_file = self._resolve_backup(filename)
        if not target_file:
            return {"success": False, "error": "El archivo de respaldo no existe."}

        was_running = process_manager.get_status() == "RUNNING"
        if was_running:
            await process_manager.broadcast_log("[ARK Server Manager] Deteniendo servidor para restaurar copia de seguridad...")
            await process_manager.stop_server()
            await asyncio.sleep(2)

        loop = asyncio.get_running_loop()

        def _do_extract():
            shooter_dir = settings.ark_data_dir / "ShooterGame"
            shooter_dir.mkdir(parents=True, exist_ok=True)

            # Modo de lectura automática para tar.gz, tar.bz2, etc.
            with tarfile.open(target_file, "r:*") as tar:
                names = tar.getnames()
                has_saved = any(n.startswith("Saved/") or n.startswith("./Saved/") for n in names)
                if has_saved:
                    tar.extractall(path=shooter_dir)
                else:
                    # Formato plano legado: extraer a Saved/SavedArks
                    target_arks = shooter_dir / "Saved" / "SavedArks"
                    target_config = shooter_dir / "Saved" / "Config" / "LinuxServer"
                    target_arks.mkdir(parents=True, exist_ok=True)
                    target_config.mkdir(parents=True, exist_ok=True)

                    temp_dir = self.backup_dir / f".temp_restore_{int(time.time())}"
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    tar.extractall(path=temp_dir)

                    for root, _, files in os.walk(temp_dir):
                        for f in files:
                            src_p = Path(root) / f
                            if f.endswith(".ark") or f.endswith(".arkprofile") or f.endswith(".arktribe"):
                                shutil.copy2(src_p, target_arks / f)
                            elif f in ("Game.ini", "GameUserSettings.ini"):
                                shutil.copy2(src_p, target_config / f)
                    shutil.rmtree(temp_dir, ignore_errors=True)

            # Sincronizar copias si el mapa activo utiliza nombre de carpeta personalizado (ej: ScorchedEarth_PSavedArks)
            clean_world = settings.world.replace("_P", "")
            if clean_world.lower() != "theisland":
                custom_saved_dir = shooter_dir / "Saved" / f"{clean_world}SavedArks"
                source_arks = shooter_dir / "Saved" / "SavedArks"
                if source_arks.exists() and source_arks.is_dir():
                    custom_saved_dir.mkdir(parents=True, exist_ok=True)
                    for f in source_arks.iterdir():
                        if f.is_file() and not (custom_saved_dir / f.name).exists():
                            try:
                                shutil.copy2(f, custom_saved_dir / f.name)
                            except Exception:
                                pass

        try:
            await loop.run_in_executor(None, _do_extract)
            await process_manager.broadcast_log(f"[ARK Server Manager] Copia '{filename}' restaurada exitosamente.")
            await webhook_manager.notify_restore(filename)
            if was_running:
                await process_manager.start_server()
            return {"success": True}
        except Exception as e:
            await process_manager.broadcast_log(f"[ARK Server Manager] Error al restaurar copia: {e}")
            return {"success": False, "error": str(e)}

    def delete_backup(self, filename: str) -> bool:
        target = self._resolve_backup(filename)
        if target:
            try:
                target.unlink()
                return True
            except Exception:
                return False
        return False

    def get_backup_path(self, filename: str) -> Optional[Path]:
        return self._resolve_backup(filename)

    def _rotate_backups(self, max_count: int = 10):
        backups = self.list_backups()
        if len(backups) > max_count:
            to_remove = backups[max_count:]
            for b in to_remove:
                self.delete_backup(b["filename"])

backup_manager = BackupManager()
