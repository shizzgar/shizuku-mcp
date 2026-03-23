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
    """

# --- THE DUAL PORTAL ARCHITECTURE ---

@mcp.tool()
async def termux_shell(command: str) -> dict:
    """
    [TERMUX CONTEXT] - Direct access to Termux environment (User level).
    
    ULTIMATE CAPABILITY: 
    You can run system commands via 'rish' and pipe them to Termux utilities (jq, sqlite3, awk, python, sed).
    
    EXAMPLES:
    - List apps and count: 'rish -c "pm list packages" | wc -l'
    - Advanced Battery: 'rish -c "dumpsys battery" | grep -E "level|status"'
    - File sharing: 'echo "content" > /sdcard/Documents/MCP/test.txt && termux-open /sdcard/Documents/MCP/test.txt'
    - Manage packages: 'pkg install <package_name>'
    
    Use this for ALL data processing, file creation, and Termux:API hardware calls.
    """
    return await shell_tools.termux_shell(command=command)

@mcp.tool()
async def system_shell(command: str) -> dict:
    """
    [SYSTEM CONTEXT] - Direct high-privilege access via Shizuku (ADB user).
    Use this for PURE Android commands that don't need Termux-side processing.
    
    CAPABILITIES:
    - pm (package manager), am (activity manager), settings, logcat, dumpsys, input.
    - Direct content provider queries.
    
    NOTE: If you need to 'grep' or 'process' large output, use termux_shell with 'rish -c' instead!
    """
    return await shell_tools.system_shell(command=command)

# --- SERVICE TOOLS ---

@mcp.tool()
async def doctor() -> dict:
    """Check health of Shizuku and Termux:API."""
    from src.doctor import get_system_info
    return {"ok": True, "data": await get_system_info()}

@mcp.tool()
async def list_artifacts() -> dict:
    """List files in the artifacts directory."""
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
    
    # Авто-создание папки для обмена
    try:
        os.makedirs("/sdcard/Documents/MCP", exist_ok=True)
    except:
        pass

    print("\n" + "="*50)
    print("READY! The Dual-Shell 'Rish-Pipe' Portal is active.")
    print("="*50 + "\n")
    
    config.setup_dirs()
    uvicorn.run(protected_app, host=config.host, port=config.port, log_level="info")

if __name__ == "__main__":
    main()
