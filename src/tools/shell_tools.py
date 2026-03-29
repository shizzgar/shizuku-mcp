import asyncio
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
    SERVER_INSTANCE_ID,
    command_job_manager,
    read_inline_text,
    read_text_delta,
    shell_session_manager,
)

ALLOWED_ACTIONS = {"auto", "exec", "poll", "open_session", "write", "read", "resize", "close", "cancel"}
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
        r"(^|\s)(bash|sh|zsh|fish)(\s|$)",
        r"\bpython3?\s*$",
        r"\bnode\s*$",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


async def _resolve_exec_backend(
    command: str,
    privilege_mode: str,
    cwd: Optional[str],
) -> Tuple[str, list[str], Dict[str, str], Optional[str]]:
    if not config.enable_raw_shell:
        raise MCPError(ErrorCode.TOOL_DISABLED, "Raw shell is disabled in configuration.")

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


async def _resolve_session_backend(
    privilege_mode: str,
    cwd: Optional[str],
) -> Tuple[str, list[str], Dict[str, str], Optional[str]]:
    if not config.enable_raw_shell:
        raise MCPError(ErrorCode.TOOL_DISABLED, "Raw shell is disabled in configuration.")

    selected_mode = privilege_mode
    if selected_mode == "auto":
        selected_mode = "termux"

    if selected_mode == "rish":
        raise MCPError(
            ErrorCode.TOOL_DISABLED,
            "Persistent rish sessions are not supported.",
            retryable=False,
            suggested_next_action="Use action='exec' with privilege_mode='rish', or open a termux session instead.",
        )

    shell_path = _termux_shell_path()
    return "termux", [shell_path, "-li"], _termux_env(), cwd


def _signature_hint(text: str) -> Optional[str]:
    if "Syntax error: \"(\" unexpected" in text and "aapt2_" in text:
        return "apktool used its temp aapt2 binary. Retry with --aapt /data/data/com.termux/files/usr/bin/aapt2."
    if "invalid entry name '$" in text:
        return "aapt2 rejected a leading-$ resource name. Fix filenames and @drawable/$... refs before rebuilding."
    return None


def _exec_hint(status: str, stderr_text: str, stdout_text: str) -> Optional[str]:
    combined = "\n".join(part for part in (stderr_text, stdout_text) if part)
    signature = _signature_hint(combined)
    if signature:
        return signature
    if status == "running":
        return "Command is still running. Poll it with the same job_id or cancel it."
    if status == "killed_by_timeout":
        return "Command hit the hard timeout. Poll artifacts or rerun it in a narrower form."
    if status == "lost":
        return "This job belonged to a previous server instance. Start it again."
    if status == "failed" and stderr_text:
        return "Command failed. Inspect stderr first."
    return None


def _session_hint(output_text: str) -> Optional[str]:
    return _signature_hint(output_text)


def _action_from_legacy(
    action: str,
    continuation: str,
    job_id: Optional[str],
    from_stdout_offset: Optional[int],
    from_stderr_offset: Optional[int],
) -> str:
    if action != "auto":
        return action
    if continuation == "continue" or job_id or from_stdout_offset is not None or from_stderr_offset is not None:
        return "poll"
    if continuation == "cancel":
        return "cancel"
    return "auto"


def _build_exec_payload(snapshot: Any, output_budget_chars: Optional[int], delta: bool = False,
                        from_stdout_offset: Optional[int] = None, from_stderr_offset: Optional[int] = None) -> Dict[str, Any]:
    if delta:
        stdout_start = from_stdout_offset if from_stdout_offset is not None else snapshot.stdout_bytes
        stderr_start = from_stderr_offset if from_stderr_offset is not None else snapshot.stderr_bytes
        stdout = read_text_delta(Path(snapshot.stdout_path), snapshot.stdout_bytes, stdout_start, output_budget_chars)
        stderr = read_text_delta(Path(snapshot.stderr_path), snapshot.stderr_bytes, stderr_start, output_budget_chars)
    else:
        stdout = read_inline_text(Path(snapshot.stdout_path), snapshot.stdout_bytes, output_budget_chars, prefer_tail=False)
        stderr = read_inline_text(Path(snapshot.stderr_path), snapshot.stderr_bytes, output_budget_chars, prefer_tail=True)

    hint = _exec_hint(snapshot.status, stderr.text, stdout.text)
    data: Dict[str, Any] = {
        "job_id": snapshot.job_id,
        "status": snapshot.status,
        "exit_code": snapshot.exit_code,
        "finish_reason": snapshot.finish_reason,
        "backend": snapshot.backend,
        "cwd": snapshot.cwd,
        "pid": snapshot.pid,
        "duration_ms": snapshot.duration_ms,
        "stdout": stdout.text,
        "stderr": stderr.text,
        "stdout_truncated": stdout.truncated,
        "stderr_truncated": stderr.truncated,
        "truncated": stdout.truncated or stderr.truncated,
        "has_more": snapshot.status == "running" or stdout.has_more or stderr.has_more,
        "stdout_offset": snapshot.stdout_bytes,
        "stderr_offset": snapshot.stderr_bytes,
    }
    if data["truncated"] or snapshot.status == "running":
        data["stdout_path"] = snapshot.stdout_path
        data["stderr_path"] = snapshot.stderr_path
    if hint:
        data["next_action_hint"] = hint
    return data


