import asyncio
import logging
import json
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

from src.config import config
from src.tools import shell_tools
from src.artifacts import list_artifacts

# Логирование
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("android-shizuku-mcp")

mcp = FastMCP("android-shizuku-mcp")

# --- TWO POWERFUL SHELL TOOLS ---

@mcp.tool()
async def termux_shell(command: str) -> dict:
    """
    [TERMUX USER CONTEXT] - Direct access to the Termux environment.
    Use this for file management, package management, and hardware interaction via Termux:API.
    
    KEY CAPABILITIES:
    - Filesystem: Access to ~/ (home), pipes (|), redirects (>), and complex bash scripts.
    - Packages: Use 'pkg install <name>' or 'apt' to add new tools. 
    - Installed Tools: python, git, ffmpeg, curl, etc.
    - Hardware (Termux:API): Use 'termux-*' commands for hardware access:
        * battery-status, wifi-connectioninfo, location (GPS)
        * toast, notification, dialog, vibration, torch
        * clipboard-get, clipboard-set
        * camera-photo, microphone-record, media-player
        * sms-list, sms-send, call-log, contact-list
        * saf-ls, saf-read, saf-write (Access to SD Card/Downloads without root)
    
    ENVIRONMENT: Full bash shell with correct PATH, HOME, and PREFIX.
    """
    return await shell_tools.termux_shell(command=command)

@mcp.tool()
async def system_shell(command: str) -> dict:
    """
    [SYSTEM ADB CONTEXT] - High-privilege access via Shizuku (rish).
    Use this for Android OS management, app control, and deep system diagnostics.
    
    KEY CAPABILITIES:
    - App Management: 
        * 'pm list packages' (list apps)
        * 'am start -n <comp>' (launch any activity)
        * 'am force-stop <pkg>' (kill any app)
        * 'pm dump <pkg>' (get app details)
    - System Settings: 'settings get/put global/secure/system <key> <value>'
    - Screen Control: 'screencap -p /sdcard/s.png', 'screenrecord --time-limit 10 /sdcard/v.mp4'
    - Input: 'input tap x y', 'input swype...', 'input keyevent 26' (power)
    - Logs & Debug: 'logcat', 'dumpsys battery/wifi/window', 'top', 'ps'
    
    ENVIRONMENT: Runs as 'shell' user (UID 2000). Use this when Termux shell lacks permissions.
    """
    return await shell_tools.system_shell(command=command)

# --- SERVICE TOOLS ---

@mcp.tool()
async def doctor() -> dict:
    """Provides system diagnostics, Shizuku status, and Termux:API availability."""
    from src.doctor import get_system_info
    return {"ok": True, "data": await get_system_info()}

@mcp.tool()
async def list_artifacts() -> dict:
    """Lists saved files (screenshots, recordings) in the artifacts directory."""
    return {"ok": True, "data": list_artifacts()}

# Middleware
class AuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            logger.info(f"--> {scope['method']} {scope['path']}")
            if config.auth_token and auth_header != f"Bearer {config.auth_token}":
                response = JSONResponse({"error": "Unauthorized"}, status_code=401)
                await response(scope, receive, send)
                return
        async def wrapped_send(message):
            if message["type"] == "http.response.start":
                logger.info(f"<-- Status {message.get('status')}")
            await send(message)
        await self.app(scope, receive, wrapped_send)

def main():
    import uvicorn
    app = mcp.streamable_http_app()
    protected_app = AuthMiddleware(app)
    mcp_url = f"http://{config.host}:{config.port}/mcp"
    mcp_config = {
        "mcpServers": {
          "android-shizuku": {
            "url": mcp_url,
            "headers": { "Authorization": f"Bearer {config.auth_token}" if config.auth_token else "" }
          }
        }
    }
    print("\n" + "="*50)
    print("READY! Only 2 POWERFUL SHELLS are active.")
    print("="*50)
    print(json.dumps(mcp_config, indent=2))
    print("="*50 + "\n")
    config.setup_dirs()
    uvicorn.run(protected_app, host=config.host, port=config.port, log_level="info")

if __name__ == "__main__":
    main()
