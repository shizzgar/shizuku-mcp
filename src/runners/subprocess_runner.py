import asyncio
import os
import subprocess
import logging
from typing import List, Optional, Tuple
from src.config import config
from src.errors import MCPError, ErrorCode

logger = logging.getLogger("android-shizuku-mcp")

async def run_command(
    args: List[str],
    timeout: Optional[int] = None,
    env: Optional[dict] = None,
    cwd: Optional[str] = None
) -> Tuple[int, str, str]:
    if timeout is None:
        timeout = config.max_command_timeout_sec

    cmd_str = " ".join(args)
    logger.info(f"EXEC: {cmd_str}")

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
            rc = process.returncode or 0
            logger.debug(f"DONE: {cmd_str} (RC: {rc})")
            return rc, stdout.decode().strip(), stderr.decode().strip()
        except asyncio.TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            logger.error(f"TIMEOUT: {cmd_str} after {timeout}s")
            raise MCPError(
                ErrorCode.COMMAND_TIMEOUT,
                f"Command timed out after {timeout} seconds",
                {"command": cmd_str}
            )
    except Exception as e:
        logger.error(f"FAIL: {cmd_str} - {str(e)}")
        raise MCPError(
            ErrorCode.COMMAND_FAILED,
            f"Failed to execute command: {str(e)}",
            {"command": cmd_str}
        )

async def run_command_binary(
    args: List[str],
    timeout: Optional[int] = None,
    env: Optional[dict] = None,
    cwd: Optional[str] = None
) -> Tuple[int, bytes, bytes]:
    if timeout is None:
        timeout = config.max_command_timeout_sec

    cmd_str = " ".join(args)
    logger.info(f"EXEC BINARY: {cmd_str}")

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
            rc = process.returncode or 0
            logger.debug(f"DONE BINARY: {cmd_str} (RC: {rc})")
            return rc, stdout, stderr
        except asyncio.TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            logger.error(f"TIMEOUT BINARY: {cmd_str} after {timeout}s")
            raise MCPError(
                ErrorCode.COMMAND_TIMEOUT,
                f"Command timed out after {timeout} seconds",
                {"command": cmd_str}
            )
    except Exception as e:
        logger.error(f"FAIL BINARY: {cmd_str} - {str(e)}")
        raise MCPError(
            ErrorCode.COMMAND_FAILED,
            f"Failed to execute command: {str(e)}",
            {"command": cmd_str}
        )
