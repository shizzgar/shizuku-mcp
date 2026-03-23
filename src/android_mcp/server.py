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

# --- KNOWLEDGE RESOURCES ---

@mcp.resource("knowledge://android/pitfalls")
def get_android_pitfalls() -> str:
    """Critical technical notes about Android Content Providers and Shell limitations."""
    return """
    1. CALENDAR RECURRING EVENTS:
       Standard 'content query' on 'content://com.android.calendar/events' fails to return recurring instances.
       STRATEGY: Use termux_shell to run: 'rish -c "content query --uri content://com.android.calendar/events" | python process_script.py'
    
    2. PUBLIC FILES ACCESS:
       Files in Termux home (~/) are PRIVATE. Always use '/sdcard/Documents/MCP/' for sharing with other Android apps.
    
    3. THE RISH PIPE PATTERN:
       To process system data with powerful tools (jq, sqlite3, awk), use rish INSIDE termux_shell:
       'rish -c "dumpsys window" | grep -i focus'
    
    4. LARGE OUTPUT (dumpsys, logcat):
       Commands like 'dumpsys' produce HUGE output. 
       - ALWAYS use 'grep' to filter.
       - If output is truncated, find the full log in the 'artifacts' directory.
    """

# --- UNIFIED ULTIMATE SHELL TOOL ---

@mcp.tool()
async def shell(command: str) -> dict:
    """
    ULTIMATE ANDROID BASH SHELL. Your primary tool for EVERYTHING.
    
    1. CONTEXT: You are running inside Termux.
    
    2. THE POWER MOVE (RISH-PIPE):
       To run high-privilege system commands, use 'rish -c "command"'.
       ALWAYS pipe 'rish' output to local tools (jq, grep, awk, python) for processing.
       Example: 'rish -c "pm list packages" | grep google | wc -l'
    
    3. HARDWARE ACCESS (Termux:API):
       Use 'termux-*' commands directly (battery-status, location, toast, etc.)
    
    4. FILESYSTEM & STORAGE:
       - '~/' (HOME): Private.
       - '/sdcard/Documents/MCP/': SHARED. USE THIS for files to be opened by Android apps.
    
    ⚠️ LARGE OUTPUT MANAGEMENT:
    - Commands like 'dumpsys', 'logcat', or 'pm list' can return megabytes of data.
    - If the output exceeds 30,000 chars, it will be AUTOMATICALLY TRUNCATED.
    - The FULL output will be saved to a .txt file in the artifacts directory.
    - STRATEGY: Always use 'grep', 'head -n 100', or 'tail' to avoid truncation.
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
    """List saved files (logs, screenshots) in the artifacts directory."""
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
    print("READY! The Unified Shell with Large Output Protection is active.")
    print("="*50 + "\n")
    config.setup_dirs()
    uvicorn.run(protected_app, host=config.host, port=config.port, log_level="info")

if __name__ == "__main__":
    main()
