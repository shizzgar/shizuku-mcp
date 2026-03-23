import os
import time
from pathlib import Path
from typing import List, Dict, Any
from src.config import config

def get_artifact_path(name: str) -> Path:
    return config.artifacts_dir / name

def list_artifacts() -> List[Dict[str, Any]]:
    artifacts = []
    for p in config.artifacts_dir.glob("*"):
        if p.is_file():
            stat = p.stat()
            artifacts.append({
                "name": p.name,
                "path": str(p.absolute()),
                "size": stat.st_size,
                "timestamp": stat.st_mtime
            })
    return artifacts

def get_new_artifact_path(prefix: str, suffix: str) -> Path:
    timestamp = int(time.time())
    name = f"{prefix}_{timestamp}{suffix}"
    return get_artifact_path(name)

def get_metadata(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    stat = p.stat()
    return {
        "name": p.name,
        "path": str(p.absolute()),
        "size": stat.st_size,
        "timestamp": stat.st_mtime
    }
