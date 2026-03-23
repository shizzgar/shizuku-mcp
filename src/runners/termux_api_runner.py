import shutil
import os
import logging
from typing import List, Optional, Tuple
from src.errors import MCPError, ErrorCode
from src.runners.subprocess_runner import run_command

logger = logging.getLogger("android-shizuku-mcp")

class TermuxApiRunner:
    def __init__(self):
        self._initialized = False
        self._available = False

    async def _check_availability(self):
        if self._initialized:
            return self._available
        
        # Проверяем через PATH
        check_bin = shutil.which("termux-api-check") or shutil.which("termux-battery-status")
        
        # Если не нашли, проверяем прямой путь (хардкод для Termux)
        if not check_bin:
            direct_path = "/data/data/com.termux/files/usr/bin/termux-battery-status"
            if os.path.exists(direct_path):
                check_bin = direct_path

        self._available = check_bin is not None
        if self._available:
            logger.info(f"Termux:API detected via: {check_bin}")
        else:
            logger.warning("Termux:API NOT DETECTED! Ensure 'pkg install termux-api' was run.")
            
        self._initialized = True
        return self._available

    async def run_api(self, command_args: List[str], timeout: Optional[int] = None) -> Tuple[int, str, str]:
        if not await self._check_availability():
            raise MCPError(ErrorCode.TERMUX_API_NOT_AVAILABLE, "Termux:API not found. Run 'pkg install termux-api' in Termux.")
        
        return await run_command(command_args, timeout=timeout)

termux_api_runner = TermuxApiRunner()
