import logging
import os
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

from src.config import config
from src.errors import MCPError, ErrorCode
from src.tools import shell_tools
from src.artifacts import list_artifacts as list_saved_artifacts

# Логирование
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("android-shizuku-mcp")

mcp = FastMCP("android-shizuku-mcp")

# --- PRIMARY SHELL TOOL ---

@mcp.tool()
async def shell(
    command: str | None = None,
    privilege_mode: str = "auto",
    timeout_sec: int | None = None,
    output_budget_chars: int | None = None,
    action: str = "auto",
    continuation: str = "start",
    job_id: str | None = None,
    session_id: str | None = None,
    cwd: str | None = None,
    input_text: str | None = None,
    append_newline: bool = True,
    from_offset: int | None = None,
    from_stdout_offset: int | None = None,
    from_stderr_offset: int | None = None,
) -> dict:
    """
    Universal Android shell with one-shot exec and persistent sessions.

    Preferred actions:
    - `action='exec'`: run one command
    - `action='poll'`: inspect a running one-shot job via `job_id`
    - `action='open_session'`: open a persistent shell session
    - `action='write'`: send input to `session_id`
    - `action='read'`: read new output from `session_id`
    - `action='close'` or `action='cancel'`: stop a session or job

    `action='auto'` picks exec for ordinary commands and session mode for interactive ones.
    If output fits the inline budget, it is returned whole instead of being split into sections.
    Legacy `continuation=start|continue|cancel` arguments are still accepted for compatibility.
    """
    try:
        return await shell_tools.execute_android_shell(
            command=command,
            privilege_mode=privilege_mode,
            timeout_sec=timeout_sec,
            output_budget_chars=output_budget_chars,
            action=action,
            continuation=continuation,
            job_id=job_id,
            session_id=session_id,
            cwd=cwd,
            input_text=input_text,
            append_newline=append_newline,
            from_offset=from_offset,
            from_stdout_offset=from_stdout_offset,
            from_stderr_offset=from_stderr_offset,
        )
    except MCPError as exc:
        return exc.to_dict()
    except Exception as exc:
        return MCPError(
            ErrorCode.INTERNAL_ERROR,
            "shell execution failed",
            details={"error": str(exc)},
        ).to_dict()

# --- SERVICE TOOLS ---

@mcp.tool()
async def doctor() -> dict:
    """Provides system diagnostics, Shizuku status, and Termux:API availability."""
    from src.doctor import get_system_info
    return {"ok": True, "data": await get_system_info()}

@mcp.tool()
async def list_artifacts() -> dict:
    """Lists saved files (logs, screenshots) in the artifacts directory (~/artifacts)."""
    return {"ok": True, "data": list_saved_artifacts()}

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
