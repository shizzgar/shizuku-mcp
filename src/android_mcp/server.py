import asyncio
import logging
from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount
from starlette.middleware.base import BaseHTTPMiddleware
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

# Security Middleware Class
class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Origin check
        origin = request.headers.get("origin")
        if origin and not (origin.startswith("http://127.0.0.1") or origin.startswith("http://localhost")):
            logger.warning(f"Request from unusual origin: {origin}")

        # Auth token check
        if config.auth_token:
            auth_header = request.headers.get("authorization")
            if not auth_header or auth_header != f"Bearer {config.auth_token}":
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
        
        return await call_next(request)

# Starlette App Setup
@asynccontextmanager
async def lifespan(app: Starlette):
    config.setup_dirs()
    async with mcp._app.session_manager.run():
        yield

app = Starlette(lifespan=lifespan)
app.add_middleware(SecurityMiddleware)

# Mount the MCP server
app.mount(config.endpoint, mcp.streamable_http_app())

def main():
    import uvicorn
    logger.info(f"Starting Android Shizuku MCP server on {config.host}:{config.port}")
    uvicorn.run(app, host=config.host, port=config.port)

if __name__ == "__main__":
    main()
