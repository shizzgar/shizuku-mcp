import asyncio
import logging
import json
from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount
from mcp.server.fastmcp import FastMCP

from src.config import config
from src.errors import MCPError, ErrorCode
from src.tools import doctor_tools, app_tools, intent_tools, shell_tools, screen_tools, utility_tools
from src.artifacts import list_artifacts

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("android-shizuku-mcp")

# Initialize FastMCP
mcp = FastMCP("android-shizuku-mcp")

# Register Tools
@mcp.tool()
async def doctor() -> dict:
    """Provides system diagnostics and status."""
    return await doctor_tools.doctor()

@mcp.tool()
async def ping() -> dict:
    """Simple healthcheck."""
    return await doctor_tools.ping()

@mcp.tool()
async def list_packages(third_party_only: bool = True, filter_str: str = None) -> dict:
    """Lists installed Android packages."""
    return await app_tools.list_packages(third_party_only=third_party_only, filter_str=filter_str)

@mcp.tool()
async def open_app(package_name: str) -> dict:
    """Opens an application by package name."""
    return await app_tools.open_app(package_name=package_name)

@mcp.tool()
async def force_stop(package_name: str) -> dict:
    """Force stops an application."""
    return await app_tools.force_stop(package_name=package_name)

@mcp.tool()
async def start_intent(
    action: str = None, 
    data: str = None, 
    package: str = None, 
    component: str = None, 
    extras: dict = None
) -> dict:
    """Starts an Android Intent."""
    return await intent_tools.start_intent(action, data, package, component, extras)

@mcp.tool()
async def open_url(url: str) -> dict:
    """Opens a URL using an Android Intent."""
    return await intent_tools.open_url(url=url)

@mcp.tool()
async def take_screenshot() -> dict:
    """Takes a screenshot and saves it as an artifact."""
    return await screen_tools.take_screenshot()

@mcp.tool()
async def record_screen(duration_sec: int = 10) -> dict:
    """Records the screen for a specified duration."""
    return await screen_tools.record_screen(duration_sec=duration_sec)

@mcp.tool()
async def clipboard_get() -> dict:
    """Gets the current clipboard content."""
    return await utility_tools.clipboard_get()

@mcp.tool()
async def clipboard_set(text: str) -> dict:
    """Sets the clipboard content."""
    return await utility_tools.clipboard_set(text=text)

@mcp.tool()
async def show_notification(title: str, content: str) -> dict:
    """Shows an Android notification."""
    return await utility_tools.show_notification(title=title, content=content)

@mcp.tool()
async def battery_status() -> dict:
    """Gets the battery status."""
    return await utility_tools.battery_status()

@mcp.tool()
async def wifi_status() -> dict:
    """Gets the WiFi connection status."""
    return await utility_tools.wifi_status()

@mcp.tool()
async def device_info() -> dict:
    """Gets general device information."""
    return await utility_tools.device_info()

@mcp.tool()
async def shell_readonly(command: str) -> dict:
    """Runs a read-only shell command via rish."""
    return await shell_tools.shell_readonly(command=command)

@mcp.tool()
async def shell_privileged(command: str, confirm_dangerous: bool = False) -> dict:
    """Runs a privileged shell command via rish. Requires explicit confirmation."""
    return await shell_tools.shell_privileged(command=command, confirm_dangerous=confirm_dangerous)

@mcp.tool()
async def list_artifacts_tool() -> dict:
    """Lists saved artifacts (screenshots, recordings)."""
    return {"ok": True, "data": list_artifacts()}

# Pure ASGI Security Middleware (Doesn't break streaming/SSE)
class SecurityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Simple manual check of headers to avoid reading body/breaking stream
        headers = dict(scope.get("headers", []))
        
        # Check Authorization
        if config.auth_token:
            auth_val = headers.get(b"authorization", b"").decode()
            if not auth_val or auth_val != f"Bearer {config.auth_token}":
                response = JSONResponse({"error": "Unauthorized"}, status_code=401)
                await response(scope, receive, send)
                return

        # Check Origin
        origin = headers.get(b"origin", b"").decode()
        if origin and not (origin.startswith("http://127.0.0.1") or origin.startswith("http://localhost")):
             logger.warning(f"Request from unusual origin: {origin}")

        await self.app(scope, receive, send)

# Starlette App Setup
@asynccontextmanager
async def lifespan(app: Starlette):
    config.setup_dirs()
    async with mcp.session_manager.run():
        yield

# We build the Starlette app and wrap it with middleware
# The mount point should match the endpoint in config
app = Starlette(lifespan=lifespan)
# FastMCP streamable_http_app is already a Starlette app
inner_mcp_app = mcp.streamable_http_app()

# Mount it. If config.endpoint is "/mcp/", it handles /mcp/ and children.
app.mount(config.endpoint, SecurityMiddleware(inner_mcp_app))

def main():
    import uvicorn
    
    # Формируем конфиг для пользователя
    mcp_config = {
        "mcpServers": {
          "android-shizuku": {
            "url": f"http://{config.host}:{config.port}{config.endpoint}",
            "headers": {
              "Authorization": f"Bearer {config.auth_token}" if config.auth_token else ""
            }
          }
        }
    }

    print("\n" + "="*50)
    print("READY! Copy this JSON to your MCP Client config:")
    print("="*50)
    print(json.dumps(mcp_config, indent=2))
    print("="*50)
    print(f"NOTE: For PC connection, run: adb reverse tcp:{config.port} tcp:{config.port}")
    print("="*50 + "\n")

    logger.info(f"Starting Android Shizuku MCP server on {config.host}:{config.port}")
    uvicorn.run(app, host=config.host, port=config.port)

if __name__ == "__main__":
    main()
