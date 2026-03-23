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

# --- THE UNIFIED ULTIMATE SHELL (ULTIMATE KNOWLEDGE EMBEDDED) ---

@mcp.tool()
async def shell(command: str) -> dict:
    """
    ULTIMATE ANDROID BASH SHELL - THE MASTER CONTROL PORTAL. Your primary tool for EVERYTHING.
    
    1. ARCHITECTURE & PERMISSIONS:
       - CONTEXT: You are a Linux user inside Termux.
       - SYSTEM ACCESS: To run high-privilege Android commands (pm, am, settings, content query, dumpsys, logcat), 
         you MUST use the rish wrapper: 'rish -c "your_command"'.
       - NO CLI BINARY 'shizuku': Shizuku power is accessed ONLY through 'rish -c'.
       - DATA PROCESSING: Use local Termux tools (jq, sqlite3, python, grep, awk, sed) by piping:
         Example: 'rish -c "pm list packages" | grep google | cut -d: -f2'
    
    2. TERMUX:API COMPREHENSIVE REFERENCE:
       [UI & INTERACTION]
       - termux-toast [-c color] [-g gravity] "message"
       - termux-notification [-t title] [-c content] [--id id] [--action "cmd"]
       - termux-clipboard-get / termux-clipboard-set "text"
       - termux-dialog [confirm|checkbox|counter|date|radio|sheet|spinner|text|time]
       [HARDWARE & SENSORS]
       - termux-battery-status (Returns JSON: percentage, temperature, health)
       - termux-torch [on|off] (Toggle flashlight)
       - termux-vibrate [-d duration_ms] [-f]
       - termux-brightness [0-255]
       - termux-location [-p gps|network|passive] [-r last|updates|once]
       - termux-sensor -s [sensor_name] -n 1 (Get gyro, accel, etc.)
       [TELEPHONY & CONNECTIVITY]
       - termux-sms-list [-l limit] [-n] (Get SMS messages)
       - termux-sms-send -n number "message"
       - termux-contact-list (Returns JSON contacts)
       - termux-call-log [-l limit]
       - termux-telephony-call <number>
       - termux-wifi-connectioninfo / termux-wifi-scaninfo
       [MULTIMEDIA]
       - termux-camera-photo [-c camera_id] <file.jpg>
       - termux-microphone-record [-d duration] [-f file.mp3]
       - termux-media-player [play|pause|stop|info] <file>
       [STORAGE & SAF]
       - termux-saf-ls / termux-saf-read / termux-saf-write (Access SD Card without root)
    
    3. ANDROID CONTENT PROVIDERS (THE GOLD MINE):
       - URI FORMAT: Calendar='content://com.android.calendar/events', SMS='content://sms/inbox', Contacts='content://contacts/people'.
       - COLUMN DISCOVERY: URIs and columns change between Samsung/Pixel. 
         ALWAYS run: 'rish -c "content query --uri <URI> --limit 1"' first to see valid column names.
       - CALENDAR SECRETS: 
         * Use columns: 'dtstart', 'dtend', 'title', 'rrule'. (NOT begin/end).
         * Recurring events (birthdays) are NOT returned by date filters on 'dtstart'. 
         * STRATEGY: Query 'rrule IS NOT NULL', then use Python in this shell to expand instances.
    
    4. ADVANCED FALLBACKS (UI AUTOMATION):
       If programmatic access fails, act like a human using UI Automator.
       NEVER parse dump.xml with grep! Use Python's xml.etree.ElementTree.
       Workflow:
       1. 'rish -c "uiautomator dump /sdcard/dump.xml"'
       2. Use Python to parse bounds '[x1,y1][x2,y2]' of the target node (e.g., text="Save").
       3. Calculate center: x=(x1+x2)/2, y=(y1+y2)/2
       4. Tap: 'rish -c "input tap x y"'
    
    5. FILESYSTEM & INTER-APP SHARING:
       - PRIVATE: '~/ ' (HOME) is invisible to other apps.
       - PUBLIC: '/sdcard/Documents/MCP/'. Use this for files (Markdown, PDF, Logs) intended for Android apps.
       - OPENING: Use 'termux-open /sdcard/Documents/MCP/file.pdf' to launch the default Android viewer.
    
    6. SILENT EXECUTION (CRITICAL):
       - DO NOT use 'echo' to print human-readable explanations, ASCII art, or progress updates.
       - The user DOES NOT SEE the terminal output. The output goes back to YOU.
       - Output ONLY raw data (JSON, paths, IDs) that you need for your next step.
    
    7. EXECUTION & LIMITS:
       - TRUNCATION: Output > 30,000 chars is saved to '~/artifacts/' and truncated in your view.
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
    print("READY! The Ultimate Knowledge-Powered Android Shell is active.")
    print("="*50 + "\n")
    
    config.setup_dirs()
    uvicorn.run(protected_app, host=config.host, port=config.port, log_level="info")

if __name__ == "__main__":
    main()
