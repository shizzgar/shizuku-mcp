import asyncio
import logging
import json
import os
import subprocess
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
    
    3. PUBLIC FILES ACCESS:
       Files in Termux home (~/) are NOT visible to other Android apps. 
       Always use '/sdcard/Documents/MCP/' for files intended to be opened by external apps.
    """

# --- TWO POWERFUL SHELL TOOLS ---

@mcp.tool()
async def termux_shell(command: str) -> dict:
    """
    [TERMUX USER CONTEXT] - Full Bash shell inside Termux.
    Use this for: 
    - Complex data processing (Python, SQLite, jq).
    - Managing files and packages (pkg/apt).
    - Hardware access via 'termux-*' commands.
    
    ⚠️ SHARED STORAGE ACCESS:
    - Files in '~/ ' are PRIVATE. Other apps (Markdown editors, PDF readers) CANNOT see them.
    - For PUBLIC files, ALWAYS use: '/sdcard/Documents/MCP/'.
    - To open a file in another app: 'termux-open /sdcard/Documents/MCP/filename.ext'
    
    DATA ANALYSIS:
    - Use 'sqlite3' to analyze large dumps fetched from system_shell.
    """
    return await shell_tools.termux_shell(command=command)

@mcp.tool()
async def system_shell(command: str) -> dict:
    """
    [SYSTEM ADB CONTEXT] - High-privilege access via Shizuku.
    Use this for:
    - App management (am/pm), Settings, and System Diagnostics.
    - Content Provider queries (content query --uri ...).
    
    ENVIRONMENT: Runs as 'shell' user. Use this to fetch data, then pipe to termux_shell for analysis.
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

def setup_shared_dir():
    """Создает публичную папку для обмена файлами с Android."""
    try:
        path = "/sdcard/Documents/MCP"
        os.makedirs(path, exist_ok=True)
        logger.info(f"Shared directory ready: {path}")
    except Exception as e:
        logger.warning(f"Could not create shared directory on SDCard: {e}")

def main():
    import uvicorn
    app = mcp.streamable_http_app()
    protected_app = AuthMiddleware(app)
    
    print("\n" + "="*50)
    print("READY! Terminal MCP with Shared Storage Support.")
    print("="*50 + "\n")
    
    config.setup_dirs()
    setup_shared_dir()
    
    uvicorn.run(protected_app, host=config.host, port=config.port, log_level="info")

if __name__ == "__main__":
    main()
