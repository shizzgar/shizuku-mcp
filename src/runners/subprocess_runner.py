import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.config import config
from src.errors import MCPError, ErrorCode

logger = logging.getLogger("android-shizuku-mcp")

LEGACY_MAX_OUTPUT_LENGTH = 30000
STREAM_CHUNK_SIZE = 8192


@dataclass
class StreamStats:
    bytes_written: int = 0


@dataclass
class CommandPreview:
    inline: Optional[str]
    truncated: bool
    strategy: str
    sections: List[Dict[str, str]]
    total_bytes: int
    path: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inline": self.inline,
            "truncated": self.truncated,
            "strategy": self.strategy,
            "sections": self.sections,
            "total_bytes": self.total_bytes,
            "path": self.path,
        }


@dataclass
class JobSnapshot:
    job_id: str
    command: str
    args: List[str]
    status: str
    started_at: float
    stdout_path: str
    stderr_path: str
    stdout_bytes: int
    stderr_bytes: int
    exit_code: Optional[int] = None
    completed_at: Optional[float] = None
    duration_ms: Optional[int] = None
    backend: Optional[str] = None
    cwd: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "command": self.command,
            "args": self.args,
            "status": self.status,
            "started_at": self.started_at,
            "stdout_path": self.stdout_path,
            "stderr_path": self.stderr_path,
            "stdout_bytes": self.stdout_bytes,
            "stderr_bytes": self.stderr_bytes,
            "exit_code": self.exit_code,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "backend": self.backend,
            "cwd": self.cwd,
        }


class RunningJob:
    def __init__(
        self,
        job_id: str,
        process: asyncio.subprocess.Process,
        command: str,
        args: List[str],
        stdout_path: Path,
        stderr_path: Path,
        stdout_task: asyncio.Task[Any],
        stderr_task: asyncio.Task[Any],
        stdout_stats: StreamStats,
        stderr_stats: StreamStats,
        started_at: float,
        backend: Optional[str],
        cwd: Optional[str],
        killer_task: Optional[asyncio.Task[Any]],
    ):
        self.job_id = job_id
        self.process = process
        self.command = command
        self.args = args
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path
        self.stdout_task = stdout_task
        self.stderr_task = stderr_task
        self.stdout_stats = stdout_stats
        self.stderr_stats = stderr_stats
        self.started_at = started_at
        self.backend = backend
        self.cwd = cwd
        self.killer_task = killer_task
        self.exit_code: Optional[int] = None
        self.completed_at: Optional[float] = None

    def snapshot(self, status: Optional[str] = None) -> JobSnapshot:
        resolved_status = status
        if resolved_status is None:
            resolved_status = "completed" if self.exit_code is not None else "running"

        duration_ms: Optional[int] = None
        end_time = self.completed_at or time.time()
        if self.started_at:
            duration_ms = int((end_time - self.started_at) * 1000)

        return JobSnapshot(
            job_id=self.job_id,
            command=self.command,
            args=self.args,
            status=resolved_status,
            started_at=self.started_at,
            stdout_path=str(self.stdout_path),
            stderr_path=str(self.stderr_path),
            stdout_bytes=self.stdout_stats.bytes_written,
            stderr_bytes=self.stderr_stats.bytes_written,
            exit_code=self.exit_code,
            completed_at=self.completed_at,
            duration_ms=duration_ms,
            backend=self.backend,
            cwd=self.cwd,
        )


async def _stream_to_file(
    stream: Optional[asyncio.StreamReader],
    path: Path,
    stats: StreamStats,
) -> None:
    if stream is None:
        path.touch()
        return

    with open(path, "wb") as handle:
        while True:
            chunk = await stream.read(STREAM_CHUNK_SIZE)
            if not chunk:
                break
            handle.write(chunk)
            stats.bytes_written += len(chunk)


def _safe_decode(blob: bytes) -> str:
    return blob.decode(errors="replace")


