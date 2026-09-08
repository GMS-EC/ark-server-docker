import os
import re
import shutil
import time
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, UploadFile

from app.config import settings
from app.core.fs_utils import atomic_write_text

class FileManager:
    """
    Gestor de archivos completo y seguro para ARK Server Manager.
    Previene vulnerabilidades de Path Traversal verificando que todas las operaciones
    se restrinjan estrictamente a settings.ark_data_dir.
    Soporta navegación, creación, edición, renombrado, duplicación, subida,
    descarga, compresión y descompresión de archivos ZIP.
    """
    def __init__(self):
        self.base_dir: Path = settings.ark_data_dir

    def _is_subpath(self, path: Path, parent: Path) -> bool:
        try:
            path.resolve().relative_to(parent.resolve())
            return True
        except (ValueError, AttributeError):
            return False

    def _resolve_safe_path(self, relative_path: str = "") -> Path:
        clean_rel = (relative_path or "").replace("\\", "/").strip("/")
        
        # Acceso transparente a carpetas especiales compartidas: clusters y backups
        if clean_rel == "clusters" or clean_rel.startswith("clusters/"):
            sub_rel = clean_rel[len("clusters"):].lstrip("/")
            target = (settings.cluster_dir / sub_rel).resolve()
            if not self._is_subpath(target, settings.cluster_dir):
                raise HTTPException(status_code=403, detail="Acceso denegado: Path traversal detectado")
            return target

        if clean_rel == "backups" or clean_rel.startswith("backups/"):
            sub_rel = clean_rel[len("backups"):].lstrip("/")
            target = (settings.backups_dir / sub_rel).resolve()
            if not self._is_subpath(target, settings.backups_dir):
                raise HTTPException(status_code=403, detail="Acceso denegado: Path traversal detectado")
            return target

        target = (self.base_dir / clean_rel).resolve()
        if not self._is_subpath(target, self.base_dir):
            raise HTTPException(status_code=403, detail="Acceso denegado: Path traversal detectado")
        return target

    def list_directory(self, relative_path: str = "") -> Dict[str, Any]:
        target_dir = self._resolve_safe_path(relative_path)
        if not target_dir.exists() or not target_dir.is_dir():
            target_dir.mkdir(parents=True, exist_ok=True)

        items: List[Dict[str, Any]] = []
        try:
            for entry in os.scandir(target_dir):
                stat = entry.stat()
                items.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": stat.st_size if entry.is_file() else 0,
                    "modified": int(stat.st_mtime),
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
        if self._is_subpath(target_dir, settings.cluster_dir):
            if target_dir.resolve() == settings.cluster_dir.resolve():
                rel_str = "clusters"
            else:
                rel_str = "clusters/" + str(target_dir.resolve().relative_to(settings.cluster_dir.resolve())).replace("\\", "/")
        elif self._is_subpath(target_dir, settings.backups_dir):
            if target_dir.resolve() == settings.backups_dir.resolve():
                rel_str = "backups"
            else:
                rel_str = "backups/" + str(target_dir.resolve().relative_to(settings.backups_dir.resolve())).replace("\\", "/")
        else:
            rel_str = str(target_dir.relative_to(self.base_dir.resolve())).replace("\\", "/")
            if rel_str == ".":
                rel_str = ""

        return {
            "current_path": rel_str,
            "items": items
        }

    def read_file(self, relative_path: str) -> Dict[str, Any]:
        target = self._resolve_safe_path(relative_path)
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
            raise HTTPException(status_code=500, detail=f"Error al leer archivo: {str(e)}")

    def write_file(self, relative_path: str, content: str) -> Dict[str, Any]:
        target = self._resolve_safe_path(relative_path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(target, content)
            return {"status": "saved", "path": relative_path, "size": len(content)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al escribir archivo: {str(e)}")

    def create_file(self, relative_path: str) -> Dict[str, Any]:
        target = self._resolve_safe_path(relative_path)
        if target.exists():
            raise HTTPException(status_code=400, detail="El archivo ya existe")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(target, "")
            return {"status": "created", "path": relative_path}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al crear archivo: {str(e)}")

    def create_folder(self, relative_path: str) -> Dict[str, Any]:
        target = self._resolve_safe_path(relative_path)
        if target.exists():
            raise HTTPException(status_code=400, detail="La carpeta ya existe")
        try:
            target.mkdir(parents=True, exist_ok=True)
            return {"status": "created", "path": relative_path}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al crear carpeta: {str(e)}")

    def delete_item(self, relative_path: str) -> Dict[str, Any]:
        target = self._resolve_safe_path(relative_path)
        if not target.exists():
            raise HTTPException(status_code=404, detail="Elemento no encontrado")

        if target == self.base_dir:
            raise HTTPException(status_code=400, detail="No se puede eliminar la raíz del servidor")

        try:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            return {"status": "deleted", "path": relative_path}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al eliminar: {str(e)}")

    async def save_upload(self, relative_dir: str, file: UploadFile) -> Dict[str, Any]:
        target_dir = self._resolve_safe_path(relative_dir)
        if not target_dir.is_dir():
            raise HTTPException(status_code=400, detail="La ruta de destino no es un directorio")

        raw_name = file.filename or "upload"
        safe_name = Path(raw_name).name
        safe_name = re.sub(r'[^\w.\-]', '_', safe_name).lstrip('.')
        if not safe_name:
            safe_name = "upload"

        dest_file = target_dir / safe_name
        try:
            with open(dest_file, "wb") as f:
                shutil.copyfileobj(file.file, f)
            return {
                "status": "uploaded",
                "filename": safe_name,
                "size": dest_file.stat().st_size
            }
        finally:
            await file.close()

    def extract_zip(self, relative_zip_path: str, target_relative_dir: str = "") -> Dict[str, Any]:
        zip_path = self._resolve_safe_path(relative_zip_path)
        dest_dir = self._resolve_safe_path(target_relative_dir)

        if not zip_path.exists() or not zipfile.is_zipfile(zip_path):
            raise HTTPException(status_code=400, detail="Archivo ZIP inválido o corrupto")

        with zipfile.ZipFile(zip_path, 'r') as zf:
            for member in zf.namelist():
                member_path = (dest_dir / member).resolve()
                if not member_path.is_relative_to(dest_dir):
                    raise HTTPException(status_code=400, detail="El ZIP contiene rutas inseguras (ZipSlip)")
            zf.extractall(dest_dir)

        return {"status": "extracted", "path": relative_zip_path}

    def rename_item(self, relative_path: str, new_name: str) -> Dict[str, Any]:
        raw_name = (new_name or "").strip()
        if not raw_name or "/" in raw_name or "\\" in raw_name or ".." in raw_name:
            raise HTTPException(status_code=400, detail="Nombre inválido o caracteres no permitidos")
        clean_new = Path(raw_name).name

        target = self._resolve_safe_path(relative_path)
        if not target.exists():
            raise HTTPException(status_code=404, detail="Elemento no encontrado")

        if target == self.base_dir:
            raise HTTPException(status_code=400, detail="No se puede renombrar el directorio raíz")

        dest = target.parent / clean_new
        if not dest.resolve().is_relative_to(self.base_dir.resolve()):
            raise HTTPException(status_code=403, detail="Ruta de destino no válida")

        if dest.exists():
            raise HTTPException(status_code=400, detail=f"Ya existe un elemento llamado '{clean_new}'")

        target.rename(dest)
        rel_dest = str(dest.relative_to(self.base_dir.resolve())).replace("\\", "/")
        return {"status": "renamed", "old_path": relative_path, "new_path": rel_dest, "name": clean_new}

    def duplicate_item(self, relative_path: str) -> Dict[str, Any]:
        target = self._resolve_safe_path(relative_path)
        if not target.exists():
            raise HTTPException(status_code=404, detail="Elemento no encontrado")

        if target == self.base_dir:
            raise HTTPException(status_code=400, detail="No se puede duplicar el directorio raíz")

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
            shutil.copytree(target, dest)

        rel_dest = str(dest.relative_to(self.base_dir.resolve())).replace("\\", "/")
        return {"status": "duplicated", "old_path": relative_path, "new_path": rel_dest, "new_name": dest.name}

    def compress_item(self, relative_path: str) -> Dict[str, Any]:
        target = self._resolve_safe_path(relative_path)
        if not target.exists():
            raise HTTPException(status_code=404, detail="Elemento no encontrado")

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
                        full = Path(root) / f
                        arc = full.relative_to(target.parent)
                        zf.write(full, arcname=str(arc))

        rel_dest = str(zip_path.relative_to(self.base_dir.resolve())).replace("\\", "/")
        return {"status": "compressed", "path": rel_dest, "filename": zip_name, "archive_name": zip_name}

file_manager = FileManager()
