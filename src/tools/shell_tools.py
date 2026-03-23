import os
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
    """Runs a shell command via Shizuku (System level)."""
    if not is_safe_command(command):
        raise MCPError(ErrorCode.TOOL_DISABLED, f"Command contains denied patterns.")

    # Выполняем через rish (доступ к ADB пользователю)
    rc, stdout, stderr = await rish_runner.run_rish(command)
    return {"ok": True, "data": {"exit_code": rc, "stdout": stdout, "stderr": stderr}}

async def termux_shell(command: str) -> Dict[str, Any]:
    """Runs a bash command directly in the Termux environment."""
    if not is_safe_command(command):
        raise MCPError(ErrorCode.TOOL_DISABLED, f"Command contains denied patterns.")

    # Подготавливаем окружение Termux
    env = os.environ.copy()
    prefix = "/data/data/com.termux/files/usr"
    env["PATH"] = f"{prefix}/bin:{env.get('PATH', '')}"
    env["LD_LIBRARY_PATH"] = f"{prefix}/lib"
    env["PREFIX"] = prefix
    env["HOME"] = os.path.expanduser("~")

    # Запускаем через bash для поддержки пайпов, алиасов и скриптов
    rc, stdout, stderr = await run_command(["/data/data/com.termux/files/usr/bin/bash", "-c", command], env=env)
    return {"ok": True, "data": {"exit_code": rc, "stdout": stdout, "stderr": stderr}}
