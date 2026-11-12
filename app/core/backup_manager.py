import os
import time
import tarfile
import zipfile
import shutil
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.config import settings
from app.core.fs_utils import is_subpath
from app.core.process_manager import process_manager
from app.core.webhook_manager import webhook_manager
from app.core.file_manager import PROTECTED_FILES

MAX_RESTORE_UNCOMPRESSED_BYTES = int(os.getenv("MAX_RESTORE_UNCOMPRESSED_MB", "51200")) * 1024 * 1024  # 50 GB default
CHUNK_SIZE = 64 * 1024


class BackupManager:
    """
    Gestiona la creación, restauración, rotación y descarga de copias de seguridad de ARK
    conservando la jerarquía nativa organizada:
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
        if not is_subpath(target, self.backup_dir):
            return None
        return target if target.exists() and target.is_file() else None

    @staticmethod
    def _safe_extract_tar(tar: tarfile.TarFile, dest_dir: Path, max_bytes: int = MAX_RESTORE_UNCOMPRESSED_BYTES) -> None:
        """Extrae un archivo tar validando contra TarSlip, enlaces simbólicos/hardlinks y tamaño máximo."""
        resolved_dest = dest_dir.resolve()
        members = tar.getmembers()
        total_size = 0

        for member in members:
            if member.issym() or member.islnk() or member.ischr() or member.isblk() or member.isfifo():
                raise ValueError(f"El archivo de respaldo contiene enlaces o dispositivos no permitidos: {member.name}")

            member_target = (resolved_dest / member.name).resolve()
            if not member_target.is_relative_to(resolved_dest):
                raise ValueError(f"Ruta fuera del directorio destino (TarSlip detectado): {member.name}")

            if member_target.name in PROTECTED_FILES:
                raise ValueError(f"El respaldo intenta sobrescribir un archivo protegido: {member_target.name}")

            total_size += max(0, member.size)
            if total_size > max_bytes:
                raise ValueError("El tamaño descomprimido del respaldo excede el límite de seguridad.")

        written_total = 0
        for member in members:
            member_target = (resolved_dest / member.name).resolve()
            if member.isdir():
                member_target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                member_target.parent.mkdir(parents=True, exist_ok=True)
                src = tar.extractfile(member)
                if src is not None:
                    with src, open(member_target, "wb") as dst:
                        while True:
                            chunk = src.read(CHUNK_SIZE)
                            if not chunk:
                                break
                            written_total += len(chunk)
                            if written_total > max_bytes:
                                dst.close()
                                member_target.unlink(missing_ok=True)
                                raise ValueError("Límite de extracción excedido durante la restauración.")
                            dst.write(chunk)

    @staticmethod
    def _safe_extract_zip(zip_path: Path, dest_dir: Path, max_bytes: int = MAX_RESTORE_UNCOMPRESSED_BYTES) -> None:
        """Extrae un archivo zip validando contra ZipSlip, symlinks, ZipBomb y archivos protegidos."""
        resolved_dest = dest_dir.resolve()
        with zipfile.ZipFile(zip_path, "r") as zf:
            infos = zf.infolist()
            total_size = 0
            for info in infos:
                unix_mode = (info.external_attr >> 16) & 0o170000
                if unix_mode == 0o120000:
                    raise ValueError(f"El archivo ZIP contiene enlaces simbólicos no permitidos: {info.filename}")
                member_target = (resolved_dest / info.filename).resolve()
                if not member_target.is_relative_to(resolved_dest):
                    raise ValueError(f"Ruta fuera del directorio destino (ZipSlip detectado): {info.filename}")
                if member_target.name in PROTECTED_FILES:
                    raise ValueError(f"El respaldo intenta sobrescribir un archivo protegido: {member_target.name}")
                total_size += max(0, info.file_size)
                if total_size > max_bytes:
                    raise ValueError("El tamaño descomprimido del respaldo excede el límite de seguridad.")

            written_total = 0
            for info in infos:
                member_target = (resolved_dest / info.filename).resolve()
                if info.is_dir() or info.filename.endswith("/"):
                    member_target.mkdir(parents=True, exist_ok=True)
                    continue
                member_target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as src, open(member_target, "wb") as dst:
                    while True:
                        chunk = src.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        written_total += len(chunk)
                        if written_total > max_bytes:
                            dst.close()
                            member_target.unlink(missing_ok=True)
                            raise ValueError("Límite de extracción excedido durante la restauración.")
                        dst.write(chunk)

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

    async def create_backup(self, custom_name: Optional[str] = None, notify: bool = True) -> Dict[str, Any]:
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

        def _do_compress():
            staging = self.backup_dir / f".staging_{int(time.time() * 1000)}"
            staging.mkdir(parents=True, exist_ok=True)

            target_saved = staging / "Saved"
            target_arks = target_saved / "SavedArks"
            target_config = target_saved / "Config" / "LinuxServer"
            target_savegames = target_saved / "SaveGames"
            target_arks.mkdir(parents=True, exist_ok=True)
            target_config.mkdir(parents=True, exist_ok=True)

            source_config = self.saved_dir / "Config" / "LinuxServer"
            source_savegames = self.saved_dir / "SaveGames"

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

            if source_config.exists():
                for ini in ("Game.ini", "GameUserSettings.ini"):
                    src_ini = source_config / ini
                    if src_ini.exists():
                        shutil.copy2(src_ini, target_config / ini)

            if source_savegames.exists():
                target_savegames.mkdir(parents=True, exist_ok=True)
                for item in source_savegames.iterdir():
                    if item.is_file():
                        shutil.copy2(item, target_savegames / item.name)

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

            with tarfile.open(out_path, "w:gz") as tar:
                tar.add(target_saved, arcname="Saved")
                tar.add(staging / "LEEME_RESTAURACION.txt", arcname="LEEME_RESTAURACION.txt")

            shutil.rmtree(staging, ignore_errors=True)
            return out_path.stat().st_size

        try:
            file_size = await asyncio.to_thread(_do_compress)
            size_mb = round(file_size / (1024 * 1024), 2)
            try:
                max_keep = int(settings.runtime_config.get("backup_max_count", os.getenv("BACKUP_MAX_COUNT", "10")))
            except Exception:
                max_keep = 10
            self._rotate_backups(max(1, max_keep))
            await process_manager.broadcast_log(f"[ARK Server Manager] Copia de seguridad '{clean_name}' completada ({size_mb} MB).")
            if notify:
                await webhook_manager.notify_backup(clean_name, size_mb)
            return {"success": True, "filename": clean_name, "size_mb": size_mb}
        except Exception as e:
            await process_manager.broadcast_log(f"[ARK Server Manager] Error en copia de seguridad: {e}")
            if notify:
                await webhook_manager.notify_backup_fail(str(e))
            return {"success": False, "error": str(e)}

    async def restore_backup(self, filename: str, create_safety_backup: bool = True) -> Dict[str, Any]:
        """Restaura una copia de seguridad soportando tanto formato organizado como legado, con validación anti-TarSlip/ZipSlip."""
        target_file = self._resolve_backup(filename)
        if not target_file:
            return {"success": False, "error": "El archivo de respaldo no existe."}

        was_running = process_manager.get_status() == "RUNNING"
        if was_running:
            await process_manager.broadcast_log("[ARK Server Manager] Deteniendo servidor para restaurar copia de seguridad...")
            await process_manager.stop_server()
            await asyncio.sleep(2)

        # Crear copia preventiva antes de sobrescribir los datos actuales si existe Saved/
        if create_safety_backup and self.saved_dir.exists():
            try:
                await self.create_backup(custom_name=f"pre_restore_{int(time.time())}", notify=False)
            except Exception:
                pass

        def _do_extract():
            shooter_dir = settings.ark_data_dir / "ShooterGame"
            shooter_dir.mkdir(parents=True, exist_ok=True)

            is_zip = target_file.name.lower().endswith(".zip")
            if is_zip:
                with zipfile.ZipFile(target_file, "r") as zf:
                    names = zf.namelist()
                has_saved = any(n.startswith("Saved/") or n.startswith("./Saved/") for n in names)
                if has_saved:
                    self._safe_extract_zip(target_file, shooter_dir)
                else:
                    temp_dir = self.backup_dir / f".temp_restore_{int(time.time() * 1000)}"
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    try:
                        self._safe_extract_zip(target_file, temp_dir)
                        self._copy_flat_extracted_files(temp_dir, shooter_dir)
                    finally:
                        shutil.rmtree(temp_dir, ignore_errors=True)
            else:
                with tarfile.open(target_file, "r:*") as tar:
                    names = tar.getnames()
                    has_saved = any(n.startswith("Saved/") or n.startswith("./Saved/") for n in names)
                    if has_saved:
                        self._safe_extract_tar(tar, shooter_dir)
                    else:
                        temp_dir = self.backup_dir / f".temp_restore_{int(time.time() * 1000)}"
                        temp_dir.mkdir(parents=True, exist_ok=True)
                        try:
                            self._safe_extract_tar(tar, temp_dir)
                            self._copy_flat_extracted_files(temp_dir, shooter_dir)
                        finally:
                            shutil.rmtree(temp_dir, ignore_errors=True)

            # Sincronizar copias si el mapa activo utiliza nombre de carpeta personalizado
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
            await asyncio.to_thread(_do_extract)
            await process_manager.broadcast_log(f"[ARK Server Manager] Copia '{filename}' restaurada exitosamente.")
            await webhook_manager.notify_restore(filename)
            if was_running:
                await process_manager.start_server()
            return {"success": True}
        except Exception as e:
            await process_manager.broadcast_log(f"[ARK Server Manager] Error al restaurar copia: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _copy_flat_extracted_files(temp_dir: Path, shooter_dir: Path) -> None:
        target_arks = shooter_dir / "Saved" / "SavedArks"
        target_config = shooter_dir / "Saved" / "Config" / "LinuxServer"
        target_arks.mkdir(parents=True, exist_ok=True)
        target_config.mkdir(parents=True, exist_ok=True)

        for root, _, files in os.walk(temp_dir):
            for f in files:
                src_p = Path(root) / f
                if f.endswith((".ark", ".arkprofile", ".arktribe")):
                    shutil.copy2(src_p, target_arks / f)
                elif f in ("Game.ini", "GameUserSettings.ini"):
                    shutil.copy2(src_p, target_config / f)

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
