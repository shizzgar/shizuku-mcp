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

async def shell_readonly(command: str) -> Dict[str, Any]:
    """Runs a shell command via Shizuku (System context)."""
    if not config.enable_raw_shell:
        # Whitelist logic...
        pass
    
    if not is_safe_command(command):
        raise MCPError(ErrorCode.TOOL_DISABLED, f"Command contains denied patterns.")

    rc, stdout, stderr = await rish_runner.run_rish(command)
    return {"ok": True, "data": {"exit_code": rc, "stdout": stdout, "stderr": stderr}}

async def shell_privileged(command: str, confirm_dangerous: bool = True) -> Dict[str, Any]:
    """Runs a shell command via Shizuku (System context)."""
    if not config.enable_raw_shell:
        raise MCPError(ErrorCode.TOOL_DISABLED, "Privileged shell is disabled.")
    
    rc, stdout, stderr = await rish_runner.run_rish(command)
    return {"ok": True, "data": {"exit_code": rc, "stdout": stdout, "stderr": stderr}}

async def shell_termux(command: str) -> Dict[str, Any]:
    """Runs a shell command directly in Termux context (access to ~/ and pkg)."""
    if not is_safe_command(command):
        raise MCPError(ErrorCode.TOOL_DISABLED, f"Command contains denied patterns.")

    # Используем прямой запуск через bash, чтобы работали алиасы и пути Termux
    rc, stdout, stderr = await run_command(["/data/data/com.termux/files/usr/bin/bash", "-c", command])
    return {"ok": True, "data": {"exit_code": rc, "stdout": stdout, "stderr": stderr}}
