from typing import Any, Dict, Optional
from src.runners.rish_runner import rish_runner
from src.errors import MCPError, ErrorCode
from src.config import config

async def list_packages(
    third_party_only: bool = True, 
    filter_str: Optional[str] = None
) -> Dict[str, Any]:
    """Lists installed Android packages."""
    cmd = "pm list packages"
    if third_party_only:
        cmd += " -3"
    if filter_str:
        cmd += f" {filter_str}"
    
    rc, stdout, stderr = await rish_runner.run_rish(cmd)
    if rc != 0:
        raise MCPError(ErrorCode.COMMAND_FAILED, f"Failed to list packages: {stderr}")
    
    packages = [line.split(":", 1)[1] if ":" in line else line for line in stdout.splitlines() if line.strip()]
    return {"ok": True, "data": {"packages": packages}}

async def open_app(package_name: str) -> Dict[str, Any]:
    """Opens an application by package name."""
    # Use monkey to start the main activity of the package
    # monkey -p <package> -c android.intent.category.LAUNCHER 1
    rc, stdout, stderr = await rish_runner.run_rish(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
    if rc != 0:
        # Sometimes monkey fails if it's not a launcher app. 
        # Fallback to 'am start' if we can find the activity, but monkey is easier for generic open.
        raise MCPError(ErrorCode.COMMAND_FAILED, f"Failed to open app {package_name}: {stderr}")
    
    return {"ok": True, "data": {"package_name": package_name, "launched": True}}

async def force_stop(package_name: str) -> Dict[str, Any]:
    """Force stops an application."""
    if not config.allow_package_force_stop:
        raise MCPError(ErrorCode.TOOL_DISABLED, "force_stop is disabled in configuration.")
    
    rc, stdout, stderr = await rish_runner.run_rish(f"am force-stop {package_name}")
    if rc != 0:
        raise MCPError(ErrorCode.COMMAND_FAILED, f"Failed to force stop {package_name}: {stderr}")
    
    return {"ok": True, "data": {"package_name": package_name, "stopped": True}}
