import re
import logging
from typing import Any, Dict, Optional
from src.runners.rish_runner import rish_runner
from src.runners.subprocess_runner import run_command
from src.errors import MCPError, ErrorCode
from src.config import config

logger = logging.getLogger("android-shizuku-mcp")

def is_safe_command(command: str) -> bool:
    if config.enable_raw_shell:
        return True
    for pattern in config.denied_shell_patterns:
        if pattern in command:
            return False
    return True

async def system_shell(command: str) -> Dict[str, Any]:
    """Runs a shell command via Shizuku (System context, ADB user).
    Access to: pm, am, settings, dumpsys, and all Android system utilities.
    """
    if not is_safe_command(command):
        raise MCPError(ErrorCode.TOOL_DISABLED, f"Command contains denied patterns.")

    rc, stdout, stderr = await rish_runner.run_rish(command)
    return {"ok": True, "data": {"exit_code": rc, "stdout": stdout, "stderr": stderr}}

async def termux_shell(command: str) -> Dict[str, Any]:
    """Runs a shell command directly in Termux context (Termux user).
    Access to: pkg, apt, python, git, and files in Termux home directory.
    """
    if not is_safe_command(command):
        raise MCPError(ErrorCode.TOOL_DISABLED, f"Command contains denied patterns.")

    # Используем bash для доступа к окружению Termux
    rc, stdout, stderr = await run_command(["/data/data/com.termux/files/usr/bin/bash", "-c", command])
    return {"ok": True, "data": {"exit_code": rc, "stdout": stdout, "stderr": stderr}}
