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
    ULTIMATE ANDROID BASH SHELL - THE MASTER CONTROL PORTAL.
    
    1. SYSTEM ACCESS (Shizuku/ADB): 
       - ALWAYS use 'rish -c "command"' for high-privilege Android commands.
       - NEVER search for a 'shizuku' binary.
    
    2. THE RISH-PIPE PATTERN:
       - Pipe system data to local tools: 'rish -c "dumpsys battery" | grep level'
    
    3. CONTENT PROVIDERS (READ-ONLY IN ANDROID 15+):
       - Use 'content query --uri <URI>'. (Always test with --limit 1 first to check columns).
       - WRITING (content insert/update) to protected DBs (Contacts, Calendar) usually FAILS due to SELinux/UID limits.
    
    4. ADVANCED FALLBACKS (WHEN APIS/DATABASES ARE BLOCKED):
       If you cannot write to a database programmatically, act like a human:
       
       A. DEEP INTENTS: Pre-fill UI forms so the user just taps 'Save'.
          Example (Contact): 'rish -c "am start -a android.intent.action.INSERT -t vnd.android.cursor.dir/contact -e name 'John Doe' -e phone '123456789'"'
          Example (Calendar): 'rish -c "am start -a android.intent.action.INSERT -t vnd.android.cursor.item/event -e title 'Meeting' -e beginTime 1774251000000"'
       
       B. UI AUTOMATION (Blind/Coordinates): 
          - Dump screen: 'rish -c "uiautomator dump /sdcard/Documents/MCP/dump.xml"'
          - Read XML to find bounds [x1,y1][x2,y2] of buttons.
          - Tap: 'rish -c "input tap <X> <Y>"'
          - Type: 'rish -c "input text 'Hello'"'
          - Keypress: 'rish -c "input keyevent <KEYCODE>"' (e.g., 3=HOME, 4=BACK, 66=ENTER).
    
    5. TERMUX:API HARDWARE CAPABILITIES:
       - UI: termux-toast, termux-notification, termux-dialog, termux-clipboard-get/set
       - HW: termux-battery-status, termux-location, termux-torch, termux-sensor
       - TELEPHONY: termux-sms-list, termux-contact-list, termux-call-log
    
    6. STORAGE & LIMITS:
       - PRIVATE: '~/ '
       - SHARED: '/sdcard/Documents/MCP/' (Use this for dumps/files for other apps).
       - Output > 30k chars is truncated and saved to '~/artifacts/'. Use 'grep'!
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
