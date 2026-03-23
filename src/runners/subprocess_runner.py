import asyncio
import os
import logging
import time
from typing import List, Optional, Tuple
from src.config import config
from src.errors import MCPError, ErrorCode

logger = logging.getLogger("android-shizuku-mcp")

# Лимит текста, который мы готовы отправить в LLM за один раз (в символах)
MAX_OUTPUT_LENGTH = 30000 

def handle_large_output(stdout: str, stderr: str, cmd_name: str) -> str:
    """Обрезает вывод и сохраняет полный вариант в артефакты, если он слишком большой."""
    combined = stdout
    if stderr:
        combined += f"\n--- STDERR ---\n{stderr}"
    
    if len(combined) <= MAX_OUTPUT_LENGTH:
        return combined

    # Если слишком много текста — сохраняем в файл
    timestamp = int(time.time())
    filename = f"large_output_{cmd_name}_{timestamp}.txt"
    filepath = config.artifacts_dir / filename
    
    try:
        with open(filepath, "w") as f:
            f.write(f"COMMAND: {cmd_name}\n\n{combined}")
        
        summary = (
            f"\n⚠️ OUTPUT TOO LARGE ({len(combined)} chars). Truncated to {MAX_OUTPUT_LENGTH}.\n"
            f"Full output saved to artifacts: {filepath.absolute()}\n"
            f"Hint: Use 'grep', 'head', or 'tail' to filter data next time.\n"
            f"--- TRUNCATED OUTPUT START ---\n"
            f"{combined[:MAX_OUTPUT_LENGTH]}\n"
            f"--- TRUNCATED OUTPUT END ---"
        )
        return summary
    except Exception as e:
        return f"Error saving large output: {e}\n\nOriginal (truncated): {combined[:MAX_OUTPUT_LENGTH]}"

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
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
            rc = process.returncode or 0
            
            stdout = stdout_bytes.decode(errors='replace').strip()
            stderr = stderr_bytes.decode(errors='replace').strip()
            
            # Применяем умную обрезку
            final_output = handle_large_output(stdout, stderr, args[0].split("/")[-1])
            
            return rc, final_output, "" # Возвращаем обработанный текст как stdout
        except asyncio.TimeoutError:
            try: process.kill()
            except ProcessLookupError: pass
            raise MCPError(ErrorCode.COMMAND_TIMEOUT, f"Command timed out", {"command": cmd_str})
    except Exception as e:
        raise MCPError(ErrorCode.COMMAND_FAILED, str(e), {"command": cmd_str})

async def run_command_binary(
    args: List[str],
    timeout: Optional[int] = None,
    env: Optional[dict] = None,
    cwd: Optional[str] = None
) -> Tuple[int, bytes, bytes]:
    # Бинарные команды (скриншоты и т.д.) не обрезаем
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
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return process.returncode or 0, stdout, stderr
    except Exception as e:
        raise MCPError(ErrorCode.COMMAND_FAILED, str(e))
