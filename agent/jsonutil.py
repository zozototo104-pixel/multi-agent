"""استخراج JSON من رد النموذج مع إعادة طلب تصحيح واحدة فقط."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any


_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def extract_json(text: str) -> Any:
    """استخراج أول قيمة JSON صالحة حتى لو أحاطها النموذج بنص أو code fence."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("رد النموذج فارغ ولا يحتوي JSON.")

    candidates = [match.group(1).strip() for match in _CODE_FENCE_RE.finditer(text)]
    candidates.append(text.strip())

    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        for index, char in enumerate(candidate):
            if char not in "[{":
                continue
            try:
                value, _ = decoder.raw_decode(candidate[index:])
                return value
            except json.JSONDecodeError:
                continue

    raise ValueError("تعذر استخراج JSON صالح من رد النموذج.")


def ask_json(
    ask_fn: Callable[..., str],
    role: str,
    prompt: str,
    system: str,
) -> Any:
    """طلب JSON، ومع الرد غير الصالح نطلب تصحيحه مرة واحدة فقط."""
    first = ask_fn(role, prompt, system=system)
    try:
        return extract_json(first)
    except ValueError as first_error:
        repair_prompt = (
            "الرد السابق لم يكن JSON صالحاً. أعد نفس الإجابة كـ JSON صالح فقط، "
            "بدون Markdown أو شرح.\n\nالرد السابق:\n" + first
        )
        second = ask_fn(role, repair_prompt, system=system)
        try:
            return extract_json(second)
        except ValueError as second_error:
            raise ValueError("النموذج أعاد JSON غير صالح مرتين.") from second_error
