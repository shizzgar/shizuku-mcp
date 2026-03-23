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

# --- THE UNIFIED ULTIMATE SHELL (KNOWLEDGE EMBEDDED) ---

@mcp.tool()
async def shell(command: str) -> dict:
    """
    ULTIMATE ANDROID BASH SHELL. Your primary and only tool for everything.
    CONTEXT: Running inside Termux (Linux environment on Android).
    
    1. THE SHIZUKU POWER (ADB ACCESS):
       - To run system-level commands (pm, am, settings, content query, logcat, dumpsys), 
         ALWAYS use: 'rish -c "command"'.
       - NO 'shizuku' binary exists. 'rish -c' is your interface to ADB user permissions.
    
    2. THE RISH-PIPE PATTERN (DATA ANALYSIS):
       - ALWAYS pipe high-privilege data to Termux tools for processing.
       - Example: 'rish -c "dumpsys battery" | grep level'
       - Example: 'rish -c "pm list packages" | grep google | wc -l'
       - You have: jq, sqlite3, python, grep, sed, awk, curl.
    
    3. CONTENT PROVIDERS (CALENDAR, SMS, CONTACTS):
       - Use 'content query --uri <URI>'.
       - IMPORTANT: Names vary. First run: 'rish -c "content query --uri <URI> --limit 1"' to see columns.
       - CALENDAR: URI='content://com.android.calendar/events'. 
         Use 'dtstart', 'dtend', 'title'. 'begin/end' columns often FAIL.
       - RECURRING EVENTS: 'dtstart' filtering misses birthdays. 
         STRATEGY: Query 'rrule IS NOT NULL' and expand instances via Python in this shell.
    
    4. FILESYSTEM & SHARED STORAGE:
       - HOME ('~/'): Private. Other Android apps CANNOT see files here.
       - SHARED: '/sdcard/Documents/MCP/'. USE THIS for files (Markdown, PDF, etc.) 
         intended to be opened by other apps.
       - OPENING FILES: Use 'termux-open /sdcard/Documents/MCP/file.ext'.
    
    5. HARDWARE (Termux:API):
       - Run directly: battery-status, location, toast, notification, clipboard-get/set, etc.
    
    6. LARGE OUTPUT:
       - Output > 30k chars is truncated and saved to '~/artifacts/'. Use 'grep' to filter!
    """
    return await shell_tools.execute_android_shell(command=command)

# --- SERVICE TOOLS ---

@mcp.tool()
async def doctor() -> dict:
    """Provides system diagnostics, Shizuku status, and Termux:API availability."""
    from src.doctor import get_system_info
    return {"ok": True, "data": await get_system_info()}

@mcp.tool()
async def list_artifacts() -> dict:
    """Lists saved files (logs, screenshots) in the artifacts directory (~/artifacts)."""
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
    
    try: os.makedirs("/sdcard/Documents/MCP", exist_ok=True)
    except: pass

    print("\n" + "="*50)
    print("READY! Ultimate Shell with Embedded Wisdom is active.")
    print("="*50 + "\n")
    
    config.setup_dirs()
    uvicorn.run(protected_app, host=config.host, port=config.port, log_level="info")

if __name__ == "__main__":
    main()