def _build_session_read_payload(
    snapshot: Any,
    output_budget_chars: Optional[int],
    from_offset: Optional[int] = None,
) -> Dict[str, Any]:
    start_offset = snapshot.read_offset if from_offset is None else from_offset
    output = read_text_delta(Path(snapshot.output_path), snapshot.output_bytes, start_offset, output_budget_chars)
    shell_session_manager.set_read_offset(snapshot.session_id, output.next_offset)
    hint = _session_hint(output.text)
    data: Dict[str, Any] = {
        "session_id": snapshot.session_id,
        "status": snapshot.status,
        "backend": snapshot.backend,
        "cwd": snapshot.cwd,
        "pid": snapshot.pid,
        "exit_code": snapshot.exit_code,
        "duration_ms": snapshot.duration_ms,
        "output": output.text,
        "truncated": output.truncated,
        "has_more": output.has_more,
        "offset": output.next_offset,
        "output_path": snapshot.output_path,
    }
    if output.message:
        data["message"] = output.message
    if hint:
        data["next_action_hint"] = hint
    return data


async def _open_session_response(
    privilege_mode: str,
    cwd: Optional[str],
    command: Optional[str],
    output_budget_chars: Optional[int],
) -> Dict[str, Any]:
    selected_backend, args, env, resolved_cwd = await _resolve_session_backend(
        privilege_mode=privilege_mode,
        cwd=cwd,
    )
    snapshot = await shell_session_manager.open_session(
        args=args,
        env=env,
        cwd=resolved_cwd,
        backend=selected_backend,
    )

    if command and command.strip():
        input_text = command if command.endswith("\n") else f"{command}\n"
        before_offset = snapshot.output_bytes
        await shell_session_manager.write(snapshot.session_id, input_text)
        await asyncio.sleep(config.session_open_wait_ms / 1000)
        snapshot = await shell_session_manager.get_snapshot(snapshot.session_id)
        data = _build_session_read_payload(snapshot, output_budget_chars, from_offset=before_offset)
    else:
        await asyncio.sleep(config.session_open_wait_ms / 1000)
        snapshot = await shell_session_manager.get_snapshot(snapshot.session_id)
        data = _build_session_read_payload(snapshot, output_budget_chars, from_offset=0)

    data.update({
        "session_id": snapshot.session_id,
        "backend": snapshot.backend,
        "cwd": snapshot.cwd,
    })
    return {"ok": True, "data": data}


