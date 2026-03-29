import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class ServerConfig(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8765
    endpoint: str = "/mcp" # FastMCP сам добавит что нужно
    auth_token: Optional[str] = None
    
    # Paths
    artifacts_dir: Path = Path("artifacts")
    logs_dir: Path = Path("logs")
    runtime_dir: Path = Path("runtime")
    jobs_dir: Path = Path("runtime/jobs")
    sessions_dir: Path = Path("runtime/sessions")
    
    # Security & Features
    enable_raw_shell: bool = True
    max_command_timeout_sec: int = 30 # Legacy cap for non-shell tools
    sync_command_budget_sec: int = 20
    hard_kill_timeout_sec: int = 600
    inline_output_char_budget: int = 12000
    max_completed_jobs: int = 50
    max_job_age_sec: int = 86400
    max_runtime_storage_bytes: int = 50 * 1024 * 1024
    session_open_wait_ms: int = 120
    allow_package_force_stop: bool = True
    allow_screenrecord: bool = True
    
    # rish settings
    rish_path: Optional[str] = None
    rish_preserve_env: int = 0
    
    model_config = SettingsConfigDict(env_prefix="MCP_", env_file=".env", extra="ignore")

    def setup_dirs(self):
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

config = ServerConfig()
