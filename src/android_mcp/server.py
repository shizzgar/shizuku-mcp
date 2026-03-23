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
    """A collection of hard-learned lessons about Android automation."""
    return """
    1. THE SHIZUKU MYTH: 
       There is NO 'shizuku' command line binary. Shizuku is a service. 
       To use its power, run commands via 'rish -c "your_command"'.
    
    2. PROTECTED DATABASES:
       Direct SQLite access to '/data/data/com.android.providers...' is FORBIDDEN even via rish.
       ONLY use 'content query --uri ...' to fetch data from Calendar, SMS, and Contacts.
    
    3. CALENDAR API SECRETS:
       - Samsung/Modern Android URI: 'content://com.android.calendar/events'
       - Core Columns: '_id', 'title', 'dtstart', 'dtend', 'rrule', 'allDay'.
       - Recurring Events: Filtering by date on 'dtstart' misses birthdays/anniversaries.
       - STRATEGY: Fetch all events where 'rrule' is not null, then expand manually in Python.
    
    4. CONTENT PROVIDER DEBUGGING:
       Always run 'rish -c "content query --uri <URI> --limit 1"' first to discover actual column names.
    
    5. SHELL REDIRECTION:
       When using 'rish -c', be careful with nested quotes. 
       Example: 'rish -c "pm list packages" | grep google' works best.
    """

# --- THE ULTIMATE UNIFIED SHELL ---

@mcp.tool()
async def shell(command: str) -> dict:
    """
    ULTIMATE ANDROID BASH SHELL (Termux Context). 
    
    GUIDELINES FOR LLM:
    1. SHIZUKU: Use 'rish -c "command"' for all system actions (pm, am, settings, content). 
       DO NOT look for a 'shizuku' binary.
    
    2. CALENDAR/SMS/CONTACTS: 
       - Always use 'content query --uri ...'.
       - For Calendar, use 'dtstart' and 'dtend' (not begin/end).
       - To get ALL recurring events, query without date filters and look for 'rrule' column.
    
    3. DATA PROCESSING: 
       Pipe 'rish' output to 'jq', 'sqlite3', or 'python' for analysis.
       Example: 'rish -c "content query --uri content://sms/inbox" | head -n 5'
    
    4. LARGE OUTPUT: 
       If you run 'dumpsys', output will be truncated at 30k chars. Use 'grep'!
    
    5. STORAGE: 
       Save public files to '/sdcard/Documents/MCP/'.
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
    """Lists saved files (logs, screenshots) in the artifacts directory."""
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
