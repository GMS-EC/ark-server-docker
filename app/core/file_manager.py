import os
import re
import stat
import shutil
import time
import logging
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Optional, NoReturn
from fastapi import HTTPException, UploadFile

from app.config import settings
from app.core.fs_utils import atomic_write_text, get_dir_size_cached, invalidate_dir_size_cache, is_subpath

logger = logging.getLogger("arkserver.files")


def _raise_internal_error(action: str, exc: Exception) -> NoReturn:
    """Registra el detalle técnico en logs y devuelve un error 500 genérico al cliente."""
    logger.exception("Error interno al %s: %s", action, exc)
    raise HTTPException(status_code=500, detail=f"Error interno al {action}.")

# Archivos de configuración/secreto del panel que no deben editarse/leerse/eliminarse/renombrarse
# desde el explorador web para evitar fugas accidentales o auto-compromiso.
PROTECTED_FILES = {
    "ark_panel_config.json",
    "arkraft_panel_config.json",
    "ark_cluster_instances.json",
    "arkraft_cluster_instances.json",
    "ark_players.json",
    "arkraft_players.json",
    "activity_logs.json",
    ".secret_key",
}

MAX_ZIP_COMPRESSION_RATIO = 100
MAX_ZIP_UNCOMPRESSED_BYTES = int(os.getenv("MAX_ZIP_UNCOMPRESSED_MB", "4096")) * 1024 * 1024
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "4096")) * 1024 * 1024
UPLOAD_CHUNK_SIZE = 64 * 1024


