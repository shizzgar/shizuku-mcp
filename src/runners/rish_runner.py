import os
import shutil
import logging
from typing import List, Optional, Tuple
from src.config import config
from src.errors import MCPError, ErrorCode
from src.runners.subprocess_runner import run_command, run_command_binary

logger = logging.getLogger("android-shizuku-mcp")

class RishRunner:
    def __init__(self):
        self._rish_path: Optional[str] = config.rish_path

    async def _find_rish(self) -> str:
        if self._rish_path and os.path.exists(self._rish_path):
            return self._rish_path

        search_paths = [
            os.path.expanduser("~/bin/rish"),
            "/data/data/com.termux/files/usr/bin/rish",
            shutil.which("rish")
        ]

        for path in search_paths:
            if path and os.path.exists(path):
                if os.access(path, os.X_OK):
                    self._rish_path = path
                    return path

        raise MCPError(
            ErrorCode.RISH_NOT_FOUND,
            "rish not found",
            details={"searched_paths": [p for p in search_paths if p]},
            retryable=False,
            suggested_next_action="Install or configure rish in Termux.",
        )

    async def check_shizuku(self) -> bool:
        try:
            path = await self._find_rish()
            # На Android 15 лучше проверять через getprop
            rc, stdout, stderr = await run_command([path, "-c", "getprop rikka.shizuku.mode"], timeout=5)
            return rc == 0
        except Exception:
            return False

    async def run_rish(self, command: str, timeout: Optional[int] = None) -> Tuple[int, str, str]:
        path = await self._find_rish()
        env = os.environ.copy()
        env["RISH_PRESERVE_ENV"] = "0" # Для Android 15 лучше всегда 0
        
        # Оборачиваем команду, чтобы избежать проблем с пайпами
        full_cmd = [path, "-c", command]
        return await run_command(full_cmd, timeout=timeout, env=env)

    async def run_rish_binary(self, command: str, timeout: Optional[int] = None) -> Tuple[int, bytes, bytes]:
        path = await self._find_rish()
        env = os.environ.copy()
        env["RISH_PRESERVE_ENV"] = "0"
        return await run_command_binary([path, "-c", command], timeout=timeout, env=env)

rish_runner = RishRunner()
