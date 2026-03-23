import asyncio
import os
import subprocess
from typing import List, Optional, Tuple
from src.config import config
from src.errors import MCPError, ErrorCode

async def run_command(
    args: List[str],
    timeout: Optional[int] = None,
    env: Optional[dict] = None,
    cwd: Optional[str] = None
) -> Tuple[int, str, str]:
    if timeout is None:
        timeout = config.max_command_timeout_sec

    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=cwd
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            return process.returncode or 0, stdout.decode().strip(), stderr.decode().strip()
        except asyncio.TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            raise MCPError(
                ErrorCode.COMMAND_TIMEOUT,
                f"Command timed out after {timeout} seconds",
                {"command": " ".join(args)}
            )
    except FileNotFoundError as e:
        raise MCPError(
            ErrorCode.COMMAND_FAILED,
            f"Executable not found: {e}",
            {"command": " ".join(args)}
        )
    except Exception as e:
        raise MCPError(
            ErrorCode.COMMAND_FAILED,
            f"Failed to execute command: {str(e)}",
            {"command": " ".join(args)}
        )

async def run_command_binary(
    args: List[str],
    timeout: Optional[int] = None,
    env: Optional[dict] = None,
    cwd: Optional[str] = None
) -> Tuple[int, bytes, bytes]:
    if timeout is None:
        timeout = config.max_command_timeout_sec

    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=cwd
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            return process.returncode or 0, stdout, stderr
        except asyncio.TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            raise MCPError(
                ErrorCode.COMMAND_TIMEOUT,
                f"Command timed out after {timeout} seconds",
                {"command": " ".join(args)}
            )
    except FileNotFoundError as e:
        raise MCPError(
            ErrorCode.COMMAND_FAILED,
            f"Executable not found: {e}",
            {"command": " ".join(args)}
        )
    except Exception as e:
        raise MCPError(
            ErrorCode.COMMAND_FAILED,
            f"Failed to execute command: {str(e)}",
            {"command": " ".join(args)}
        )
