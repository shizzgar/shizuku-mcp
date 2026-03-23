import os
import shutil
from typing import List, Optional, Tuple
from src.config import config
from src.errors import MCPError, ErrorCode
from src.runners.subprocess_runner import run_command

class RishRunner:
    def __init__(self):
        self._rish_path: Optional[str] = config.rish_path
        self._initialized = False

    async def _find_rish(self) -> str:
        if self._rish_path:
            if os.path.exists(self._rish_path):
                return self._rish_path
            else:
                raise MCPError(ErrorCode.RISH_NOT_FOUND, f"rish not found at configured path: {self._rish_path}")

        # Common locations in Termux
        search_paths = [
            os.path.expanduser("~/bin/rish"),
            "/data/data/com.termux/files/usr/bin/rish",
            shutil.which("rish")
        ]

        for path in search_paths:
            if path and os.path.exists(path):
                # Check permissions (especially for Android 14+)
                # Shizuku says it shouldn't be writable by others, 
                # but for simplicity we just check if it exists and is executable.
                if os.access(path, os.X_OK):
                    self._rish_path = path
                    return path

        raise MCPError(ErrorCode.RISH_NOT_FOUND, "rish not found in common locations. Please configure it.")

    async def check_shizuku(self) -> bool:
        try:
            path = await self._find_rish()
            # Try a simple command to check if Shizuku is running
            # We use a timeout to avoid hanging if Shizuku is stuck
            rc, stdout, stderr = await run_command([path, "-c", "id"], timeout=5)
            return rc == 0
        except Exception:
            return False

    async def run_rish(
        self, 
        command: str, 
        timeout: Optional[int] = None
    ) -> Tuple[int, str, str]:
        path = await self._find_rish()
        
        env = os.environ.copy()
        env["RISH_PRESERVE_ENV"] = str(config.rish_preserve_env)
        
        return await run_command([path, "-c", command], timeout=timeout, env=env)

    async def run_rish_binary(
        self, 
        command: str, 
        timeout: Optional[int] = None
    ) -> Tuple[int, bytes, bytes]:
        path = await self._find_rish()
        
        env = os.environ.copy()
        env["RISH_PRESERVE_ENV"] = str(config.rish_preserve_env)
        
        from src.runners.subprocess_runner import run_command_binary
        return await run_command_binary([path, "-c", command], timeout=timeout, env=env)

rish_runner = RishRunner()
