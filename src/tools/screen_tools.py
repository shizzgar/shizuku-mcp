import asyncio
from typing import Any, Dict, Optional
from src.runners.rish_runner import rish_runner
from src.errors import MCPError, ErrorCode
from src.artifacts import get_new_artifact_path, get_metadata
from src.config import config

async def take_screenshot() -> Dict[str, Any]:
    """Takes a screenshot and saves it as an artifact."""
    path = get_new_artifact_path("screenshot", ".png")
    # rish screencap -p <path>
    # Note: screencap path must be accessible by Shizuku. 
    # Usually /sdcard/ is accessible. 
    # But we want to save it in artifacts dir which is in Termux home.
    # Shizuku/rish might not have permission to write directly to Termux home.
    # We should save to /sdcard/ and then move it, or try writing directly.
    
    # Try writing to /sdcard/ first as it's more reliable for screencap
    temp_path = f"/sdcard/mcp_screenshot_{int(asyncio.get_event_loop().time())}.png"
    rc, stdout, stderr = await rish_runner.run_rish(f"screencap -p {temp_path}")
    if rc != 0:
        raise MCPError(ErrorCode.COMMAND_FAILED, f"Failed to take screenshot: {stderr}")
    
    # Move from /sdcard/ to artifacts using binary cat
    rc, stdout_bytes, stderr_bytes = await rish_runner.run_rish_binary(f"cat {temp_path}")
    if rc == 0:
        with open(path, "wb") as f:
            f.write(stdout_bytes)
    else:
        raise MCPError(ErrorCode.COMMAND_FAILED, f"Failed to transfer screenshot: {stderr_bytes.decode()}")
        
    # Cleanup temp
    await rish_runner.run_rish(f"rm {temp_path}")
    
    return {"ok": True, "data": get_metadata(str(path))}

async def record_screen(duration_sec: int = 10) -> Dict[str, Any]:
    """Records the screen for a specified duration."""
    if not config.allow_screenrecord:
        raise MCPError(ErrorCode.TOOL_DISABLED, "screenrecord is disabled.")
    
    path = get_new_artifact_path("screenrecord", ".mp4")
    temp_path = f"/sdcard/mcp_record_{int(asyncio.get_event_loop().time())}.mp4"
    
    # screenrecord --time-limit <sec> <path>
    rc, stdout, stderr = await rish_runner.run_rish(f"screenrecord --time-limit {duration_sec} {temp_path}")
    if rc != 0:
        raise MCPError(ErrorCode.COMMAND_FAILED, f"Failed to record screen: {stderr}")
    
    # Move to artifacts
    rc, stdout_bytes, stderr_bytes = await rish_runner.run_rish_binary(f"cat {temp_path}")
    if rc == 0:
        with open(path, "wb") as f:
            f.write(stdout_bytes)
    else:
        raise MCPError(ErrorCode.COMMAND_FAILED, f"Failed to transfer recording: {stderr_bytes.decode()}")

    await rish_runner.run_rish(f"rm {temp_path}")
    
    return {"ok": True, "data": get_metadata(str(path))}
