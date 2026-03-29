import asyncio
import errno
import json
import logging
import os
import pty
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
SERVER_INSTANCE_ID = uuid.uuid4().hex[:12]
TERMINAL_JOB_STATES = {"completed", "failed", "cancelled", "killed_by_timeout", "lost"}
TERMINAL_SESSION_STATES = {"closed", "lost"}


@dataclass
class StreamStats:
    bytes_written: int = 0


@dataclass
class TextRead:
    text: str
    truncated: bool
    has_more: bool
    start_offset: int
    next_offset: int
    total_bytes: int
    path: str
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "truncated": self.truncated,
            "has_more": self.has_more,
            "start_offset": self.start_offset,
            "next_offset": self.next_offset,
            "total_bytes": self.total_bytes,
            "path": self.path,
            "message": self.message,
        }


@dataclass
class OutputPreview:
    mode: str
    strategy: str
    kind: str
    inline: Optional[str]
    truncated: bool
    has_more: bool
    start_offset: int
    end_offset: int
    next_offset: int
    total_bytes: int
    path: str
    message: Optional[str]
    char_count_estimate: Optional[int]
    line_count_estimate: Optional[int]
    nonempty_line_count_estimate: Optional[int]
    first_lines: List[str]
    last_lines: List[str]
    sample_lines: List[str]
    json_summary: Optional[Dict[str, Any]]
    sections: List[Dict[str, str]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "strategy": self.strategy,
            "kind": self.kind,
            "inline": self.inline,
            "truncated": self.truncated,
            "has_more": self.has_more,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "next_offset": self.next_offset,
            "total_bytes": self.total_bytes,
            "path": self.path,
            "message": self.message,
            "char_count_estimate": self.char_count_estimate,
            "line_count_estimate": self.line_count_estimate,
            "nonempty_line_count_estimate": self.nonempty_line_count_estimate,
            "first_lines": self.first_lines,
            "last_lines": self.last_lines,
            "sample_lines": self.sample_lines,
            "json_summary": self.json_summary,
            "sections": self.sections,
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
    owner_id: str
    pid: Optional[int]
    exit_code: Optional[int] = None
    completed_at: Optional[float] = None
    duration_ms: Optional[int] = None
    backend: Optional[str] = None
    cwd: Optional[str] = None
    finish_reason: Optional[str] = None

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
            "owner_id": self.owner_id,
            "pid": self.pid,
            "exit_code": self.exit_code,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "backend": self.backend,
            "cwd": self.cwd,
            "finish_reason": self.finish_reason,
        }


@dataclass
class SessionSnapshot:
    session_id: str
    status: str
    started_at: float
    output_path: str
    output_bytes: int
    owner_id: str
    pid: Optional[int]
    backend: Optional[str] = None
    cwd: Optional[str] = None
    exit_code: Optional[int] = None
    completed_at: Optional[float] = None
    duration_ms: Optional[int] = None
    read_offset: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "started_at": self.started_at,
            "output_path": self.output_path,
            "output_bytes": self.output_bytes,
            "owner_id": self.owner_id,
            "pid": self.pid,
            "backend": self.backend,
            "cwd": self.cwd,
            "exit_code": self.exit_code,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "read_offset": self.read_offset,
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
        owner_id: str,
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
        self.owner_id = owner_id
        self.exit_code: Optional[int] = None
        self.completed_at: Optional[float] = None
        self.status: str = "running"
        self.read_offset: int = 0
        self.finish_reason: Optional[str] = None

    def snapshot(self) -> JobSnapshot:
        end_time = self.completed_at or time.time()
        duration_ms = int((end_time - self.started_at) * 1000)
        return JobSnapshot(
            job_id=self.job_id,
            command=self.command,
            args=self.args,
            status=self.status,
            started_at=self.started_at,
            stdout_path=str(self.stdout_path),
            stderr_path=str(self.stderr_path),
            stdout_bytes=self.stdout_stats.bytes_written,
            stderr_bytes=self.stderr_stats.bytes_written,
            owner_id=self.owner_id,
            pid=self.process.pid,
            exit_code=self.exit_code,
            completed_at=self.completed_at,
            duration_ms=duration_ms,
            backend=self.backend,
            cwd=self.cwd,
            finish_reason=self.finish_reason,
        )


