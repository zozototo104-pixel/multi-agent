"""حلقة MVP: تخطيط ← كتابة ← Docker ← إصلاح حتى النجاح أو نفاد المحاولات."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models import usage_summary

from .coder import fix_code, write_code
from .planner import make_plan
from .sandbox import run_in_sandbox
from .schemas import FileContent, RunResult
from .workspace import read_project_files, write_files


def _attempt_summary(number: int, result: RunResult) -> dict[str, Any]:
    return {
        "attempt": number,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "duration": result.duration,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
    }


def _write_report(project_dir: Path, report: dict[str, Any]) -> None:
    (project_dir / "agent_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build(request: str, max_attempts: int = 5) -> dict[str, Any]:
    if not 1 <= max_attempts <= 5:
        raise ValueError("max_attempts يجب أن يكون بين 1 و5.")

    print("🧠 تخطيط المشروع...")
    plan = make_plan(request)

    print("✍️ كتابة الملفات...")
    files = write_code(plan)
    project_dir = write_files(plan.project_name, files)

    attempts: list[dict[str, Any]] = []
    success = False

    for attempt in range(1, max_attempts + 1):
        print(f"🧪 تشغيل الاختبارات — المحاولة {attempt}/{max_attempts}...")
        result = run_in_sandbox(project_dir, plan)
        attempts.append(_attempt_summary(attempt, result))

        if result.exit_code == 0 and not result.timed_out:
            success = True
            print("✅ نجحت الاختبارات.")
            break

        if attempt == max_attempts:
            print("❌ انتهت المحاولات بدون نجاح الاختبارات.")
            break

        print(f"🔧 إصلاح #{attempt}...")
        current_files = read_project_files(project_dir)
        changed_files = fix_code(plan, current_files, result)
        write_files(plan.project_name, changed_files)

    report = {
        "request": request,
        "plan": plan.to_dict(),
        "attempts_count": len(attempts),
        "success": success,
        "attempts": attempts,
        "usage": usage_summary(),
    }
    _write_report(project_dir, report)
    return report
