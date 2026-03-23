import os
import logging
from typing import Any, Dict, Optional
from src.runners.subprocess_runner import run_command
from src.errors import MCPError, ErrorCode
from src.config import config

logger = logging.getLogger("android-shizuku-mcp")

def is_safe_command(command: str) -> bool:
    if config.enable_raw_shell:
        return True
    # Базовая защита от совсем уж деструктивных действий в корне системы
    for pattern in config.denied_shell_patterns:
        if pattern in command:
            return False
    return True

async def execute_android_shell(command: str) -> Dict[str, Any]:
    """The core execution engine for the unified Android Shell."""
    if not is_safe_command(command):
        raise MCPError(ErrorCode.TOOL_DISABLED, f"Command contains explicitly denied patterns.")

    # Подготавливаем окружение Termux (бинарники, библиотеки, пути)
    env = os.environ.copy()
    prefix = "/data/data/com.termux/files/usr"
    env["PATH"] = f"{prefix}/bin:{env.get('PATH', '')}"
    env["LD_LIBRARY_PATH"] = f"{prefix}/lib"
    env["PREFIX"] = prefix
    env["HOME"] = os.path.expanduser("~")

    # Запускаем через bash для поддержки всей мощи скриптов
    rc, stdout, stderr = await run_command(["/data/data/com.termux/files/usr/bin/bash", "-c", command], env=env)
    return {"ok": True, "data": {"exit_code": rc, "stdout": stdout, "stderr": stderr}}
