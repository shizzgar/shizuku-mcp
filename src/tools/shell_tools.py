import os
import re
import shlex
from pathlib import Path
from shutil import which
from typing import Any, Dict, Optional, Tuple

from src.config import config
from src.errors import MCPError, ErrorCode
from src.runners.rish_runner import rish_runner
from src.runners.subprocess_runner import (
    build_output_preview,
    command_job_manager,
    read_output_delta,
    SERVER_INSTANCE_ID,
)

ALLOWED_PRIVILEGE_MODES = {"auto", "termux", "rish"}
ALLOWED_CONTINUATIONS = {"start", "continue", "cancel"}

RISH_REQUIRED_PREFIXES = (
    "am ",
    "appops ",
    "cmd ",
    "content ",
    "dumpsys",
    "getprop ",
    "input ",
    "logcat",
    "monkey ",
    "pm ",
    "screenrecord",
    "screencap",
    "service ",
    "settings ",
    "setprop ",
    "svc ",
    "uiautomator",
)


def _validate_mode(value: str, allowed: set[str], field: str) -> None:
    if value not in allowed:
        raise MCPError(
            ErrorCode.INVALID_ARGUMENT,
            f"Unsupported {field}",
            {"field": field, "value": value, "allowed": sorted(allowed)},
        )


def _termux_shell_path() -> str:
    termux_bash = "/data/data/com.termux/files/usr/bin/bash"
    if os.path.exists(termux_bash):
        return termux_bash
    return which("bash") or "/bin/bash"


def _termux_env() -> Dict[str, str]:
    env = os.environ.copy()
    prefix = "/data/data/com.termux/files/usr"

    if os.path.exists(prefix):
        env["PATH"] = f"{prefix}/bin:{env.get('PATH', '')}"
        env["LD_LIBRARY_PATH"] = f"{prefix}/lib"
        env["PREFIX"] = prefix

    env["HOME"] = os.path.expanduser("~")
    return env


def _contains_denied_pattern(command: str) -> Optional[str]:
    for pattern in config.denied_shell_patterns:
        if pattern in command:
            return pattern
    return None


def _requires_rish(command: str) -> bool:
    normalized = command.strip()
    return normalized.startswith(RISH_REQUIRED_PREFIXES)


