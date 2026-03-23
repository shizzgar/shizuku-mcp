from typing import Any, Dict
from src.doctor import get_system_info

async def doctor() -> Dict[str, Any]:
    """Provides system diagnostics and status."""
    info = await get_system_info()
    return {"ok": True, "data": info}

async def ping() -> Dict[str, Any]:
    """Simple healthcheck."""
    return {"ok": True, "data": "pong"}
