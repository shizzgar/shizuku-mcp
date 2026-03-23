import asyncio
import logging
import json
import os
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

# --- THE UNIFIED ULTIMATE SHELL (WITH FULL COMMAND REFERENCE) ---

@mcp.tool()
async def shell(command: str) -> dict:
    """
    ULTIMATE ANDROID BASH SHELL. Your primary tool for EVERYTHING.
    CONTEXT: Running inside Termux (Linux) with Shizuku (ADB) support.
    
    1. THE RISH-PIPE PATTERN:
       - Use 'rish -c "command"' for system actions (ADB permissions).
       - ALWAYS pipe to Termux tools: 'rish -c "pm list packages" | grep google'
    
    2. TERMUX:API REFERENCE (Hardware & System):
       - UI: termux-toast, termux-notification, termux-dialog (input/confirm), termux-clipboard-get/set
       - HARDWARE: termux-battery-status, termux-torch (on/off), termux-vibrate, termux-brightness
       - CONNECTIVITY: termux-wifi-connectioninfo, termux-wifi-scaninfo, termux-location (GPS)
       - TELEPHONY: termux-sms-list, termux-sms-send -n <num> -m <txt>, termux-contact-list, termux-call-log, termux-telephony-deviceinfo
       - MULTIMEDIA: termux-camera-photo <file>, termux-microphone-record -d <sec> <file>, termux-media-player play <file>
       - STORAGE (SAF): termux-saf-ls, termux-saf-read, termux-saf-write (Access SD Card/Downloads)
    
    3. ESSENTIAL UTILITIES:
       - Use 'jq' for JSON parsing, 'sqlite3' for databases, 'python' for complex logic.
       - Use 'termux-open <file>' to launch files in Android apps.
    
    4. FILESYSTEM RULES:
       - Files in '~/ ' are PRIVATE. 
       - For sharing with other apps, ALWAYS use: '/sdcard/Documents/MCP/'.
    
    5. PERFORMANCE:
       - Large output (>30k chars) is truncated and saved to '~/artifacts/'.
    """
    return await shell_tools.execute_android_shell(command=command)

# --- SERVICE TOOLS ---

@mcp.tool()
async def doctor() -> dict:
    """Check health of Shizuku and Termux:API."""
    from src.doctor import get_system_info
    return {"ok": True, "data": await get_system_info()}

@mcp.tool()
async def list_artifacts() -> dict:
    """List files in the artifacts directory (~/artifacts)."""
    return {"ok": True, "data": list_artifacts()}

# Middleware
class AuthMiddleware:
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            if config.auth_token and auth_header != f"Bearer {config.auth_token}":
                response = JSONResponse({"error": "Unauthorized"}, status_code=401)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)

def main():
    import uvicorn
    app = mcp.streamable_http_app()
    protected_app = AuthMiddleware(app)
    
    try: os.makedirs("/sdcard/Documents/MCP", exist_ok=True)
    except: pass

    print("\n" + "="*50)
    print("READY! The 'Learned' Android MCP Server is active.")
    print("="*50 + "\n")
    
    config.setup_dirs()
    uvicorn.run(protected_app, host=config.host, port=config.port, log_level="info")

if __name__ == "__main__":
    main()