def _command_seems_interactive(command: str) -> bool:
    normalized = command.strip()
    patterns = (
        r"\btail\s+-f\b",
        r"\blogcat\b",
        r"(^|\s)top(\s|$)",
        r"\bwatch\s+",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


async def _resolve_execution_backend(
    command: str,
    privilege_mode: str,
    cwd: Optional[str],
) -> Tuple[str, list[str], Dict[str, str], Optional[str]]:
    if not config.enable_raw_shell:
        raise MCPError(ErrorCode.TOOL_DISABLED, "Raw shell is disabled in configuration.")

    denied_pattern = _contains_denied_pattern(command)
    if denied_pattern:
        raise MCPError(
            ErrorCode.TOOL_DISABLED,
            "Command contains an explicitly denied pattern.",
            {"pattern": denied_pattern},
        )

    if privilege_mode == "auto":
        selected_mode = "rish" if _requires_rish(command) else "termux"
    else:
        selected_mode = privilege_mode

    if selected_mode == "termux":
        shell_path = _termux_shell_path()
        return "termux", [shell_path, "-lc", command], _termux_env(), cwd

    rish_path = await rish_runner._find_rish()
    env = os.environ.copy()
    env["RISH_PRESERVE_ENV"] = str(config.rish_preserve_env)

    remote_command = command
    if cwd:
        remote_command = f"cd {shlex.quote(cwd)} && {command}"

    return "rish", [rish_path, "-c", remote_command], env, None


def _next_action_hint(status: str, finish_reason: Optional[str], stdout_preview: Dict[str, Any], stderr_preview: Dict[str, Any]) -> str:
    if status == "running":
        return "Command is still running. Call shell again with continuation='continue' and the same job_id."

    if status == "lost":
        return "This job was started by a previous server instance and can no longer be controlled. Start the command again."

    if status == "cancelled":
        return "Command was cancelled. Start a new job if you still need this work."

    if status == "killed_by_timeout":
        return "Command exceeded the hard timeout and was killed. Narrow the command or increase the server timeout budget."

    if finish_reason == "failed":
        return "Command exited with a non-zero code. Inspect stderr or rerun a narrower diagnostic command."

    if stdout_preview.get("truncated") or stderr_preview.get("truncated"):
        stdout_path = stdout_preview.get("path")
        return (
            "Output was sampled to protect context. Inspect narrower slices with the same shell tool, "
            f"for example: head/tail/sed -n/rg/jq against {stdout_path}."
        )

    return "Command completed within the inline budget."


def _stream_payload(
    path: Path,
    total_bytes: int,
    output_budget_chars: Optional[int],
    from_offset: Optional[int],
) -> Dict[str, Any]:
    if from_offset is None:
        return build_output_preview(
            path=path,
            total_bytes=total_bytes,
            inline_budget=output_budget_chars,
        ).to_dict()

    return read_output_delta(
        path=path,
        total_bytes=total_bytes,
        start_offset=from_offset,
        inline_budget=output_budget_chars,
    ).to_dict()


async def execute_android_shell(
    command: Optional[str] = None,
    privilege_mode: str = "auto",
    timeout_sec: Optional[int] = None,
    output_budget_chars: Optional[int] = None,
    continuation: str = "start",
    job_id: Optional[str] = None,
    cwd: Optional[str] = None,
    from_stdout_offset: Optional[int] = None,
    from_stderr_offset: Optional[int] = None,
) -> Dict[str, Any]:
    _validate_mode(privilege_mode, ALLOWED_PRIVILEGE_MODES, "privilege_mode")
    _validate_mode(continuation, ALLOWED_CONTINUATIONS, "continuation")
    if timeout_sec is not None and timeout_sec < 0:
        raise MCPError(ErrorCode.INVALID_ARGUMENT, "timeout_sec must be >= 0")
    if output_budget_chars is not None and output_budget_chars <= 0:
        raise MCPError(ErrorCode.INVALID_ARGUMENT, "output_budget_chars must be > 0")
    if from_stdout_offset is not None and from_stdout_offset < 0:
        raise MCPError(ErrorCode.INVALID_ARGUMENT, "from_stdout_offset must be >= 0")
    if from_stderr_offset is not None and from_stderr_offset < 0:
        raise MCPError(ErrorCode.INVALID_ARGUMENT, "from_stderr_offset must be >= 0")

    if continuation in {"continue", "cancel"}:
        if not job_id:
            raise MCPError(
                ErrorCode.INVALID_ARGUMENT,
                f"job_id is required when continuation='{continuation}'",
            )
        if continuation == "cancel":
            snapshot = await command_job_manager.terminate(job_id, reason="cancelled")
        else:
            snapshot = await command_job_manager.get_snapshot(job_id)
    else:
        if not command or not command.strip():
            raise MCPError(ErrorCode.INVALID_ARGUMENT, "command must be provided")

        selected_backend, args, env, resolved_cwd = await _resolve_execution_backend(
            command=command,
            privilege_mode=privilege_mode,
            cwd=cwd,
        )
        snapshot = await command_job_manager.start_job(
            args=args,
            command=command,
            env=env,
            cwd=resolved_cwd,
            backend=selected_backend,
        )

        sync_budget = timeout_sec if timeout_sec is not None else config.sync_command_budget_sec
        if _command_seems_interactive(command):
            sync_budget = min(sync_budget, 1)
        if sync_budget > 0:
            snapshot = await command_job_manager.wait_for(snapshot.job_id, sync_budget)

    stdout_preview = _stream_payload(
        path=Path(snapshot.stdout_path),
        total_bytes=snapshot.stdout_bytes,
        output_budget_chars=output_budget_chars,
        from_offset=from_stdout_offset,
    )
    stderr_preview = _stream_payload(
        path=Path(snapshot.stderr_path),
        total_bytes=snapshot.stderr_bytes,
        output_budget_chars=output_budget_chars,
        from_offset=from_stderr_offset,
    )

    job_state = "active" if snapshot.status == "running" and snapshot.owner_id == SERVER_INSTANCE_ID else "stale" if snapshot.status == "lost" else "terminal"

    return {
        "ok": True,
        "data": {
            "job_id": snapshot.job_id,
            "status": snapshot.status,
            "finish_reason": snapshot.finish_reason,
            "job_state": job_state,
            "job_owner": snapshot.owner_id,
            "server_instance_id": SERVER_INSTANCE_ID,
            "command": snapshot.command,
            "backend": snapshot.backend,
            "cwd": snapshot.cwd,
            "pid": snapshot.pid,
            "exit_code": snapshot.exit_code,
            "duration_ms": snapshot.duration_ms,
            "stdout": stdout_preview,
            "stderr": stderr_preview,
            "offsets": {
                "stdout": snapshot.stdout_bytes,
                "stderr": snapshot.stderr_bytes,
            },
            "artifacts": {
                "stdout_path": snapshot.stdout_path,
                "stderr_path": snapshot.stderr_path,
            },
            "next_action_hint": _next_action_hint(snapshot.status, snapshot.finish_reason, stdout_preview, stderr_preview),
        },
    }