async def execute_android_shell(
    command: Optional[str] = None,
    privilege_mode: str = "auto",
    timeout_sec: Optional[int] = None,
    output_budget_chars: Optional[int] = None,
    action: str = "auto",
    continuation: str = "start",
    job_id: Optional[str] = None,
    session_id: Optional[str] = None,
    cwd: Optional[str] = None,
    input_text: Optional[str] = None,
    append_newline: bool = True,
    from_offset: Optional[int] = None,
    from_stdout_offset: Optional[int] = None,
    from_stderr_offset: Optional[int] = None,
) -> Dict[str, Any]:
    _validate_mode(action, ALLOWED_ACTIONS, "action")
    _validate_mode(privilege_mode, ALLOWED_PRIVILEGE_MODES, "privilege_mode")
    _validate_mode(continuation, ALLOWED_CONTINUATIONS, "continuation")
    if timeout_sec is not None and timeout_sec < 0:
        raise MCPError(ErrorCode.INVALID_ARGUMENT, "timeout_sec must be >= 0")
    if output_budget_chars is not None and output_budget_chars <= 0:
        raise MCPError(ErrorCode.INVALID_ARGUMENT, "output_budget_chars must be > 0")
    if from_offset is not None and from_offset < 0:
        raise MCPError(ErrorCode.INVALID_ARGUMENT, "from_offset must be >= 0")
    if from_stdout_offset is not None and from_stdout_offset < 0:
        raise MCPError(ErrorCode.INVALID_ARGUMENT, "from_stdout_offset must be >= 0")
    if from_stderr_offset is not None and from_stderr_offset < 0:
        raise MCPError(ErrorCode.INVALID_ARGUMENT, "from_stderr_offset must be >= 0")

    action = _action_from_legacy(action, continuation, job_id, from_stdout_offset, from_stderr_offset)

    if action == "auto":
        if not command or not command.strip():
            raise MCPError(ErrorCode.INVALID_ARGUMENT, "command must be provided")
        action = "open_session" if _command_seems_interactive(command) else "exec"

    if action == "exec":
        if not command or not command.strip():
            raise MCPError(ErrorCode.INVALID_ARGUMENT, "command must be provided")
        selected_backend, args, env, resolved_cwd = await _resolve_exec_backend(
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
        if sync_budget > 0:
            snapshot = await command_job_manager.wait_for(snapshot.job_id, sync_budget)
        return {"ok": True, "data": _build_exec_payload(snapshot, output_budget_chars)}

    if action == "poll":
        if not job_id:
            raise MCPError(
                ErrorCode.INVALID_ARGUMENT,
                "job_id is required for action='poll'",
                retryable=False,
                suggested_next_action="Pass an existing job_id from a previous exec call.",
            )
        snapshot = await command_job_manager.get_snapshot(job_id)
        return {
            "ok": True,
            "data": _build_exec_payload(
                snapshot,
                output_budget_chars,
                delta=(from_stdout_offset is not None or from_stderr_offset is not None),
                from_stdout_offset=from_stdout_offset,
                from_stderr_offset=from_stderr_offset,
            ),
        }

    if action == "open_session":
        return await _open_session_response(privilege_mode, cwd, command, output_budget_chars)

    if action == "write":
        if not session_id:
            raise MCPError(
                ErrorCode.INVALID_ARGUMENT,
                "session_id is required for action='write'",
                retryable=False,
                suggested_next_action="Open a session first, then write to it.",
            )
        payload = input_text if input_text is not None else command
        if payload is None:
            raise MCPError(
                ErrorCode.INVALID_ARGUMENT,
                "input_text or command is required for action='write'",
                retryable=False,
                suggested_next_action="Pass the text you want to send to the session.",
            )
        snapshot_before = await shell_session_manager.get_snapshot(session_id)
        if snapshot_before.status != "running":
            return {"ok": True, "data": _build_session_read_payload(snapshot_before, output_budget_chars, from_offset=from_offset)}
        data = payload if not append_newline else (payload if payload.endswith("\n") else f"{payload}\n")
        await shell_session_manager.write(session_id, data)
        await asyncio.sleep(config.session_open_wait_ms / 1000)
        snapshot_after = await shell_session_manager.get_snapshot(session_id)
        return {
            "ok": True,
            "data": _build_session_read_payload(snapshot_after, output_budget_chars, from_offset=snapshot_before.output_bytes),
        }

    if action == "read":
        if not session_id:
            raise MCPError(
                ErrorCode.INVALID_ARGUMENT,
                "session_id is required for action='read'",
                retryable=False,
                suggested_next_action="Open a session first, then read from it.",
            )
        snapshot = await shell_session_manager.get_snapshot(session_id)
        return {"ok": True, "data": _build_session_read_payload(snapshot, output_budget_chars, from_offset=from_offset)}

    if action == "close":
        if not session_id:
            raise MCPError(
                ErrorCode.INVALID_ARGUMENT,
                "session_id is required for action='close'",
                retryable=False,
                suggested_next_action="Pass the session_id you want to close.",
            )
        snapshot = await shell_session_manager.close(session_id)
        output = read_inline_text(Path(snapshot.output_path), snapshot.output_bytes, output_budget_chars)
        data: Dict[str, Any] = {
            "session_id": snapshot.session_id,
            "status": snapshot.status,
            "backend": snapshot.backend,
            "cwd": snapshot.cwd,
            "pid": snapshot.pid,
            "exit_code": snapshot.exit_code,
            "duration_ms": snapshot.duration_ms,
            "output": output.text,
            "truncated": output.truncated,
            "has_more": False,
            "offset": snapshot.read_offset,
            "output_path": snapshot.output_path,
        }
        hint = _session_hint(output.text)
        if hint:
            data["next_action_hint"] = hint
        return {"ok": True, "data": data}

    if action == "cancel":
        if session_id:
            snapshot = await shell_session_manager.close(session_id)
            return {
                "ok": True,
                "data": {
                    "session_id": snapshot.session_id,
                    "status": snapshot.status,
                    "backend": snapshot.backend,
                    "cwd": snapshot.cwd,
                    "exit_code": snapshot.exit_code,
                    "duration_ms": snapshot.duration_ms,
                    "output_path": snapshot.output_path,
                },
            }
        if not job_id:
            raise MCPError(
                ErrorCode.INVALID_ARGUMENT,
                "job_id or session_id is required for action='cancel'",
                retryable=False,
                suggested_next_action="Pass a running job_id or session_id to cancel.",
            )
        snapshot = await command_job_manager.terminate(job_id, reason="cancelled")
        return {"ok": True, "data": _build_exec_payload(snapshot, output_budget_chars)}

    if action == "resize":
        raise MCPError(
            ErrorCode.TOOL_DISABLED,
            "PTY resize is not implemented yet.",
            retryable=False,
            suggested_next_action="Use open_session, write, read, close, or exec.",
        )

    raise MCPError(ErrorCode.INVALID_ARGUMENT, "unsupported shell action")
