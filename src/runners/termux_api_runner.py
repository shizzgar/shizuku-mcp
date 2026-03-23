import shutil
from typing import List, Optional, Tuple
from src.errors import MCPError, ErrorCode
from src.runners.subprocess_runner import run_command

class TermuxApiRunner:
    def __init__(self):
        self._initialized = False
        self._available = False

    async def _check_availability(self):
        if self._initialized:
            return self._available
        
        # Check if any termux-api command exists
        self._available = shutil.which("termux-api-check") is not None or shutil.which("termux-clipboard-get") is not None
        self._initialized = True
        return self._available

    async def run_api(
        self, 
        command_args: List[str], 
        timeout: Optional[int] = None
    ) -> Tuple[int, str, str]:
        if not await self._check_availability():
            raise MCPError(ErrorCode.TERMUX_API_NOT_AVAILABLE, "Termux:API not found in PATH.")
        
        # All termux-api commands start with termux-
        return await run_command(command_args, timeout=timeout)

termux_api_runner = TermuxApiRunner()
