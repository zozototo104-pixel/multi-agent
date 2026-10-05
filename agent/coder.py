"""توليد ملفات المشروع وإصلاحها اعتماداً على نتائج Docker الحقيقية."""

from __future__ import annotations

import json
import os

from models import ask

from .jsonutil import ask_json
from .schemas import FileContent, Plan, RunResult

CODER_ROLE = os.getenv("CODER_ROLE", "claude")

_SYSTEM = """أنت كاتب كود Python. أرجع JSON صالحاً فقط بلا Markdown أو شرح.
الشكل الإلزامي: {"files":[{"path":"relative/path.py","content":"..."}]}
كل المسارات نسبية داخل المشروع.
ممنوع كتابة كود يجري أي اتصال شبكة.
ممنوع حذف الاختبارات أو تعطيلها أو تخطيها أو إضعاف assertions كي تنجح.
أصلح كود التطبيق بدلاً من التحايل على الاختبارات."""


def _parse_files(data: object) -> list[FileContent]:
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        raise ValueError("رد الكاتب يجب أن يحتوي قائمة files.")
    files = [FileContent.from_dict(item) for item in data["files"]]
    if not files:
        raise ValueError("النموذج لم يرجع أي ملفات.")
    return files


def write_code(plan: Plan) -> list[FileContent]:
    prompt = (
        "اكتب جميع ملفات هذه الخطة. يجب أن ترجع كل الملفات المذكورة في الخطة.\n"
        + json.dumps(plan.to_dict(), ensure_ascii=False)
    )
    return _parse_files(ask_json(ask, CODER_ROLE, prompt, _SYSTEM))


def fix_code(
    plan: Plan,
    files: list[FileContent],
    run_result: RunResult,
) -> list[FileContent]:
    current = [{"path": item.path, "content": item.content} for item in files]
    output = (run_result.stdout + "\n" + run_result.stderr)[-4000:]
    prompt = (
        "الاختبارات فشلت. أصلح السبب اعتماداً على المخرجات الحقيقية أدناه. "
        "أرجع الملفات المعدلة فقط، ولا تعد الملفات التي لم تتغير.\n\n"
        f"الخطة:\n{json.dumps(plan.to_dict(), ensure_ascii=False)}\n\n"
        f"الملفات الحالية:\n{json.dumps(current, ensure_ascii=False)}\n\n"
        f"exit_code: {run_result.exit_code}\n"
        f"timed_out: {run_result.timed_out}\n"
        f"آخر مخرجات التشغيل:\n{output}"
    )
    return _parse_files(ask_json(ask, CODER_ROLE, prompt, _SYSTEM))
