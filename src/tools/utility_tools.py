from typing import Any, Dict, Optional
from src.runners.termux_api_runner import termux_api_runner
from src.errors import MCPError, ErrorCode

async def clipboard_get() -> Dict[str, Any]:
    """Gets the current clipboard content."""
    rc, stdout, stderr = await termux_api_runner.run_api(["termux-clipboard-get"])
    if rc != 0:
        raise MCPError(ErrorCode.COMMAND_FAILED, f"Failed to get clipboard: {stderr}")
    return {"ok": True, "data": {"text": stdout}}

async def clipboard_set(text: str) -> Dict[str, Any]:
    """Sets the clipboard content."""
    # termux-clipboard-set expects the text to be passed via stdin or as argument
    # Using argument is simpler for small texts
    rc, stdout, stderr = await termux_api_runner.run_api(["termux-clipboard-set", text])
    if rc != 0:
        raise MCPError(ErrorCode.COMMAND_FAILED, f"Failed to set clipboard: {stderr}")
    return {"ok": True, "data": {"success": True}}

async def show_notification(title: str, content: str) -> Dict[str, Any]:
    """Shows an Android notification."""
    rc, stdout, stderr = await termux_api_runner.run_api(["termux-notification", "-t", title, "-c", content])
    if rc != 0:
        raise MCPError(ErrorCode.COMMAND_FAILED, f"Failed to show notification: {stderr}")
    return {"ok": True, "data": {"success": True}}

async def battery_status() -> Dict[str, Any]:
    """Gets the battery status."""
    rc, stdout, stderr = await termux_api_runner.run_api(["termux-battery-status"])
    if rc != 0:
        raise MCPError(ErrorCode.COMMAND_FAILED, f"Failed to get battery status: {stderr}")
    import json
    return {"ok": True, "data": json.loads(stdout)}

async def wifi_status() -> Dict[str, Any]:
    """Gets the WiFi connection status."""
    rc, stdout, stderr = await termux_api_runner.run_api(["termux-wifi-connectioninfo"])
    if rc != 0:
        raise MCPError(ErrorCode.COMMAND_FAILED, f"Failed to get WiFi status: {stderr}")
    import json
    return {"ok": True, "data": json.loads(stdout)}

async def device_info() -> Dict[str, Any]:
    """Gets general device information."""
    rc, stdout, stderr = await termux_api_runner.run_api(["termux-telephony-deviceinfo"])
    if rc != 0:
        # Fallback or partial info if telephony not available
        return {"ok": True, "data": {"info": "Telephony info not available"}}
    import json
    return {"ok": True, "data": json.loads(stdout)}