class RunningSession:
    def __init__(
        self,
        session_id: str,
        process: asyncio.subprocess.Process,
        master_fd: int,
        output_path: Path,
        read_task: asyncio.Task[Any],
        output_stats: StreamStats,
        started_at: float,
        backend: Optional[str],
        cwd: Optional[str],
        owner_id: str,
    ):
        self.session_id = session_id
        self.process = process
        self.master_fd = master_fd
        self.output_path = output_path
        self.read_task = read_task
        self.output_stats = output_stats
        self.started_at = started_at
        self.backend = backend
        self.cwd = cwd
        self.owner_id = owner_id
        self.exit_code: Optional[int] = None
        self.completed_at: Optional[float] = None
        self.status: str = "running"

    def snapshot(self) -> SessionSnapshot:
        end_time = self.completed_at or time.time()
        duration_ms = int((end_time - self.started_at) * 1000)
        return SessionSnapshot(
            session_id=self.session_id,
            status=self.status,
            started_at=self.started_at,
            output_path=str(self.output_path),
            output_bytes=self.output_stats.bytes_written,
            owner_id=self.owner_id,
            pid=self.process.pid,
            backend=self.backend,
            cwd=self.cwd,
            exit_code=self.exit_code,
            completed_at=self.completed_at,
            duration_ms=duration_ms,
            read_offset=self.read_offset,
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


async def _stream_pty_to_file(
    master_fd: int,
    path: Path,
    stats: StreamStats,
) -> None:
    loop = asyncio.get_running_loop()
    with open(path, "wb") as handle:
        while True:
            try:
                chunk = await loop.run_in_executor(None, os.read, master_fd, STREAM_CHUNK_SIZE)
            except OSError as exc:
                if exc.errno in {errno.EIO, errno.EBADF}:
                    break
                raise
            if not chunk:
                break
            handle.write(chunk)
            handle.flush()
            stats.bytes_written += len(chunk)


def _safe_decode(blob: bytes) -> str:
    return blob.decode(errors="replace")


def _close_fd(fd: int) -> None:
    try:
        os.close(fd)
    except OSError:
        return


def _read_window(path: Path, start: int, size: int) -> bytes:
    if size <= 0 or not path.exists():
        return b""

    with open(path, "rb") as handle:
        handle.seek(max(0, start))
        return handle.read(size)


def read_inline_text(
    path: Path,
    total_bytes: int,
    inline_budget: Optional[int] = None,
    prefer_tail: bool = False,
) -> TextRead:
    inline_budget = inline_budget or config.inline_output_char_budget

    if not path.exists():
        return TextRead("", False, False, 0, 0, 0, str(path))

    if total_bytes <= inline_budget:
        text = _safe_decode(_read_window(path, 0, total_bytes))
        return TextRead(text, False, False, 0, total_bytes, total_bytes, str(path))

    if prefer_tail:
        start = max(0, total_bytes - inline_budget)
        text = _safe_decode(_read_window(path, start, total_bytes - start))
        omitted = start
        marker = f"...[truncated {omitted} earlier bytes]...\n"
        return TextRead(marker + text, True, False, 0, total_bytes, total_bytes, str(path))

    marker = f"\n...[truncated {total_bytes - inline_budget} bytes]...\n"
    head_budget = max(1, (inline_budget - len(marker)) // 2)
    tail_budget = max(1, inline_budget - len(marker) - head_budget)
    head = _safe_decode(_read_window(path, 0, head_budget))
    tail_start = max(0, total_bytes - tail_budget)
    tail = _safe_decode(_read_window(path, tail_start, total_bytes - tail_start))
    return TextRead(head + marker + tail, True, False, 0, total_bytes, total_bytes, str(path))


def read_text_delta(
    path: Path,
    total_bytes: int,
    start_offset: int,
    inline_budget: Optional[int] = None,
) -> TextRead:
    inline_budget = inline_budget or config.inline_output_char_budget
    bounded_start = max(0, min(start_offset, total_bytes))

    if total_bytes <= bounded_start:
        return TextRead(
            "",
            False,
            False,
            bounded_start,
            bounded_start,
            total_bytes,
            str(path),
            message="no new output",
        )

    raw = _read_window(path, bounded_start, min(inline_budget, total_bytes - bounded_start))
    next_offset = bounded_start + len(raw)
    return TextRead(
        _safe_decode(raw),
        next_offset < total_bytes,
        next_offset < total_bytes,
        bounded_start,
        next_offset,
        total_bytes,
        str(path),
    )


def _trim_to_line_boundaries(
    text: str,
    trim_leading: bool,
    trim_trailing: bool,
) -> str:
    if "\n" not in text:
        return text

    if trim_leading and not text.startswith("\n"):
        first_break = text.find("\n")
        if first_break != -1:
            text = text[first_break + 1 :]

    if trim_trailing and not text.endswith("\n"):
        last_break = text.rfind("\n")
        if last_break != -1:
            text = text[:last_break]

    return text


def _read_text_slice(
    path: Path,
    start_offset: int,
    max_bytes: int,
    total_bytes: int,
    line_aware: bool = True,
) -> Tuple[str, int]:
    start_offset = max(0, min(start_offset, total_bytes))
    max_bytes = max(0, min(max_bytes, total_bytes - start_offset))
    raw = _read_window(path, start_offset, max_bytes)
    text = _safe_decode(raw)
    if line_aware:
        text = _trim_to_line_boundaries(
            text,
            trim_leading=start_offset > 0,
            trim_trailing=(start_offset + max_bytes) < total_bytes,
        )
    return text, start_offset + len(raw)


def _estimate_line_metrics(path: Path) -> Tuple[int, int]:
    if not path.exists():
        return 0, 0

    line_count = 0
    nonempty_line_count = 0
    carry = b""

    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            merged = carry + chunk
            parts = merged.split(b"\n")
            carry = parts.pop()
            for part in parts:
                line_count += 1
                if part.strip():
                    nonempty_line_count += 1

    if carry:
        line_count += 1
        if carry.strip():
            nonempty_line_count += 1

    return line_count, nonempty_line_count


def _collect_lines(text: str, limit: int = 3) -> List[str]:
    return [line for line in text.splitlines() if line][:limit]


def _collect_last_lines(text: str, limit: int = 3) -> List[str]:
    lines = [line for line in text.splitlines() if line]
    return lines[-limit:]


def _compact_json_value(value: Any, max_items: int = 5, depth: int = 0) -> Any:
    if depth >= 2:
        if isinstance(value, dict):
            return {"type": "object", "keys": len(value)}
        if isinstance(value, list):
            return {"type": "array", "items": len(value)}
        return value

    if isinstance(value, dict):
        items = list(value.items())[:max_items]
        return {key: _compact_json_value(item, max_items=max_items, depth=depth + 1) for key, item in items}
    if isinstance(value, list):
        return [_compact_json_value(item, max_items=max_items, depth=depth + 1) for item in value[:max_items]]
    return value


def _json_summary_from_text(text: str) -> Optional[Dict[str, Any]]:
    candidate = text.strip()
    if not candidate or candidate[0] not in "[{":
        return None

    try:
        parsed = json.loads(candidate)
    except Exception:
        return None

    if isinstance(parsed, dict):
        return {
            "summary_type": "object",
            "key_count": len(parsed),
            "preview": _compact_json_value(parsed),
        }
    if isinstance(parsed, list):
        return {
            "summary_type": "array",
            "item_count": len(parsed),
            "preview": _compact_json_value(parsed),
        }
    return {
        "summary_type": type(parsed).__name__,
        "preview": parsed,
    }


def _enrich_preview(preview: OutputPreview) -> OutputPreview:
    preview.char_count_estimate = preview.total_bytes

    if preview.kind == "empty":
        return preview

    candidate_text = preview.inline
    if candidate_text is None:
        candidate_text = "\n".join(section["text"] for section in preview.sections if section.get("text"))

    json_summary = _json_summary_from_text(candidate_text or "")
    if json_summary is not None:
        preview.kind = "json"
        preview.json_summary = json_summary
        return preview

    line_count, nonempty_line_count = _estimate_line_metrics(Path(preview.path))
    preview.line_count_estimate = line_count
    preview.nonempty_line_count_estimate = nonempty_line_count

    if line_count > 1:
        preview.kind = "lines"
        if preview.inline is not None:
            preview.first_lines = _collect_lines(preview.inline)
            preview.last_lines = _collect_last_lines(preview.inline)
            preview.sample_lines = preview.first_lines[:]
            return preview

        head_text = next((section["text"] for section in preview.sections if section["position"] == "head"), "")
        tail_text = next((section["text"] for section in preview.sections if section["position"] == "tail"), "")
        middle_text = next((section["text"] for section in preview.sections if section["position"] == "middle"), "")
        preview.first_lines = _collect_lines(head_text)
        preview.last_lines = _collect_last_lines(tail_text)
        preview.sample_lines = _collect_lines(middle_text or head_text)
        return preview

    preview.kind = "text"
    return preview


def build_output_preview(
    path: Path,
    total_bytes: int,
    inline_budget: Optional[int] = None,
    section_budget: Optional[int] = None,
) -> OutputPreview:
    inline_budget = inline_budget or config.inline_output_char_budget
    section_budget = section_budget or max(256, inline_budget // 4)

    if not path.exists():
        return OutputPreview(
            mode="inline",
            strategy="inline",
            kind="text",
            inline="",
            truncated=False,
            has_more=False,
            start_offset=0,
            end_offset=0,
            next_offset=0,
            total_bytes=0,
            path=str(path),
            message=None,
            char_count_estimate=0,
            line_count_estimate=0,
            nonempty_line_count_estimate=0,
            first_lines=[],
            last_lines=[],
            sample_lines=[],
            json_summary=None,
            sections=[],
        )

    if total_bytes <= inline_budget:
        inline, end_offset = _read_text_slice(path, 0, inline_budget, total_bytes, line_aware=False)
        return _enrich_preview(OutputPreview(
            mode="inline",
            strategy="inline",
            kind="text",
            inline=inline,
            truncated=False,
            has_more=False,
            start_offset=0,
            end_offset=end_offset,
            next_offset=total_bytes,
            total_bytes=total_bytes,
            path=str(path),
            message=None,
            char_count_estimate=None,
            line_count_estimate=None,
            nonempty_line_count_estimate=None,
            first_lines=[],
            last_lines=[],
            sample_lines=[],
            json_summary=None,
            sections=[],
        ))

    head_text, _ = _read_text_slice(path, 0, section_budget, total_bytes)
    sections = [{"position": "head", "text": head_text}]

    if total_bytes > section_budget * 2:
        middle_offset = max(0, (total_bytes // 2) - (section_budget // 2))
        middle_text, _ = _read_text_slice(path, middle_offset, section_budget, total_bytes)
        if middle_text:
            sections.append({"position": "middle", "text": middle_text})

    tail_offset = max(0, total_bytes - section_budget)
    tail_text, tail_end = _read_text_slice(path, tail_offset, section_budget, total_bytes)
    sections.append({"position": "tail", "text": tail_text})

    return _enrich_preview(OutputPreview(
        mode="sample",
        strategy="head_middle_tail" if len(sections) == 3 else "head_tail",
        kind="text",
        inline=None,
        truncated=True,
        has_more=False,
        start_offset=0,
        end_offset=tail_end,
        next_offset=total_bytes,
        total_bytes=total_bytes,
        path=str(path),
        message=None,
        char_count_estimate=None,
        line_count_estimate=None,
        nonempty_line_count_estimate=None,
        first_lines=[],
        last_lines=[],
        sample_lines=[],
        json_summary=None,
        sections=sections,
    ))


def read_output_delta(
    path: Path,
    total_bytes: int,
    start_offset: int,
    inline_budget: Optional[int] = None,
) -> OutputPreview:
    inline_budget = inline_budget or config.inline_output_char_budget
    bounded_start = max(0, min(start_offset, total_bytes))

    if total_bytes <= bounded_start:
        return OutputPreview(
            mode="delta",
            strategy="delta",
            kind="empty",
            inline="",
            truncated=False,
            has_more=False,
            start_offset=bounded_start,
            end_offset=bounded_start,
            next_offset=bounded_start,
            total_bytes=total_bytes,
            path=str(path),
            message="no new output",
            char_count_estimate=total_bytes,
            line_count_estimate=None,
            nonempty_line_count_estimate=None,
            first_lines=[],
            last_lines=[],
            sample_lines=[],
            json_summary=None,
            sections=[],
        )

    inline, end_offset = _read_text_slice(path, bounded_start, inline_budget, total_bytes, line_aware=False)
    has_more = end_offset < total_bytes
    return _enrich_preview(OutputPreview(
        mode="delta",
        strategy="delta",
        kind="text",
        inline=inline,
        truncated=has_more,
        has_more=has_more,
        start_offset=bounded_start,
        end_offset=end_offset,
        next_offset=end_offset,
        total_bytes=total_bytes,
        path=str(path),
        message=None,
        char_count_estimate=None,
        line_count_estimate=None,
        nonempty_line_count_estimate=None,
        first_lines=[],
        last_lines=[],
        sample_lines=[],
        json_summary=None,
        sections=[],
    ))


def _job_size(snapshot: JobSnapshot) -> int:
    return snapshot.stdout_bytes + snapshot.stderr_bytes


def _safe_unlink(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        return


def get_runtime_health() -> Dict[str, Any]:
    config.setup_dirs()
    meta_files = list(config.jobs_dir.glob("*.json"))
    job_count = 0
    terminal_job_count = 0
    storage_bytes = 0

    for meta_path in meta_files:
        try:
            snapshot = JobSnapshot(**json.loads(meta_path.read_text(encoding="utf-8")))
        except Exception:
            continue
        job_count += 1
        if snapshot.status in TERMINAL_JOB_STATES:
            terminal_job_count += 1
        storage_bytes += _job_size(snapshot)

    return {
        "instance_id": SERVER_INSTANCE_ID,
        "jobs_dir": str(config.jobs_dir.absolute()),
        "job_count": job_count,
        "terminal_job_count": terminal_job_count,
        "storage_bytes": storage_bytes,
        "max_completed_jobs": config.max_completed_jobs,
        "max_job_age_sec": config.max_job_age_sec,
        "max_runtime_storage_bytes": config.max_runtime_storage_bytes,
    }


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

    def _remove_job_files(self, job_id: str) -> None:
        stdout_path, stderr_path, meta_path = self._job_paths(job_id)
        _safe_unlink(stdout_path)
        _safe_unlink(stderr_path)
        _safe_unlink(meta_path)

    def cleanup_old_jobs(self) -> None:
        config.setup_dirs()
        now = time.time()
        snapshots: List[Tuple[JobSnapshot, Path]] = []

        for meta_path in config.jobs_dir.glob("*.json"):
            try:
                snapshot = JobSnapshot(**json.loads(meta_path.read_text(encoding="utf-8")))
            except Exception:
                _safe_unlink(meta_path)
                continue
            snapshots.append((snapshot, meta_path))

        terminal_snapshots = [
            item for item in snapshots if item[0].status in TERMINAL_JOB_STATES
        ]
        terminal_snapshots.sort(
            key=lambda item: item[0].completed_at or item[0].started_at,
            reverse=True,
        )

        total_storage = sum(_job_size(snapshot) for snapshot, _ in terminal_snapshots)
        retained = 0

        for snapshot, _ in terminal_snapshots:
            completed_at = snapshot.completed_at or snapshot.started_at
            age = now - completed_at
            should_delete = False

            if age > config.max_job_age_sec:
                should_delete = True
            elif retained >= config.max_completed_jobs:
                should_delete = True
            elif total_storage > config.max_runtime_storage_bytes:
                should_delete = True

            if should_delete:
                total_storage -= _job_size(snapshot)
                self._remove_job_files(snapshot.job_id)
                continue

            retained += 1

    async def _kill_after(self, job_id: str, timeout: int) -> None:
        try:
            await asyncio.sleep(timeout)
            job = self._jobs.get(job_id)
            if job is None or job.process.returncode is not None:
                return
            logger.warning("KILL[%s]: exceeded hard timeout of %ss", job_id, timeout)
            job.finish_reason = "killed_by_timeout"
            job.status = "killed_by_timeout"
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
        self.cleanup_old_jobs()

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
            owner_id=SERVER_INSTANCE_ID,
        )
        self._jobs[job_id] = job

        snapshot = job.snapshot()
        self._persist_snapshot(snapshot)
        return snapshot

    async def _finalize_if_done(self, job: RunningJob) -> JobSnapshot:
        if job.status in TERMINAL_JOB_STATES:
            snapshot = job.snapshot()
            self._persist_snapshot(snapshot)
            return snapshot

        if job.process.returncode is None:
            try:
                await asyncio.wait_for(job.process.wait(), timeout=0)
            except asyncio.TimeoutError:
                snapshot = job.snapshot()
                self._persist_snapshot(snapshot)
                return snapshot

        await asyncio.gather(job.stdout_task, job.stderr_task)
        if job.killer_task is not None:
            job.killer_task.cancel()

        job.exit_code = job.process.returncode or 0
        job.completed_at = time.time()
        if job.finish_reason == "cancelled":
            job.status = "cancelled"
        elif job.finish_reason == "killed_by_timeout":
            job.status = "killed_by_timeout"
        elif job.exit_code == 0:
            job.finish_reason = "completed"
            job.status = "completed"
        else:
            job.finish_reason = "failed"
            job.status = "failed"

        snapshot = job.snapshot()
        self._persist_snapshot(snapshot)
        return snapshot

    async def wait_for(self, job_id: str, timeout: int) -> JobSnapshot:
        job = self._jobs.get(job_id)
        if job is None:
            raise MCPError(
                ErrorCode.INVALID_ARGUMENT,
                "unknown job_id",
                {"job_id": job_id},
                retryable=False,
                suggested_next_action="Use an existing job_id or start a new command.",
            )

        try:
            await asyncio.wait_for(job.process.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            snapshot = job.snapshot()
            self._persist_snapshot(snapshot)
            return snapshot

        return await self._finalize_if_done(job)

    async def get_snapshot(self, job_id: str) -> JobSnapshot:
        job = self._jobs.get(job_id)
        if job is not None:
            return await self._finalize_if_done(job)

        _, _, meta_path = self._job_paths(job_id)
        if not meta_path.exists():
            raise MCPError(
                ErrorCode.INVALID_ARGUMENT,
                "unknown job_id",
                {"job_id": job_id},
                retryable=False,
                suggested_next_action="Use an existing job_id or start a new command.",
            )

        snapshot = JobSnapshot(**json.loads(meta_path.read_text(encoding="utf-8")))
        if snapshot.status == "running" and snapshot.owner_id != SERVER_INSTANCE_ID:
            snapshot.status = "lost"
            snapshot.finish_reason = "orphaned"
            snapshot.completed_at = snapshot.completed_at or time.time()
            snapshot.duration_ms = int((snapshot.completed_at - snapshot.started_at) * 1000)
            self._persist_snapshot(snapshot)
        return snapshot

    async def terminate(self, job_id: str, reason: str = "cancelled") -> JobSnapshot:
        job = self._jobs.get(job_id)
        if job is None:
            snapshot = await self.get_snapshot(job_id)
            if snapshot.status == "running":
                snapshot.status = "lost"
                snapshot.finish_reason = "orphaned"
                self._persist_snapshot(snapshot)
            return snapshot

        if job.process.returncode is None:
            job.finish_reason = reason
            job.status = reason
            job.process.kill()
            await job.process.wait()

        return await self._finalize_if_done(job)


command_job_manager = CommandJobManager()


class ShellSessionManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, RunningSession] = {}

    def _session_paths(self, session_id: str) -> Tuple[Path, Path]:
        output_path = config.sessions_dir / f"{session_id}.output.log"
        meta_path = config.sessions_dir / f"{session_id}.json"
        return output_path, meta_path

    def _persist_snapshot(self, snapshot: SessionSnapshot) -> None:
        _, meta_path = self._session_paths(snapshot.session_id)
        meta_path.write_text(json.dumps(snapshot.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")

    async def open_session(
        self,
        args: List[str],
        env: Optional[dict] = None,
        cwd: Optional[str] = None,
        backend: Optional[str] = None,
    ) -> SessionSnapshot:
        config.setup_dirs()
        session_id = uuid.uuid4().hex[:12]
        output_path, _ = self._session_paths(session_id)
        started_at = time.time()
        master_fd, slave_fd = pty.openpty()

        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env,
                cwd=cwd,
            )
        finally:
            _close_fd(slave_fd)

        output_stats = StreamStats()
        read_task = asyncio.create_task(_stream_pty_to_file(master_fd, output_path, output_stats))

        session = RunningSession(
            session_id=session_id,
            process=process,
            master_fd=master_fd,
            output_path=output_path,
            read_task=read_task,
            output_stats=output_stats,
            started_at=started_at,
            backend=backend,
            cwd=cwd,
            owner_id=SERVER_INSTANCE_ID,
        )
        self._sessions[session_id] = session

        snapshot = session.snapshot()
        self._persist_snapshot(snapshot)
        return snapshot

    async def _finalize_if_done(self, session: RunningSession) -> SessionSnapshot:
        if session.status in TERMINAL_SESSION_STATES:
            snapshot = session.snapshot()
            self._persist_snapshot(snapshot)
            return snapshot

        if session.process.returncode is None:
            try:
                await asyncio.wait_for(session.process.wait(), timeout=0)
            except asyncio.TimeoutError:
                snapshot = session.snapshot()
                self._persist_snapshot(snapshot)
                return snapshot

        await session.read_task
        _close_fd(session.master_fd)
        session.exit_code = session.process.returncode or 0
        session.completed_at = time.time()
        session.status = "closed"
        snapshot = session.snapshot()
        self._persist_snapshot(snapshot)
        return snapshot

    async def get_snapshot(self, session_id: str) -> SessionSnapshot:
        session = self._sessions.get(session_id)
        if session is not None:
            return await self._finalize_if_done(session)

        _, meta_path = self._session_paths(session_id)
        if not meta_path.exists():
            raise MCPError(
                ErrorCode.INVALID_ARGUMENT,
                "unknown session_id",
                {"session_id": session_id},
                retryable=False,
                suggested_next_action="Use an existing session_id or open a new session.",
            )

        snapshot = SessionSnapshot(**json.loads(meta_path.read_text(encoding="utf-8")))
        if snapshot.status == "running" and snapshot.owner_id != SERVER_INSTANCE_ID:
            snapshot.status = "lost"
            snapshot.completed_at = snapshot.completed_at or time.time()
            snapshot.duration_ms = int((snapshot.completed_at - snapshot.started_at) * 1000)
            self._persist_snapshot(snapshot)
        return snapshot

    async def write(self, session_id: str, data: str) -> SessionSnapshot:
        session = self._sessions.get(session_id)
        if session is None:
            return await self.get_snapshot(session_id)
        if session.process.returncode is not None:
            return await self._finalize_if_done(session)
        os.write(session.master_fd, data.encode())
        snapshot = session.snapshot()
        self._persist_snapshot(snapshot)
        return snapshot

    def set_read_offset(self, session_id: str, next_offset: int) -> None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.read_offset = max(0, next_offset)
            self._persist_snapshot(session.snapshot())
            return

        snapshot = SessionSnapshot(**json.loads(self._session_paths(session_id)[1].read_text(encoding="utf-8")))
        snapshot.read_offset = max(0, next_offset)
        self._persist_snapshot(snapshot)

    async def close(self, session_id: str) -> SessionSnapshot:
        session = self._sessions.get(session_id)
        if session is None:
            return await self.get_snapshot(session_id)

        if session.process.returncode is None:
            session.process.terminate()
            try:
                await asyncio.wait_for(session.process.wait(), timeout=2)
            except asyncio.TimeoutError:
                session.process.kill()
                await session.process.wait()

        return await self._finalize_if_done(session)


shell_session_manager = ShellSessionManager()


def _handle_legacy_large_output(stdout: str, stderr: str, cmd_name: str) -> str:
    combined = stdout
    if stderr:
        combined += f"\n--- STDERR ---\n{stderr}"

    if len(combined) <= LEGACY_MAX_OUTPUT_LENGTH:
        return combined

    timestamp = int(time.time())
    filename = f"large_output_{cmd_name}_{timestamp}.txt"
    filepath = config.artifacts_dir / filename
    filepath.write_text(f"COMMAND: {cmd_name}\n\n{combined}", encoding="utf-8")

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
            raise MCPError(
                ErrorCode.COMMAND_TIMEOUT,
                "command timed out",
                {"command": cmd_str},
                retryable=True,
                suggested_next_action="Poll the job again or narrow the command.",
            ) from exc

        await asyncio.gather(stdout_task, stderr_task)

        stdout = _safe_decode(_read_window(stdout_path, 0, stdout_stats.bytes_written))
        stderr = _safe_decode(_read_window(stderr_path, 0, stderr_stats.bytes_written))

        logger.info("DONE: %s (RC: %s)", cmd_str, process.returncode or 0)
        if len(stdout) + len(stderr) > LEGACY_MAX_OUTPUT_LENGTH:
            stdout = _handle_legacy_large_output(stdout, stderr, args[0].split("/")[-1])
            stderr = ""
        return process.returncode or 0, stdout, stderr
    except MCPError:
        raise
    except Exception as exc:
        raise MCPError(
            ErrorCode.COMMAND_FAILED,
            "command execution failed",
            {"command": cmd_str, "error": str(exc)},
            retryable=True,
            suggested_next_action="Inspect stderr or rerun a narrower command.",
        ) from exc


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
        raise MCPError(
            ErrorCode.COMMAND_FAILED,
            "binary command failed",
            {"error": str(exc)},
            retryable=True,
            suggested_next_action="Retry the command or inspect the server logs.",
        ) from exc
