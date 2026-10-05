"""تشغيل تثبيت واختبارات المشروع داخل Docker فقط."""

from __future__ import annotations

import shlex
import shutil
import subprocess
import time
from pathlib import Path

from .schemas import Plan, RunResult

IMAGE = "python:3.12-slim"
INSTALL_TIMEOUT = 180
TEST_TIMEOUT = 120


def _ensure_docker() -> None:
    if shutil.which("docker") is None:
        raise RuntimeError("Docker غير موجود. لا يمكن تشغيل الكود خارج sandbox كبديل.")


def _run(args: list[str], timeout: int) -> RunResult:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return RunResult(
            exit_code=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            duration=round(time.monotonic() - started, 3),
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return RunResult(
            exit_code=124,
            stdout=stdout,
            stderr=stderr,
            duration=round(time.monotonic() - started, 3),
            timed_out=True,
        )


def _safe_command(command: str, label: str) -> list[str]:
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        raise ValueError(f"{label} غير صالح: {exc}") from exc
    if not parts:
        raise ValueError(f"{label} لا يمكن أن يكون فارغاً.")
    return parts


def run_in_sandbox(project_dir: Path, plan: Plan) -> RunResult:
    _ensure_docker()
    project = str(project_dir.resolve())

    dependencies = [item for item in plan.dependencies if item and item != "pytest"]
    install_packages = ["pytest", *dependencies]
    install = _run(
        [
            "docker", "run", "--rm",
            "-v", f"{project}:/app",
            "-w", "/app",
            IMAGE,
            "python", "-m", "pip", "install",
            "--disable-pip-version-check",
            "--target", "/app/.agent_deps",
            *install_packages,
        ],
        INSTALL_TIMEOUT,
    )
    if install.exit_code != 0:
        return install

    test_parts = _safe_command(plan.test_command, "test_command")
    return _run(
        [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", "512m",
            "--cpus", "1",
            "--pids-limit", "256",
            "-e", "PYTHONPATH=/app/.agent_deps:/app",
            "-v", f"{project}:/app",
            "-w", "/app",
            IMAGE,
            *test_parts,
        ],
        TEST_TIMEOUT,
    )