class FileManager:
    """
    Gestor de archivos completo y seguro para ARK Server Manager.
    Previene vulnerabilidades de Path Traversal, ZipSlip, ZipBomb, Symlinks y acceso
    a archivos críticos del panel.
    """
    def __init__(self):
        self.base_dir: Path = settings.ark_data_dir

    def _rel_to_root(self, path: Path) -> str:
        """Calcula la ruta relativa del elemento respecto a la raíz que lo contiene
        (ark_data, clusters o backups) para reportarla correctamente en la API."""
        for root in (self.base_dir, settings.cluster_dir, settings.backups_dir):
            try:
                rel = path.resolve().relative_to(root.resolve())
                return str(rel).replace("\\", "/")
            except (ValueError, AttributeError):
                continue
        return path.name

    def _is_special_root(self, path: Path) -> bool:
        """True si el path es una raíz que no debe eliminarse/renombrarse/duplicarse completa."""
        p = path.resolve()
        return p in (self.base_dir.resolve(), settings.cluster_dir.resolve(), settings.backups_dir.resolve())

    def _assert_not_protected(self, path_or_name: str) -> None:
        clean = str(path_or_name).replace("\\", "/").strip("/")
        parts = [p for p in clean.split("/") if p]
        if any(part in PROTECTED_FILES for part in parts) or Path(clean).name in PROTECTED_FILES:
            raise HTTPException(
                status_code=403,
                detail="Archivo de configuración o seguridad protegido del panel."
            )

    def _check_storage_quota(self, additional_bytes: int) -> None:
        """Verifica si existe una cuota de disco configurada (STORAGE_LIMIT_GB) o espacio físico libre."""
        limit_gb_str = os.getenv("STORAGE_LIMIT_GB", "").strip()
        if limit_gb_str:
            try:
                limit_bytes = int(float(limit_gb_str) * (1024 ** 3))
                if limit_bytes > 0:
                    current_used = get_dir_size_cached(self.base_dir)
                    if current_used + additional_bytes > limit_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail="Cuota de almacenamiento del servidor excedida."
                        )
            except HTTPException:
                raise
            except Exception:
                pass

    def _resolve_safe_path(self, relative_path: str = "") -> Path:
        clean_rel = (relative_path or "").replace("\\", "/").strip("/")

        # Acceso transparente a carpetas especiales compartidas: clusters y backups
        if clean_rel == "clusters" or clean_rel.startswith("clusters/"):
            sub_rel = clean_rel[len("clusters"):].lstrip("/")
            candidate = settings.cluster_dir / sub_rel
            if candidate.is_symlink():
                raise HTTPException(status_code=403, detail="Acceso denegado: enlaces simbólicos no permitidos")
            target = candidate.resolve()
            if not is_subpath(target, settings.cluster_dir):
                raise HTTPException(status_code=403, detail="Acceso denegado: Path traversal detectado")
            return target

        if clean_rel == "backups" or clean_rel.startswith("backups/"):
            sub_rel = clean_rel[len("backups"):].lstrip("/")
            candidate = settings.backups_dir / sub_rel
            if candidate.is_symlink():
                raise HTTPException(status_code=403, detail="Acceso denegado: enlaces simbólicos no permitidos")
            target = candidate.resolve()
            if not is_subpath(target, settings.backups_dir):
                raise HTTPException(status_code=403, detail="Acceso denegado: Path traversal detectado")
            return target

        candidate = self.base_dir / clean_rel
        if candidate.is_symlink():
            raise HTTPException(status_code=403, detail="Acceso denegado: enlaces simbólicos no permitidos")
        target = candidate.resolve()
        if not is_subpath(target, self.base_dir):
            raise HTTPException(status_code=403, detail="Acceso denegado: Path traversal detectado")
        return target

    def resolve_download(self, relative_path: str) -> Path:
        """Resuelve un archivo descargable dentro de las raíces permitidas
        y bloquea la descarga de archivos de configuración protegidos."""
        self._assert_not_protected(relative_path)
        safe = self._resolve_safe_path(relative_path)
        self._assert_not_protected(safe.name)
        if not safe.exists() or not safe.is_file():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        return safe

    def list_directory(self, relative_path: str = "") -> Dict[str, Any]:
        target_dir = self._resolve_safe_path(relative_path)
        if not target_dir.exists() or not target_dir.is_dir():
            target_dir.mkdir(parents=True, exist_ok=True)

        items: List[Dict[str, Any]] = []
        try:
            for entry in os.scandir(target_dir):
                if entry.name in PROTECTED_FILES or entry.is_symlink():
                    continue
                stat_res = entry.stat()
                items.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": stat_res.st_size if entry.is_file() else 0,
                    "modified": int(stat_res.st_mtime),
                    "extension": entry.name.split(".")[-1].lower() if "." in entry.name and not entry.is_dir() else ""
                })
        except PermissionError:
            raise HTTPException(status_code=403, detail="Permiso denegado")

        # Agregar accesos directos virtuales en la raíz si existen
        clean_rel = (relative_path or "").replace("\\", "/").strip("/")
        if not clean_rel:
            existing_names = {i["name"] for i in items}
            if "clusters" not in existing_names and settings.cluster_dir.exists():
                try:
                    mtime = int(settings.cluster_dir.stat().st_mtime)
                except Exception:
                    mtime = int(time.time())
                items.append({
                    "name": "clusters",
                    "is_dir": True,
                    "size": 0,
                    "modified": mtime,
                    "extension": ""
                })
            if "backups" not in existing_names and settings.backups_dir.exists():
                try:
                    mtime = int(settings.backups_dir.stat().st_mtime)
                except Exception:
                    mtime = int(time.time())
                items.append({
                    "name": "backups",
                    "is_dir": True,
                    "size": 0,
                    "modified": mtime,
                    "extension": ""
                })

        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

        # Calcular rel_str adecuado para la raíz y carpetas especiales
        try:
            if is_subpath(target_dir, settings.cluster_dir):
                if target_dir.resolve() == settings.cluster_dir.resolve():
                    rel_str = "clusters"
                else:
                    rel_str = "clusters/" + str(target_dir.resolve().relative_to(settings.cluster_dir.resolve())).replace("\\", "/")
            elif is_subpath(target_dir, settings.backups_dir):
                if target_dir.resolve() == settings.backups_dir.resolve():
                    rel_str = "backups"
                else:
                    rel_str = "backups/" + str(target_dir.resolve().relative_to(settings.backups_dir.resolve())).replace("\\", "/")
            else:
                rel_str = str(target_dir.resolve().relative_to(self.base_dir.resolve())).replace("\\", "/")
                if rel_str == ".":
                    rel_str = ""
        except Exception:
            rel_str = clean_rel

        return {
            "current_path": rel_str,
            "items": items
        }

    def read_file(self, relative_path: str) -> Dict[str, Any]:
        self._assert_not_protected(relative_path)
        target = self._resolve_safe_path(relative_path)
        self._assert_not_protected(target.name)
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")

        if target.stat().st_size > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Archivo demasiado grande para el editor web (>10MB)")

        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {
                "path": relative_path,
                "content": content,
                "size": target.stat().st_size
            }
        except Exception as e:
            _raise_internal_error("leer el archivo", e)

    def write_file(self, relative_path: str, content: str) -> Dict[str, Any]:
        self._assert_not_protected(relative_path)
        target = self._resolve_safe_path(relative_path)
        self._assert_not_protected(target.name)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(target, content)
            return {"status": "saved", "path": relative_path, "size": len(content)}
        except Exception as e:
            _raise_internal_error("escribir el archivo", e)

    def create_file(self, relative_path: str) -> Dict[str, Any]:
        self._assert_not_protected(relative_path)
        target = self._resolve_safe_path(relative_path)
        self._assert_not_protected(target.name)
        if target.exists():
            raise HTTPException(status_code=400, detail="El archivo ya existe")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(target, "")
            return {"status": "created", "path": relative_path}
        except Exception as e:
            _raise_internal_error("crear el archivo", e)

    def create_folder(self, relative_path: str) -> Dict[str, Any]:
        self._assert_not_protected(relative_path)
        target = self._resolve_safe_path(relative_path)
        self._assert_not_protected(target.name)
        if target.exists():
            raise HTTPException(status_code=400, detail="La carpeta ya existe")
        try:
            target.mkdir(parents=True, exist_ok=True)
            return {"status": "created", "path": relative_path}
        except Exception as e:
            _raise_internal_error("crear la carpeta", e)

    def delete_item(self, relative_path: str) -> Dict[str, Any]:
        self._assert_not_protected(relative_path)
        target = self._resolve_safe_path(relative_path)
        self._assert_not_protected(target.name)
        if not target.exists():
            raise HTTPException(status_code=404, detail="Elemento no encontrado")

        if self._is_special_root(target):
            raise HTTPException(status_code=400, detail="No se puede eliminar una carpeta raíz (servidor, clusters o backups)")

        try:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            invalidate_dir_size_cache(target.parent)
            return {"status": "deleted", "path": relative_path}
        except Exception as e:
            _raise_internal_error("eliminar el elemento", e)

    async def save_upload(self, relative_dir: str, file: UploadFile) -> Dict[str, Any]:
        target_dir = self._resolve_safe_path(relative_dir)
        if not target_dir.is_dir():
            raise HTTPException(status_code=400, detail="La ruta de destino no es un directorio")

        raw_name = file.filename or "upload"
        self._assert_not_protected(raw_name)
        safe_name = Path(raw_name).name
        safe_name = re.sub(r'[^\w.\-]', '_', safe_name).lstrip('.')
        if not safe_name:
            safe_name = "upload"
        self._assert_not_protected(safe_name)

        dest_file = target_dir / safe_name
        if dest_file.is_symlink():
            raise HTTPException(status_code=403, detail="No se permite sobrescribir enlaces simbólicos")

        written = 0
        try:
            with open(dest_file, "wb") as f:
                while True:
                    chunk = await file.read(UPLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_UPLOAD_BYTES:
                        raise HTTPException(
                            status_code=413,
                            detail="El archivo excede el tamaño máximo permitido de subida"
                        )
                    self._check_storage_quota(written)
                    f.write(chunk)
            invalidate_dir_size_cache(target_dir)
            return {
                "status": "uploaded",
                "filename": safe_name,
                "size": dest_file.stat().st_size
            }
        except HTTPException:
            if dest_file.exists():
                try:
                    dest_file.unlink()
                except OSError:
                    pass
            raise
        except Exception as e:
            if dest_file.exists():
                try:
                    dest_file.unlink()
                except OSError:
                    pass
            _raise_internal_error("guardar el archivo subido", e)
        finally:
            await file.close()

    def extract_zip(self, relative_zip_path: str, target_relative_dir: str = "") -> Dict[str, Any]:
        self._assert_not_protected(relative_zip_path)
        zip_path = self._resolve_safe_path(relative_zip_path)
        dest_dir = self._resolve_safe_path(target_relative_dir)
        dest_resolved = dest_dir.resolve()

        if not zip_path.exists() or not zipfile.is_zipfile(zip_path):
            raise HTTPException(status_code=400, detail="Archivo ZIP inválido o corrupto")

        total_declared_uncompressed = 0
        with zipfile.ZipFile(zip_path, "r") as zf:
            infos = zf.infolist()
            for info in infos:
                # 1. Detectar symlinks en atributos UNIX del ZIP
                unix_mode = (info.external_attr >> 16) & 0o170000
                if unix_mode == stat.S_IFLNK:
                    raise HTTPException(status_code=400, detail="El ZIP contiene enlaces simbólicos no permitidos")

                # 2. Validar contra ZipSlip y archivos protegidos
                if info.filename.startswith("/") or info.filename.startswith("\\") or ".." in Path(info.filename).parts:
                    raise HTTPException(status_code=400, detail="El ZIP contiene rutas inseguras (ZipSlip)")
                member_path = (dest_resolved / info.filename).resolve()
                if not member_path.is_relative_to(dest_resolved):
                    raise HTTPException(status_code=400, detail="El ZIP contiene rutas inseguras (ZipSlip)")

                self._assert_not_protected(info.filename)

                # 3. Validar contra Zip Bomb por cabeceras
                if info.compress_size > 0:
                    ratio = info.file_size / info.compress_size
                    if ratio > MAX_ZIP_COMPRESSION_RATIO:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Ratio de compresión excesivo ({int(ratio)}:1) detectado (Zip Bomb)"
                        )
                elif info.file_size > 0 and not info.is_dir():
                    raise HTTPException(status_code=400, detail="Cabecera de archivo comprimido inválida en ZIP")

                total_declared_uncompressed += max(0, info.file_size)
                if total_declared_uncompressed > MAX_ZIP_UNCOMPRESSED_BYTES:
                    raise HTTPException(
                        status_code=400,
                        detail="El tamaño total descomprimido del ZIP excede el límite de seguridad"
                    )

            self._check_storage_quota(total_declared_uncompressed)

            # 4. Extracción controlada por bloques verificando bytes reales escritos
            total_written = 0
            for info in infos:
                target_path = (dest_resolved / info.filename).resolve()
                if info.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                    continue

                target_path.parent.mkdir(parents=True, exist_ok=True)
                entry_written = 0
                with zf.open(info, "r") as src, open(target_path, "wb") as dst:
                    while True:
                        chunk = src.read(UPLOAD_CHUNK_SIZE)
                        if not chunk:
                            break
                        entry_written += len(chunk)
                        total_written += len(chunk)
                        if total_written > MAX_ZIP_UNCOMPRESSED_BYTES:
                            dst.close()
                            target_path.unlink(missing_ok=True)
                            raise HTTPException(
                                status_code=400,
                                detail="Límite de extracción superado durante lectura real (Zip Bomb)"
                            )
                        if info.compress_size > 0 and (entry_written / info.compress_size) > MAX_ZIP_COMPRESSION_RATIO:
                            dst.close()
                            target_path.unlink(missing_ok=True)
                            raise HTTPException(
                                status_code=400,
                                detail="Ratio real de descompresión excede el límite de seguridad (Zip Bomb)"
                            )
                        dst.write(chunk)

        invalidate_dir_size_cache(dest_resolved)
        return {"status": "extracted", "path": relative_zip_path}

    def rename_item(self, relative_path: str, new_name: str) -> Dict[str, Any]:
        self._assert_not_protected(relative_path)
        raw_name = (new_name or "").strip()
        if not raw_name or "/" in raw_name or "\\" in raw_name or ".." in raw_name:
            raise HTTPException(status_code=400, detail="Nombre inválido o caracteres no permitidos")
        clean_new = Path(raw_name).name
        self._assert_not_protected(clean_new)

        target = self._resolve_safe_path(relative_path)
        self._assert_not_protected(target.name)
        if not target.exists():
            raise HTTPException(status_code=404, detail="Elemento no encontrado")

        if self._is_special_root(target):
            raise HTTPException(status_code=400, detail="No se puede renombrar una carpeta raíz (servidor, clusters o backups)")

        dest = target.parent / clean_new
        allowed = any(
            is_subpath(dest, r)
            for r in (self.base_dir, settings.cluster_dir, settings.backups_dir)
        )
        if not allowed:
            raise HTTPException(status_code=403, detail="Ruta de destino no válida")

        if dest.exists():
            raise HTTPException(status_code=400, detail=f"Ya existe un elemento llamado '{clean_new}'")

        target.rename(dest)
        rel_dest = self._rel_to_root(dest)
        return {"status": "renamed", "old_path": relative_path, "new_path": rel_dest, "name": clean_new}

    def duplicate_item(self, relative_path: str) -> Dict[str, Any]:
        self._assert_not_protected(relative_path)
        target = self._resolve_safe_path(relative_path)
        self._assert_not_protected(target.name)
        if not target.exists():
            raise HTTPException(status_code=404, detail="Elemento no encontrado")

        if self._is_special_root(target):
            raise HTTPException(status_code=400, detail="No se puede duplicar una carpeta raíz (servidor, clusters o backups)")

        parent = target.parent
        if target.is_file():
            stem = target.stem
            suffix = target.suffix
            candidate = f"{stem}.copy{suffix}"
            idx = 1
            while (parent / candidate).exists():
                candidate = f"{stem}.copy_{idx}{suffix}"
                idx += 1
            dest = parent / candidate
            shutil.copy2(target, dest)
        else:
            name = target.name
            candidate = f"{name}.copy"
            idx = 1
            while (parent / candidate).exists():
                candidate = f"{name}.copy_{idx}"
                idx += 1
            dest = parent / candidate
            shutil.copytree(target, dest, symlinks=False, ignore=shutil.ignore_patterns(*PROTECTED_FILES))

        invalidate_dir_size_cache(parent)
        rel_dest = self._rel_to_root(dest)
        return {"status": "duplicated", "old_path": relative_path, "new_path": rel_dest, "new_name": dest.name}

    def compress_item(self, relative_path: str) -> Dict[str, Any]:
        self._assert_not_protected(relative_path)
        target = self._resolve_safe_path(relative_path)
        self._assert_not_protected(target.name)
        if not target.exists():
            raise HTTPException(status_code=404, detail="Elemento no encontrado")

        if self._is_special_root(target):
            raise HTTPException(status_code=400, detail="No se puede comprimir una carpeta raíz (servidor, clusters o backups)")

        parent = target.parent
        zip_name = f"{target.name}.zip"
        zip_path = parent / zip_name
        idx = 1
        while zip_path.exists():
            zip_name = f"{target.name}_{idx}.zip"
            zip_path = parent / zip_name
            idx += 1

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            if target.is_file():
                zf.write(target, arcname=target.name)
            else:
                for root, _, files in os.walk(target):
                    for f in files:
                        if f in PROTECTED_FILES:
                            continue
                        full = Path(root) / f
                        if full.is_symlink():
                            continue
                        arc = full.relative_to(target.parent)
                        zf.write(full, arcname=str(arc))

        invalidate_dir_size_cache(parent)
        rel_dest = self._rel_to_root(zip_path)
        return {"status": "compressed", "path": rel_dest, "filename": zip_name, "archive_name": zip_name}


file_manager = FileManager()
