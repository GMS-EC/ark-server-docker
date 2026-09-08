import os
import json
import tempfile
from pathlib import Path
from typing import Any

def atomic_write_text(file_path: Path, content: str, encoding: str = "utf-8") -> None:
    """Escribe un archivo de texto atómicamente para prevenir corrupción de archivos."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    dir_name = file_path.parent
    
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding=encoding) as tf:
        tf.write(content)
        temp_name = tf.name
        
    os.replace(temp_name, file_path)

def atomic_write_json(file_path: Path, data: Any, indent: int = 2) -> None:
    """Escribe un archivo JSON atómicamente."""
    content = json.dumps(data, indent=indent, ensure_ascii=False)
    atomic_write_text(file_path, content, encoding="utf-8")
