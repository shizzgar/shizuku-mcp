import asyncio
import json
import time
from pathlib import Path

from src.config import config
from src.errors import ErrorCode, MCPError
from src.runners import subprocess_runner
from src.runners.subprocess_runner import JobSnapshot, SessionSnapshot, read_inline_text, read_text_delta
from src.tools.shell_tools import execute_android_shell


def _configure_runtime(tmp_path: Path) -> None:
    config.artifacts_dir = tmp_path / "artifacts"
    config.logs_dir = tmp_path / "logs"
    config.runtime_dir = tmp_path / "runtime"
    config.jobs_dir = config.runtime_dir / "jobs"
    config.sessions_dir = config.runtime_dir / "sessions"
    config.setup_dirs()


def test_read_inline_text_returns_full_output_when_under_budget(tmp_path):
    _configure_runtime(tmp_path)
    path = tmp_path / "small.txt"
    path.write_text("hello\nworld\n", encoding="utf-8")

    result = read_inline_text(path, total_bytes=path.stat().st_size, inline_budget=100)

    assert result.text == "hello\nworld\n"
    assert result.truncated is False


def test_read_inline_text_truncates_only_over_budget(tmp_path):
    _configure_runtime(tmp_path)
    path = tmp_path / "large.txt"
    path.write_text("A" * 5000, encoding="utf-8")

    result = read_inline_text(path, total_bytes=path.stat().st_size, inline_budget=400)

    assert result.truncated is True
    assert "truncated" in result.text


def test_read_text_delta_reports_empty_delta(tmp_path):
    _configure_runtime(tmp_path)
    path = tmp_path / "delta.txt"
    path.write_text("hello\n", encoding="utf-8")

    result = read_text_delta(path, total_bytes=path.stat().st_size, start_offset=path.stat().st_size, inline_budget=100)

    assert result.text == ""
    assert result.message == "no new output"
    assert result.next_offset == path.stat().st_size


def test_exec_returns_raw_inline_output(tmp_path):
    _configure_runtime(tmp_path)

    result = asyncio.run(
        execute_android_shell(
            action="exec",
            command="python3 -c \"print('hello')\"",
            privilege_mode="termux",
            timeout_sec=2,
            output_budget_chars=200,
        )
    )

    data = result["data"]
    assert data["status"] == "completed"
    assert data["stdout"] == "hello\n"
    assert data["stderr"] == ""
    assert data["truncated"] is False


def test_exec_poll_returns_running_job_and_then_completion(tmp_path):
    _configure_runtime(tmp_path)

    started = asyncio.run(
        execute_android_shell(
            action="exec",
            command="python3 -c \"import time; print('start'); time.sleep(1.0); print('done')\"",
            privilege_mode="termux",
            timeout_sec=0,
            output_budget_chars=400,
        )
    )

    assert started["data"]["status"] == "running"
    job_id = started["data"]["job_id"]

    asyncio.run(asyncio.sleep(1.5))

    finished = asyncio.run(
        execute_android_shell(
            action="poll",
            job_id=job_id,
            privilege_mode="termux",
            output_budget_chars=400,
        )
    )

    assert finished["data"]["status"] == "completed"
    assert "start" in finished["data"]["stdout"]
    assert "done" in finished["data"]["stdout"]


def test_open_session_write_read_close_roundtrip(tmp_path):
    _configure_runtime(tmp_path)

    opened = asyncio.run(
        execute_android_shell(
            action="open_session",
            privilege_mode="termux",
            output_budget_chars=400,
        )
    )

    session_id = opened["data"]["session_id"]

    wrote = asyncio.run(
        execute_android_shell(
            action="write",
            session_id=session_id,
            input_text="printf 'hello-session\\n'",
            privilege_mode="termux",
            output_budget_chars=400,
        )
    )

    assert "hello-session" in wrote["data"]["output"]

    idle = asyncio.run(
        execute_android_shell(
            action="read",
            session_id=session_id,
            privilege_mode="termux",
            output_budget_chars=400,
        )
    )

    assert idle["data"]["message"] == "no new output"

    closed = asyncio.run(
        execute_android_shell(
            action="close",
            session_id=session_id,
            privilege_mode="termux",
            output_budget_chars=400,
        )
    )

    assert closed["data"]["status"] == "closed"


def test_auto_uses_session_for_interactive_command(tmp_path):
    _configure_runtime(tmp_path)

    result = asyncio.run(
        execute_android_shell(
            command="tail -f /dev/null",
            privilege_mode="termux",
            output_budget_chars=200,
        )
    )

    assert "session_id" in result["data"]
    asyncio.run(
        execute_android_shell(
            action="close",
            session_id=result["data"]["session_id"],
            privilege_mode="termux",
            output_budget_chars=200,
        )
    )


def test_explicit_rish_session_is_rejected(tmp_path):
    _configure_runtime(tmp_path)

    try:
        asyncio.run(
            execute_android_shell(
                action="open_session",
                privilege_mode="rish",
                output_budget_chars=200,
            )
        )
    except MCPError as exc:
        assert exc.code == ErrorCode.TOOL_DISABLED
    else:
        raise AssertionError("Expected MCPError for rish session")


def test_stale_job_becomes_lost_after_instance_change(tmp_path):
    _configure_runtime(tmp_path)

    snapshot = JobSnapshot(
        job_id="stale12345678",
        command="sleep 10",
        args=["bash", "-lc", "sleep 10"],
        status="running",
        started_at=time.time() - 30,
        stdout_path=str((config.jobs_dir / "stale12345678.stdout.log").absolute()),
        stderr_path=str((config.jobs_dir / "stale12345678.stderr.log").absolute()),
        stdout_bytes=0,
        stderr_bytes=0,
        owner_id="previous-instance",
        pid=99999,
        backend="termux",
        finish_reason=None,
    )
    meta_path = config.jobs_dir / "stale12345678.json"
    meta_path.write_text(json.dumps(snapshot.to_dict()), encoding="utf-8")
    Path(snapshot.stdout_path).write_text("", encoding="utf-8")
    Path(snapshot.stderr_path).write_text("", encoding="utf-8")

    found = asyncio.run(subprocess_runner.command_job_manager.get_snapshot("stale12345678"))

    assert found.status == "lost"
    assert found.finish_reason == "orphaned"


def test_stale_session_becomes_lost_after_instance_change(tmp_path):
    _configure_runtime(tmp_path)

    snapshot = SessionSnapshot(
        session_id="stalesession1",
        status="running",
        started_at=time.time() - 10,
        output_path=str((config.sessions_dir / "stalesession1.output.log").absolute()),
        output_bytes=0,
        owner_id="previous-instance",
        pid=77777,
        backend="termux",
        cwd=None,
    )
    meta_path = config.sessions_dir / "stalesession1.json"
    meta_path.write_text(json.dumps(snapshot.to_dict()), encoding="utf-8")
    Path(snapshot.output_path).write_text("", encoding="utf-8")

    found = asyncio.run(subprocess_runner.shell_session_manager.get_snapshot("stalesession1"))

    assert found.status == "lost"


def test_mcperror_to_dict_contains_normalized_fields():
    error = MCPError(
        ErrorCode.INVALID_ARGUMENT,
        "bad args",
        details={"field": "job_id"},
    )

    payload = error.to_dict()

    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
    assert payload["error"]["retryable"] is False
    assert payload["error"]["suggested_next_action"]
