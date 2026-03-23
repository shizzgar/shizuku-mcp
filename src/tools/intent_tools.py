from typing import Any, Dict, Optional
from src.runners.rish_runner import rish_runner
from src.errors import MCPError, ErrorCode

async def start_intent(
    action: Optional[str] = None, 
    data: Optional[str] = None, 
    package: Optional[str] = None, 
    component: Optional[str] = None, 
    extras: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Starts an Android Intent."""
    cmd = "am start"
    if action:
        cmd += f" -a {action}"
    if data:
        cmd += f" -d {data}"
    if package:
        cmd += f" -p {package}"
    if component:
        cmd += f" -n {component}"
    
    if extras:
        for k, v in extras.items():
            if isinstance(v, bool):
                cmd += f" --ez {k} {str(v).lower()}"
            elif isinstance(v, int):
                cmd += f" --ei {k} {v}"
            elif isinstance(v, float):
                cmd += f" --ef {k} {v}"
            else:
                cmd += f" --es {k} '{v}'"
    
    rc, stdout, stderr = await rish_runner.run_rish(cmd)
    if rc != 0:
        raise MCPError(ErrorCode.COMMAND_FAILED, f"Failed to start intent: {stderr}")
    
    return {"ok": True, "data": {"started": True, "stdout": stdout}}

async def open_url(url: str) -> Dict[str, Any]:
    """Opens a URL using an Android Intent."""
    return await start_intent(action="android.intent.action.VIEW", data=url)
