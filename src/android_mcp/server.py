import asyncio
import logging
import json
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

from src.config import config
from src.tools import doctor_tools, app_tools, intent_tools, shell_tools, screen_tools, utility_tools
from src.artifacts import list_artifacts

# Логирование
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("android-shizuku-mcp")

mcp = FastMCP("android-shizuku-mcp")

# --- Инструменты ---
@mcp.tool()
async def doctor() -> dict: return await doctor_tools.doctor()
@mcp.tool()
async def ping() -> dict: return await doctor_tools.ping()
@mcp.tool()
async def list_packages(third_party_only: bool = True, filter_str: str = None) -> dict:
    return await app_tools.list_packages(third_party_only=third_party_only, filter_str=filter_str)
@mcp.tool()
async def open_app(package_name: str) -> dict: return await app_tools.open_app(package_name=package_name)
@mcp.tool()
async def force_stop(package_name: str) -> dict: return await app_tools.force_stop(package_name=package_name)
@mcp.tool()
async def start_intent(action: str = None, data: str = None, package: str = None, component: str = None, extras: dict = None) -> dict:
    return await intent_tools.start_intent(action, data, package, component, extras)
@mcp.tool()
async def open_url(url: str) -> dict: return await intent_tools.open_url(url=url)
@mcp.tool()
async def take_screenshot() -> dict: return await screen_tools.take_screenshot()
@mcp.tool()
async def record_screen(duration_sec: int = 10) -> dict: return await screen_tools.record_screen(duration_sec=duration_sec)
@mcp.tool()
async def clipboard_get() -> dict: return await utility_tools.clipboard_get()
@mcp.tool()
async def clipboard_set(text: str) -> dict: return await utility_tools.clipboard_set(text=text)
@mcp.tool()
async def show_notification(title: str, content: str) -> dict: return await utility_tools.show_notification(title=title, content=content)
@mcp.tool()
async def battery_status() -> dict: return await utility_tools.battery_status()
@mcp.tool()
async def wifi_status() -> dict: return await utility_tools.wifi_status()
@mcp.tool()
async def device_info() -> dict: return await utility_tools.device_info()
@mcp.tool()
async def shell_readonly(command: str) -> dict: return await shell_tools.shell_readonly(command=command)
@mcp.tool()
async def shell_privileged(command: str, confirm_dangerous: bool = False) -> dict:
    return await shell_tools.shell_privileged(command=command, confirm_dangerous=confirm_dangerous)

@mcp.tool()
async def shell_termux(command: str) -> dict:
    """Runs a shell command directly in Termux context (access to ~/ and pkg)."""
    return await shell_tools.shell_termux(command=command)

@mcp.tool()
async def list_artifacts_tool() -> dict: return {"ok": True, "data": list_artifacts()}


# Легкая ASGI мидлварь
class AuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            
            logger.info(f"--> {scope['method']} {scope['path']}")

            if config.auth_token and auth_header != f"Bearer {config.auth_token}":
                logger.warning(f"!!! AUTH FAILED")
                response = JSONResponse({"error": "Unauthorized"}, status_code=401)
                await response(scope, receive, send)
                return

        async def wrapped_send(message):
            if message["type"] == "http.response.start":
                status = message.get("status")
                logger.info(f"<-- Status {status}")
                if status in (301, 307, 308):
                    for k, v in message.get("headers", []):
                        if k.lower() == b"location":
                            logger.warning(f"!!! REDIRECT TO: {v.decode()}")
            await send(message)

        await self.app(scope, receive, wrapped_send)

def main():
    import uvicorn
    
    # Берем приложение прямо из FastMCP
    # Оно уже содержит в себе все нужные Lifespan и роуты
    app = mcp.streamable_http_app()
    protected_app = AuthMiddleware(app)

    mcp_url = f"http://{config.host}:{config.port}/mcp"
    mcp_config = {
        "mcpServers": {
          "android-shizuku": {
            "url": mcp_url,
            "headers": { "Authorization": f"Bearer {config.auth_token}" if config.auth_token else "" }
          }
        }
    }
    print("\n" + "="*50)
    print("READY! Copy this JSON to RikkaHub:")
    print("="*50)
    print(json.dumps(mcp_config, indent=2))
    print("="*50 + "\n")

    config.setup_dirs()
    # Запускаем обернутое приложение
    uvicorn.run(protected_app, host=config.host, port=config.port, log_level="info")

if __name__ == "__main__":
    main()
