"""تحويل طلب المستخدم إلى خطة Python منظمة وقابلة للتحقق."""

from __future__ import annotations

import os
import re

from models import ask

from .jsonutil import ask_json
from .schemas import Plan

PLANNER_ROLE = os.getenv("PLANNER_ROLE", "claude")

_SYSTEM = """أنت مخطط مشاريع برمجية. أرجع JSON فقط بلا Markdown أو شرح.
اللغة المدعومة في هذه المرحلة Python فقط.
يجب أن تحتوي الخطة دائماً ملف اختبار pytest واحداً على الأقل.
لا تقترح كوداً يحتاج اتصال شبكة وقت التشغيل أو الاختبار.
الشكل الإلزامي:
{"project_name":"snake_case","language":"python","description":"...","files":[{"path":"...","purpose":"..."}],"dependencies":["..."],"test_command":"pytest -q","run_command":"..."}
project_name يجب أن يكون snake_case آمناً، ومسارات الملفات نسبية داخل المشروع فقط."""


def make_plan(request: str) -> Plan:
    if not isinstance(request, str) or not request.strip():
        raise ValueError("الطلب لا يمكن أن يكون فارغاً.")

    data = ask_json(ask, PLANNER_ROLE, request.strip(), _SYSTEM)
    plan = Plan.from_dict(data)
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", plan.project_name):
        raise ValueError("project_name يجب أن يكون snake_case آمناً.")
    return plan
