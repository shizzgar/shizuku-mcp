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

# --- UNIFIED ULTIMATE SHELL TOOL ---

@mcp.tool()
async def shell(command: str) -> dict:
    """
    ULTIMATE ANDROID BASH SHELL. Your primary tool for EVERYTHING.
    
    1. CONTEXT: You are running inside Termux (Linux environment on Android).
    
    2. THE POWER MOVE (RISH-PIPE):
       To run high-privilege system commands, use 'rish -c "command"'.
       ALWAYS pipe 'rish' output to local tools (jq, grep, awk, python) for processing.
       Example: 'rish -c "pm list packages" | grep google | wc -l'
       Example: 'rish -c "dumpsys battery" | grep level'
    
    3. HARDWARE ACCESS (Termux:API):
       Use 'termux-*' commands directly for Android hardware:
       - battery-status, wifi-connectioninfo, location (GPS)
       - toast "message", notification -c "text", vibration, torch on/off
       - clipboard-get, clipboard-set "text"
       - sms-list, contact-list, call-log
    
    4. FILESYSTEM & STORAGE:
       - '~/' (HOME): Private Termux space. Use for scripts and temporary data.
       - '/sdcard/Documents/MCP/': SHARED space. USE THIS to save files (Markdown, PDF, Images) 
         intended to be opened by other Android apps.
       - To open a shared file in an Android app: 'termux-open /sdcard/Documents/MCP/file.ext'
    
    5. DATA ANALYSIS:
       You have 'sqlite3', 'python', 'jq', 'curl', 'sed' pre-installed. 
       Fetch data via 'rish' or 'content query', then analyze it here.
    
    6. APP MANAGEMENT:
       Use 'rish -c "am start -n <component>"', 'rish -c "am force-stop <pkg>"', 
       or 'rish -c "pm dump <pkg>"'.
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

# Middleware (Auth)
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
    
    # Ensure shared directory exists
    try: os.makedirs("/sdcard/Documents/MCP", exist_ok=True)
    except: pass

    print("\n" + "="*50)
    print("READY! The Unified Ultimate Android Shell is active.")
    print("="*50 + "\n")
    
    config.setup_dirs()
    uvicorn.run(protected_app, host=config.host, port=config.port, log_level="info")

if __name__ == "__main__":
    main()
