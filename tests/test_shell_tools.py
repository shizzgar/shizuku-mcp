import asyncio
from pathlib import Path

from src.config import config
from src.runners.subprocess_runner import build_output_preview
from src.tools.shell_tools import execute_android_shell


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
    assert preview.sections[-1]["text"].endswith("C" * 120)


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
    assert data["stdout"]["truncated"] is True
    assert data["stdout"]["strategy"] in {"head_tail", "head_middle_tail"}
    assert Path(data["artifacts"]["stdout_path"]).exists()


def test_shell_continues_long_running_job(tmp_path):
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
        )
    )

    assert finished["data"]["status"] == "completed"
    assert finished["data"]["exit_code"] == 0
    assert "start" in (finished["data"]["stdout"]["inline"] or "")
    assert "done" in (finished["data"]["stdout"]["inline"] or "")
