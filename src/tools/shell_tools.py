import re
from typing import Any, Dict, Optional
from src.runners.rish_runner import rish_runner
from src.errors import MCPError, ErrorCode
from src.config import config

def is_safe_command(command: str) -> bool:
    # Check denied patterns
    for pattern in config.denied_shell_patterns:
        if pattern in command:
            return False
    
    # Check whitelist (if not empty)
    if config.allowed_shell_patterns:
        matched = False
        for pattern in config.allowed_shell_patterns:
            if re.search(pattern, command):
                matched = True
                break
        if not matched:
            return False
            
    return True

async def shell_readonly(command: str) -> Dict[str, Any]:
    """Runs a read-only shell command via rish."""
    # List of common readonly commands
    readonly_whitelist = [
        r"^pm list packages",
        r"^getprop",
        r"^settings get",
        r"^dumpsys",
        r"^cmd package resolve-activity",
        r"^ls",
        r"^cat",
        r"^df",
        r"^uptime"
    ]
    
    matched = False
    for pattern in readonly_whitelist:
        if re.search(pattern, command):
            matched = True
            break
            
    if not matched:
         raise MCPError(ErrorCode.TOOL_DISABLED, f"Command '{command}' is not in the read-only whitelist.")

    if not is_safe_command(command):
        raise MCPError(ErrorCode.TOOL_DISABLED, f"Command '{command}' contains denied patterns.")

    rc, stdout, stderr = await rish_runner.run_rish(command)
    return {"ok": True, "data": {"exit_code": rc, "stdout": stdout, "stderr": stderr}}

async def shell_privileged(command: str, confirm_dangerous: bool = False) -> Dict[str, Any]:
    """Runs a privileged shell command via rish. Requires explicit confirmation."""
    if not config.enable_raw_shell:
        raise MCPError(ErrorCode.TOOL_DISABLED, "Privileged shell is disabled in configuration.")
    
    if not confirm_dangerous:
        raise MCPError(ErrorCode.INVALID_ARGUMENT, "confirm_dangerous=true is required for privileged shell.")
    
    if not is_safe_command(command):
        raise MCPError(ErrorCode.TOOL_DISABLED, f"Command '{command}' contains denied patterns.")
    
    rc, stdout, stderr = await rish_runner.run_rish(command)
    return {"ok": True, "data": {"exit_code": rc, "stdout": stdout, "stderr": stderr}}
