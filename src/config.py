import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class ServerConfig(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8765
    endpoint: str = "/mcp"
    auth_token: Optional[str] = None
    
    # Paths
    artifacts_dir: Path = Path("artifacts")
    logs_dir: Path = Path("logs")
    
    # Security & Features
    enable_raw_shell: bool = False
    max_command_timeout_sec: int = 20
    allow_package_force_stop: bool = True
    allow_screenrecord: bool = True
    
    # Shell filters
    allowed_shell_patterns: List[str] = []
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
