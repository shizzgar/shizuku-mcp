import json
import logging
from typing import Any, Dict, List, Optional
from src.runners.subprocess_runner import run_command
from src.errors import MCPError, ErrorCode
from src.config import config

logger = logging.getLogger("android-shizuku-mcp")

async def run_mega_termux_command(command: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Универсальная обертка для любых termux-* команд.
    Если command не начинается с 'termux-', мы добавляем этот префикс.
    """
    if not command.startswith("termux-"):
        command = f"termux-{command}"
        
    cmd_args = [command]
    if args:
        cmd_args.extend(args)
        
    # Некоторые команды могут "висеть" (например, чтение сенсоров без -n 1), 
    # поэтому таймаут обязателен.
    try:
        # Для Termux окружения нужно быть уверенным, что PATH прокинут корректно
        import os
        env = os.environ.copy()
        termux_bin = "/data/data/com.termux/files/usr/bin"
        if termux_bin not in env.get("PATH", ""):
            env["PATH"] = f"{termux_bin}:{env.get('PATH', '')}"
            
        rc, stdout, stderr = await run_command(cmd_args, env=env)
        
        if rc != 0:
            raise MCPError(ErrorCode.COMMAND_FAILED, f"Command failed: {stderr or stdout}")
            
        # Пытаемся распарсить JSON, так как большинство termux-api команд возвращают именно его
        try:
            parsed_data = json.loads(stdout)
            return {"ok": True, "data": parsed_data}
        except json.JSONDecodeError:
            # Если это не JSON, возвращаем как обычный текст
            return {"ok": True, "data": {"output": stdout}}
            
    except MCPError:
        raise
    except Exception as e:
        raise MCPError(ErrorCode.INTERNAL_ERROR, f"Failed to execute {command}: {str(e)}")
