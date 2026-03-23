from enum import Enum
from typing import Any, Dict, Optional

class ErrorCode(str, Enum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    UNAUTHORIZED = "UNAUTHORIZED"
    TOOL_DISABLED = "TOOL_DISABLED"
    RISH_NOT_FOUND = "RISH_NOT_FOUND"
    RISH_PERMISSION_INVALID = "RISH_PERMISSION_INVALID"
    SHIZUKU_NOT_RUNNING = "SHIZUKU_NOT_RUNNING"
    TERMUX_API_NOT_AVAILABLE = "TERMUX_API_NOT_AVAILABLE"
    COMMAND_TIMEOUT = "COMMAND_TIMEOUT"
    COMMAND_FAILED = "COMMAND_FAILED"
    ARTIFACT_NOT_FOUND = "ARTIFACT_NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class MCPError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": False,
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details
            }
        }
