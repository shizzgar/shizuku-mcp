import asyncio
import logging
import json
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

from src.config import config
from src.tools import shell_tools
from src.tools.mega_termux_tools import run_mega_termux_command
from src.artifacts import list_artifacts

# Логирование
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("android-shizuku-mcp")

mcp = FastMCP("android-shizuku-mcp")

# --- ОЧИЩЕННЫЙ СПИСОК ИНСТРУМЕНТОВ (ТОЛЬКО SHELL И MEGA-WRAPPER) ---

@mcp.tool()
async def termux_shell(command: str) -> dict:
    """
    Executes a bash command directly in the Termux environment (User level).
    Use this for:
    - Managing files in ~/ (Termux home)
    - Running installed packages (python, git, ffmpeg, etc.)
    - Using pkg/apt package managers
    - Accessing any Termux-specific utilities
    """
    return await shell_tools.termux_shell(command=command)

@mcp.tool()
async def system_shell(command: str) -> dict:
    """
    Executes a shell command via Shizuku/rish (System level, ADB user context).
    Use this for:
    - Managing Android apps (pm list packages, am start, etc.)
    - Changing system settings (settings get/put)
    - Diagnostics (dumpsys, top, logcat)
    - Any high-privilege Android system operations
    """
    return await shell_tools.system_shell(command=command)

@mcp.tool()
async def termux_cmd(command: str, args: list[str] = None) -> dict:
    """
    ULTIMATE WRAPPER for all 80+ Termux and Termux:API commands.
    Automatically handles 'termux-' prefix and parses JSON output.

    --- AVAILABLE COMMANDS REFERENCE ---
    
    1. BASIC (No API required):
    termux-info, termux-wake-lock, termux-wake-unlock, termux-setup-storage, 
    termux-open, termux-open-url, termux-reload-settings, termux-backup, termux-restore

    2. POWER & DISPLAY (API):
    battery-status, brightness, torch (flashlight), wallpaper

    3. IO & UI (API):
    clipboard-get, clipboard-set, toast, notification, notification-list, 
    notification-remove, dialog (input/confirm/etc.)

    4. MULTIMEDIA (API):
    camera-info, camera-photo, microphone-record, media-player, media-scan

    5. NETWORK & SENSORS (API):
    wifi-scaninfo, wifi-connectioninfo, wifi-enable, location (GPS), sensor (gyro/accel)

    6. TELEPHONY (API):
    call-log, contact-list, sms-inbox, sms-list, sms-send, telephony-call, telephony-deviceinfo

    7. STORAGE (SAF - Storage Access Framework):
    saf-ls, saf-read, saf-write, saf-mkdir, saf-rm, saf-stat

    8. SYSTEM (API):
    share, download, fingerprint, keystore, job-scheduler, volume, vibrate, tts-speak
    """
    return await run_mega_termux_command(command, args)

# Мидлварь безопасности (остается без изменений)
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
    print("READY! Only 3 powerful shell tools are active.")
    print("="*50)
    print(json.dumps(mcp_config, indent=2))
    print("="*50 + "\n")
    config.setup_dirs()
    uvicorn.run(protected_app, host=config.host, port=config.port, log_level="info")

if __name__ == "__main__":
    main()
