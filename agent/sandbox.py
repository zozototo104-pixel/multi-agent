"""تشغيل تثبيت واختبارات المشروع داخل Docker فقط."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path

from .schemas import Plan, RunResult

IMAGE = "python:3.12-slim"
INSTALL_TIMEOUT = 180
TEST_TIMEOUT = 120
_DEPENDENCY_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._\-\[\]]*([<>=!~]=?[A-Za-z0-9.*]+)?$"
)


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


def _safe_test_command(command: str) -> list[str]:
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        raise ValueError(f"test_command غير صالح: {exc}") from exc
    if not parts:
        raise ValueError("test_command لا يمكن أن يكون فارغاً.")
    if parts[0] == "pytest":
        return parts
    if len(parts) >= 3 and parts[:3] == ["python", "-m", "pytest"]:
        return parts
    raise ValueError("test_command يجب أن يبدأ بـ pytest أو python -m pytest.")


def _safe_dependencies(dependencies: list[str]) -> list[str]:
    validated: list[str] = []
    for dependency in dependencies:
        if dependency == "pytest":
            continue
        if dependency.startswith("-") or not _DEPENDENCY_RE.fullmatch(dependency):
            raise ValueError(f"dependency غير آمن ومرفوض: {dependency}")
        validated.append(dependency)
    return validated


def _user_args() -> list[str]:
    return ["--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp"]


def run_in_sandbox(project_dir: Path, plan: Plan) -> RunResult:
    _ensure_docker()
    project = str(project_dir.resolve())
    dependencies = _safe_dependencies(plan.dependencies)
    test_parts = _safe_test_command(plan.test_command)
    install_packages = ["pytest", *dependencies]

    install = _run(
        [
            "docker", "run", "--rm",
            *_user_args(),
            "--memory", "1g",
            "--cpus", "1",
            "--pids-limit", "256",
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

    if test_parts[0] == "pytest":
        test_parts = ["pytest", "-p", "no:cacheprovider", *test_parts[1:]]
    else:
        test_parts = ["python", "-m", "pytest", "-p", "no:cacheprovider", *test_parts[3:]]

    return _run(
        [
            "docker", "run", "--rm",
            *_user_args(),
            "--network", "none",
            "--memory", "512m",
            "--cpus", "1",
            "--pids-limit", "256",
            "-e", "PYTHONPATH=/app/.agent_deps:/app",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-v", f"{project}:/app",
            "-w", "/app",
            IMAGE,
            *test_parts,
        ],
        TEST_TIMEOUT,
    )
