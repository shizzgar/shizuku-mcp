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
        details: Optional[Dict[str, Any]] = None,
        retryable: Optional[bool] = None,
        suggested_next_action: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.retryable = _default_retryable(code) if retryable is None else retryable
        self.suggested_next_action = suggested_next_action or _default_suggested_next_action(code)
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": False,
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details,
                "retryable": self.retryable,
                "suggested_next_action": self.suggested_next_action,
            }
        }


def _default_retryable(code: ErrorCode) -> bool:
    return code in {
        ErrorCode.SHIZUKU_NOT_RUNNING,
        ErrorCode.COMMAND_TIMEOUT,
        ErrorCode.COMMAND_FAILED,
        ErrorCode.INTERNAL_ERROR,
    }


def _default_suggested_next_action(code: ErrorCode) -> str:
    suggestions = {
        ErrorCode.INVALID_ARGUMENT: "Fix the tool arguments and retry.",
        ErrorCode.UNAUTHORIZED: "Provide a valid bearer token and retry.",
        ErrorCode.TOOL_DISABLED: "Change server config or use another command.",
        ErrorCode.RISH_NOT_FOUND: "Install or configure rish in Termux.",
        ErrorCode.RISH_PERMISSION_INVALID: "Fix rish file permissions and retry.",
        ErrorCode.SHIZUKU_NOT_RUNNING: "Start Shizuku and retry.",
        ErrorCode.TERMUX_API_NOT_AVAILABLE: "Install the Termux:API app and package.",
        ErrorCode.COMMAND_TIMEOUT: "Poll the job again or narrow the command.",
        ErrorCode.COMMAND_FAILED: "Inspect stderr or rerun a narrower command.",
        ErrorCode.ARTIFACT_NOT_FOUND: "Check the job or artifact path and retry.",
        ErrorCode.INTERNAL_ERROR: "Retry once or inspect the server logs.",
    }
    return suggestions.get(code, "Retry with a narrower command.")
