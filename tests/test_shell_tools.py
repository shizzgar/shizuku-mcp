import asyncio
import json
import time
from pathlib import Path

from src.config import config
from src.errors import ErrorCode, MCPError
from src.runners import subprocess_runner
from src.runners.subprocess_runner import JobSnapshot, build_output_preview, read_output_delta
from src.tools.shell_tools import _next_action_hint, execute_android_shell


def _configure_runtime(tmp_path: Path) -> None:
    config.artifacts_dir = tmp_path / "artifacts"
    config.logs_dir = tmp_path / "logs"
    config.runtime_dir = tmp_path / "runtime"
    config.jobs_dir = config.runtime_dir / "jobs"
    config.setup_dirs()


def test_build_output_preview_samples_large_output(tmp_path):
    _configure_runtime(tmp_path)
    path = tmp_path / "large.txt"
    path.write_text("A" * 600 + "B" * 600 + "C" * 600, encoding="utf-8")

    preview = build_output_preview(path, total_bytes=path.stat().st_size, inline_budget=300, section_budget=120)

    assert preview.truncated is True
    assert preview.strategy == "head_middle_tail"
    assert [section["position"] for section in preview.sections] == ["head", "middle", "tail"]
    assert preview.sections[0]["text"].startswith("A")
    assert preview.sections[-1]["text"].strip().endswith("C")


def test_build_output_preview_detects_json_output(tmp_path):
    _configure_runtime(tmp_path)
    path = tmp_path / "data.json"
    path.write_text("{\"ok\": true, \"items\": [1, 2, 3], \"name\": \"demo\"}", encoding="utf-8")

    preview = build_output_preview(path, total_bytes=path.stat().st_size, inline_budget=400, section_budget=120)

    assert preview.kind == "json"
    assert preview.json_summary is not None
    assert preview.json_summary["summary_type"] == "object"


def test_shell_returns_sampled_output_for_large_stdout(tmp_path):
    _configure_runtime(tmp_path)

    result = asyncio.run(
        execute_android_shell(
            command="python3 -c \"print('A' * 2500)\"",
            privilege_mode="termux",
            timeout_sec=2,
            output_budget_chars=400,
        )
    )

    data = result["data"]
    assert data["status"] == "completed"
    assert data["finish_reason"] == "completed"
    assert data["stdout"]["truncated"] is True
    assert data["stdout"]["strategy"] in {"head_tail", "head_middle_tail"}
    assert Path(data["artifacts"]["stdout_path"]).exists()


def test_read_output_delta_reports_empty_delta(tmp_path):
    _configure_runtime(tmp_path)
    path = tmp_path / "delta.txt"
    path.write_text("hello\n", encoding="utf-8")

    preview = read_output_delta(path, total_bytes=path.stat().st_size, start_offset=path.stat().st_size, inline_budget=100)

    assert preview.kind == "empty"
    assert preview.message == "no new output"
    assert preview.next_offset == path.stat().st_size


def test_shell_continues_long_running_job_with_offsets(tmp_path):
    _configure_runtime(tmp_path)

    started = asyncio.run(
        execute_android_shell(
            command="python3 -c \"import time; print('start'); time.sleep(1.5); print('done')\"",
            privilege_mode="termux",
            timeout_sec=0,
        )
    )

    assert started["data"]["status"] == "running"
    job_id = started["data"]["job_id"]

    asyncio.run(asyncio.sleep(2))

    finished = asyncio.run(
        execute_android_shell(
            continuation="continue",
            job_id=job_id,
            privilege_mode="termux",
            from_stdout_offset=0,
        )
    )

    assert finished["data"]["status"] == "completed"
    assert finished["data"]["exit_code"] == 0
    assert finished["data"]["stdout"]["mode"] == "delta"
    assert "start" in (finished["data"]["stdout"]["inline"] or "")
    assert finished["data"]["offsets"]["stdout"] >= finished["data"]["stdout"]["next_offset"]


def test_shell_can_cancel_running_job(tmp_path):
    _configure_runtime(tmp_path)

    started = asyncio.run(
        execute_android_shell(
            command="python3 -c \"import time; time.sleep(10)\"",
            privilege_mode="termux",
            timeout_sec=0,
        )
    )

    cancelled = asyncio.run(
        execute_android_shell(
            continuation="cancel",
            job_id=started["data"]["job_id"],
            privilege_mode="termux",
        )
    )

    assert cancelled["data"]["status"] == "cancelled"
    assert cancelled["data"]["finish_reason"] == "cancelled"


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
    assert found.owner_id != subprocess_runner.SERVER_INSTANCE_ID


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


def test_next_action_hint_detects_internal_apktool_aapt2_failure():
    hint = _next_action_hint(
        status="failed",
        finish_reason="failed",
        primary_stream="stderr",
        stdout_preview={"inline": "", "total_bytes": 0},
        stderr_preview={
            "inline": (
                "Execution failed: [/data/data/com.termux/files/usr/tmp/aapt2_123.tmp, compile]\n"
                "Syntax error: \"(\" unexpected\n"
            ),
            "total_bytes": 120,
        },
    )

    assert "--aapt /data/data/com.termux/files/usr/bin/aapt2" in hint


def test_next_action_hint_detects_leading_dollar_resource_names():
    hint = _next_action_hint(
        status="failed",
        finish_reason="failed",
        primary_stream="stderr",
        stdout_preview={"inline": "", "total_bytes": 0},
        stderr_preview={
            "inline": "error: resource 'drawable/$avd_hide_password__0' has invalid entry name '$avd_hide_password__0.",
            "total_bytes": 101,
        },
    )

    assert "leading-$ resource name" in hint
