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
       FIX: Fetch events with 'rrule IS NOT NULL' and expand them manually via Python in termux_shell.
    
    2. PERMISSION HANGS:
       On Android 15+, some background commands may timeout if the app (like Termux:API) is throttled.
       FIX: Ensure 'Unrestricted' battery mode and 'Display over other apps' is allowed.
    
    3. COLUMN NAMES:
       Content Provider columns vary by Android version. If a query fails, fetch all columns first to verify.
    """

# --- TWO POWERFUL SHELL TOOLS ---

@mcp.tool()
async def termux_shell(command: str) -> dict:
    """
    [TERMUX USER CONTEXT] - Full Bash shell inside Termux.
    Use this for: 
    - Complex data processing (Python, jq, sed, awk).
    - Managing local files (~/) and packages (pkg/apt).
    - Hardware access via 'termux-*' commands.
    
    EXPERT TIP: If a system_shell command (like calendar query) returns raw data that needs 
    complex expansion (like RRULEs), pipe the output to a Python script here.
    """
    return await shell_tools.termux_shell(command=command)

@mcp.tool()
async def system_shell(command: str) -> dict:
    """
    [SYSTEM ADB CONTEXT] - High-privilege access via Shizuku.
    Use this for:
    - App management (am/pm), Settings, and System Diagnostics.
    - Content Provider queries (content query --uri ...).
    
    CRITICAL PITFALL: 
    When querying 'content://com.android.calendar/events', recurring events (birthdays, etc.) 
    are NOT returned as individual instances. Only the original template is returned.
    STRATEGY: Query 'rrule' column, and if not null, manually expand instances using termux_shell.
    """
    return await shell_tools.system_shell(command=command)

# --- SERVICE TOOLS ---

@mcp.tool()
async def doctor() -> dict:
    """Health check for Shizuku and Termux:API."""
    from src.doctor import get_system_info
    return {"ok": True, "data": await get_system_info()}

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
    print("\n" + "="*50)
    print("READY! Multi-Shell MCP with Android Wisdom is active.")
    print("="*50 + "\n")
    config.setup_dirs()
    uvicorn.run(protected_app, host=config.host, port=config.port, log_level="info")

if __name__ == "__main__":
    main()