def build_output_preview(
    path: Path,
    total_bytes: int,
    inline_budget: Optional[int] = None,
    section_budget: Optional[int] = None,
) -> CommandPreview:
    inline_budget = inline_budget or config.inline_output_char_budget
    section_budget = section_budget or config.preview_section_char_budget

    if not path.exists():
        return CommandPreview(
            inline="",
            truncated=False,
            strategy="inline",
            sections=[],
            total_bytes=0,
            path=str(path),
        )

    if total_bytes <= inline_budget:
        with open(path, "rb") as handle:
            inline = _safe_decode(handle.read(inline_budget))
        return CommandPreview(
            inline=inline,
            truncated=False,
            strategy="inline",
            sections=[],
            total_bytes=total_bytes,
            path=str(path),
        )

    with open(path, "rb") as handle:
        head = _safe_decode(handle.read(section_budget))

        middle = ""
        if total_bytes > section_budget * 2:
            middle_offset = max(0, (total_bytes // 2) - (section_budget // 2))
            handle.seek(middle_offset)
            middle = _safe_decode(handle.read(section_budget))

        tail_offset = max(0, total_bytes - section_budget)
        handle.seek(tail_offset)
        tail = _safe_decode(handle.read(section_budget))

    sections = [{"position": "head", "text": head}]
    if middle:
        sections.append({"position": "middle", "text": middle})
    sections.append({"position": "tail", "text": tail})

    return CommandPreview(
        inline=None,
        truncated=True,
        strategy="head_middle_tail" if middle else "head_tail",
        sections=sections,
        total_bytes=total_bytes,
        path=str(path),
    )


class CommandJobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, RunningJob] = {}

    def _job_paths(self, job_id: str) -> Tuple[Path, Path, Path]:
        stdout_path = config.jobs_dir / f"{job_id}.stdout.log"
        stderr_path = config.jobs_dir / f"{job_id}.stderr.log"
        meta_path = config.jobs_dir / f"{job_id}.json"
        return stdout_path, stderr_path, meta_path

    def _persist_snapshot(self, snapshot: JobSnapshot) -> None:
        _, _, meta_path = self._job_paths(snapshot.job_id)
        meta_path.write_text(json.dumps(snapshot.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")

    async def _kill_after(self, job_id: str, timeout: int) -> None:
        try:
            await asyncio.sleep(timeout)
            job = self._jobs.get(job_id)
            if job is None or job.process.returncode is not None:
                return
            logger.warning("KILL[%s]: exceeded hard timeout of %ss", job_id, timeout)
            job.process.kill()
            await job.process.wait()
        except asyncio.CancelledError:
            return

    async def start_job(
        self,
        args: List[str],
        command: str,
        env: Optional[dict] = None,
        cwd: Optional[str] = None,
        backend: Optional[str] = None,
        hard_timeout: Optional[int] = None,
    ) -> JobSnapshot:
        config.setup_dirs()

        job_id = uuid.uuid4().hex[:12]
        stdout_path, stderr_path, _ = self._job_paths(job_id)
        started_at = time.time()

        logger.info("EXEC[%s]: %s", job_id, " ".join(args))
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=cwd,
        )

        stdout_stats = StreamStats()
        stderr_stats = StreamStats()
        stdout_task = asyncio.create_task(_stream_to_file(process.stdout, stdout_path, stdout_stats))
        stderr_task = asyncio.create_task(_stream_to_file(process.stderr, stderr_path, stderr_stats))
        killer_task = None
        resolved_hard_timeout = hard_timeout if hard_timeout is not None else config.hard_kill_timeout_sec
        if resolved_hard_timeout > 0:
            killer_task = asyncio.create_task(self._kill_after(job_id, resolved_hard_timeout))

        job = RunningJob(
            job_id=job_id,
            process=process,
            command=command,
            args=args,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stdout_task=stdout_task,
            stderr_task=stderr_task,
            stdout_stats=stdout_stats,
            stderr_stats=stderr_stats,
            started_at=started_at,
            backend=backend,
            cwd=cwd,
            killer_task=killer_task,
        )
        self._jobs[job_id] = job

        snapshot = job.snapshot(status="running")
        self._persist_snapshot(snapshot)
        return snapshot

    async def _finalize_if_done(self, job: RunningJob) -> JobSnapshot:
        if job.exit_code is not None:
            snapshot = job.snapshot(status="completed")
            self._persist_snapshot(snapshot)
            return snapshot

        if job.process.returncode is None:
            try:
                await asyncio.wait_for(job.process.wait(), timeout=0)
            except asyncio.TimeoutError:
                snapshot = job.snapshot(status="running")
                self._persist_snapshot(snapshot)
                return snapshot

        await asyncio.gather(job.stdout_task, job.stderr_task)
        if job.killer_task is not None:
            job.killer_task.cancel()
        job.exit_code = job.process.returncode or 0
        job.completed_at = time.time()
        snapshot = job.snapshot(status="completed")
        self._persist_snapshot(snapshot)
        return snapshot

    async def wait_for(self, job_id: str, timeout: int) -> JobSnapshot:
        job = self._jobs.get(job_id)
        if job is None:
            raise MCPError(ErrorCode.INVALID_ARGUMENT, "Unknown job_id", {"job_id": job_id})

        try:
            await asyncio.wait_for(job.process.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            snapshot = job.snapshot(status="running")
            self._persist_snapshot(snapshot)
            return snapshot

        return await self._finalize_if_done(job)

    async def get_snapshot(self, job_id: str) -> JobSnapshot:
        job = self._jobs.get(job_id)
        if job is None:
            _, _, meta_path = self._job_paths(job_id)
            if meta_path.exists():
                data = json.loads(meta_path.read_text())
                return JobSnapshot(**data)
            raise MCPError(ErrorCode.INVALID_ARGUMENT, "Unknown job_id", {"job_id": job_id})

        return await self._finalize_if_done(job)

    async def terminate(self, job_id: str) -> JobSnapshot:
        job = self._jobs.get(job_id)
        if job is None:
            raise MCPError(ErrorCode.INVALID_ARGUMENT, "Unknown job_id", {"job_id": job_id})

        if job.process.returncode is None:
            job.process.kill()
            await job.process.wait()

        return await self._finalize_if_done(job)


command_job_manager = CommandJobManager()


def _handle_legacy_large_output(stdout: str, stderr: str, cmd_name: str) -> str:
    combined = stdout
    if stderr:
        combined += f"\n--- STDERR ---\n{stderr}"

    if len(combined) <= LEGACY_MAX_OUTPUT_LENGTH:
        return combined

    timestamp = int(time.time())
    filename = f"large_output_{cmd_name}_{timestamp}.txt"
    filepath = config.artifacts_dir / filename
    filepath.write_text(f"COMMAND: {cmd_name}\n\n{combined}")

    return (
        f"OUTPUT TOO LARGE ({len(combined)} chars). Truncated to {LEGACY_MAX_OUTPUT_LENGTH}.\n"
        f"Full output saved to artifacts: {filepath.absolute()}\n"
        f"Hint: use 'head', 'tail', 'sed -n', 'rg', or redirects to inspect a narrower slice.\n"
        f"--- TRUNCATED OUTPUT START ---\n"
        f"{combined[:LEGACY_MAX_OUTPUT_LENGTH]}\n"
        f"--- TRUNCATED OUTPUT END ---"
    )


async def run_command(
    args: List[str],
    timeout: Optional[int] = None,
    env: Optional[dict] = None,
    cwd: Optional[str] = None,
) -> Tuple[int, str, str]:
    if timeout is None:
        timeout = config.max_command_timeout_sec

    config.setup_dirs()
    cmd_str = " ".join(args)
    logger.info("EXEC: %s", cmd_str)

    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=cwd,
        )

        stdout_path = config.runtime_dir / f"legacy_{uuid.uuid4().hex[:12]}.stdout.log"
        stderr_path = config.runtime_dir / f"legacy_{uuid.uuid4().hex[:12]}.stderr.log"
        stdout_stats = StreamStats()
        stderr_stats = StreamStats()
        stdout_task = asyncio.create_task(_stream_to_file(process.stdout, stdout_path, stdout_stats))
        stderr_task = asyncio.create_task(_stream_to_file(process.stderr, stderr_path, stderr_stats))

        try:
            await asyncio.wait_for(process.wait(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            raise MCPError(ErrorCode.COMMAND_TIMEOUT, "Command timed out", {"command": cmd_str}) from exc

        await asyncio.gather(stdout_task, stderr_task)

        with open(stdout_path, "rb") as handle:
            stdout = _safe_decode(handle.read())
        with open(stderr_path, "rb") as handle:
            stderr = _safe_decode(handle.read())

        logger.info("DONE: %s (RC: %s)", cmd_str, process.returncode or 0)
        if len(stdout) + len(stderr) > LEGACY_MAX_OUTPUT_LENGTH:
            stdout = _handle_legacy_large_output(stdout, stderr, args[0].split("/")[-1])
            stderr = ""
        return process.returncode or 0, stdout, stderr
    except MCPError:
        raise
    except Exception as exc:
        raise MCPError(ErrorCode.COMMAND_FAILED, str(exc), {"command": cmd_str}) from exc


async def run_command_binary(
    args: List[str],
    timeout: Optional[int] = None,
    env: Optional[dict] = None,
    cwd: Optional[str] = None,
) -> Tuple[int, bytes, bytes]:
    if timeout is None:
        timeout = config.max_command_timeout_sec

    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return process.returncode or 0, stdout, stderr
    except Exception as exc:
        raise MCPError(ErrorCode.COMMAND_FAILED, str(exc)) from exc
