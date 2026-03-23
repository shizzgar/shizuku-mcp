import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class ServerConfig(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8765
    endpoint: str = "/mcp" # FastMCP сам добавит что нужно
    auth_token: Optional[str] = None
    
    # Paths
    artifacts_dir: Path = Path("artifacts")
    logs_dir: Path = Path("logs")
    
    # Security & Features
    enable_raw_shell: bool = False
    max_command_timeout_sec: int = 30 # Увеличим для Android 15
    allow_package_force_stop: bool = True
    allow_screenrecord: bool = True
    
    # Shell filters
    # Теперь можно переопределить через MCP_ALLOWED_SHELL_PATTERNS="ls,top,df"
    allowed_shell_patterns: List[str] = [
        r"^pm list packages",
        r"^getprop",
        r"^settings get",
        r"^dumpsys",
        r"^cmd package resolve-activity",
        r"^ls",
        r"^cat",
        r"^df",
        r"^uptime",
        r"^uname"
    ]
    
    denied_shell_patterns: List[str] = [
        "rm -rf /",
        "su",
        "sudo",
        "reboot",
        "svc power shutdown"
    ]
    
    # rish settings
    rish_path: Optional[str] = None
    rish_preserve_env: int = 0
    
    model_config = SettingsConfigDict(env_prefix="MCP_", env_file=".env", extra="ignore")

    def setup_dirs(self):
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

config = ServerConfig()
