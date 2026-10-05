"""طبقة موحدة لاستدعاء نماذج المشروع عبر LiteLLM."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import litellm

import config

_call_count = 0
_total_input_tokens = 0
_total_output_tokens = 0


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    """قراءة قيمة من dict أو كائن LiteLLM بطريقة آمنة."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _usage_tokens(response: Any) -> tuple[int, int]:
    usage = _get_value(response, "usage", {}) or {}
    prompt_tokens = int(_get_value(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(_get_value(usage, "completion_tokens", 0) or 0)
    return prompt_tokens, completion_tokens


def _response_text(response: Any) -> str:
    choices = _get_value(response, "choices", []) or []
    if not choices:
        raise RuntimeError("المزود أعاد استجابة بدون choices.")
    message = _get_value(choices[0], "message", {}) or {}
    content = _get_value(message, "content", "")
    if content is None:
        return ""
    return str(content)


def _is_retryable(exc: Exception) -> bool:
    """إعادة المحاولة فقط لأخطاء الشبكة/المهلة/429/5xx."""
    status = getattr(exc, "status_code", None)
    if status == 429 or (isinstance(status, int) and 500 <= status <= 599):
        return True

    retryable_types = tuple(
        cls
        for cls in (
            getattr(litellm, "RateLimitError", None),
            getattr(litellm, "Timeout", None),
            getattr(litellm, "APIConnectionError", None),
            getattr(litellm, "ServiceUnavailableError", None),
        )
        if isinstance(cls, type)
    )
    return bool(retryable_types) and isinstance(exc, retryable_types)


def _write_log(record: dict[str, Any]) -> None:
    path = Path(config.CALL_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _log_call(*, role: str, provider: str, model: str, started: float,
              success: bool, input_tokens: int = 0, output_tokens: int = 0,
              error: str | None = None) -> None:
    record = {
        "time": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_seconds": round(time.monotonic() - started, 3),
        "success": success,
    }
    if error:
        record["error"] = error[:500]
    _write_log(record)


def ask(role: str, prompt: str, system: str = "") -> str:
    """إرسال prompt إلى النموذج المرتبط بالدور وإرجاع النص فقط."""
    global _call_count, _total_input_tokens, _total_output_tokens

    if role not in config.ROLES:
        raise ValueError(f"الدور غير معروف: {role}")
    if _call_count >= config.MAX_CALLS_PER_RUN:
        raise RuntimeError(
            f"تم تجاوز الحد الأقصى للاستدعاءات في هذا التشغيل ({config.MAX_CALLS_PER_RUN})."
        )

    role_config = config.ROLES[role]
    provider = config.PROVIDERS[role_config.provider]
    api_key = os.getenv(provider.api_key_env)
    if not api_key:
        raise RuntimeError(
            f"مفتاح المزود {provider.name} غير موجود. "
            f"أضف متغير البيئة {provider.api_key_env} في Codespaces Secrets."
        )

    _call_count += 1
    started = time.monotonic()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    last_error: Exception | None = None
    for attempt in range(config.MODEL_MAX_RETRIES + 1):
        try:
            response = litellm.completion(
                model=f"openai/{role_config.model}",
                messages=messages,
                api_base=provider.api_base,
                api_key=api_key,
                timeout=config.MODEL_TIMEOUT_SECONDS,
                max_tokens=config.MODEL_MAX_TOKENS,
                num_retries=0,
            )
            input_tokens, output_tokens = _usage_tokens(response)
            _total_input_tokens += input_tokens
            _total_output_tokens += output_tokens
            text = _response_text(response)
            _log_call(
                role=role,
                provider=provider.name,
                model=role_config.model,
                started=started,
                success=True,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            return text
        except Exception as exc:
            last_error = exc
            if attempt >= config.MODEL_MAX_RETRIES or not _is_retryable(exc):
                break
            time.sleep(2 ** attempt)

    assert last_error is not None
    _log_call(
        role=role,
        provider=provider.name,
        model=role_config.model,
        started=started,
        success=False,
        error=str(last_error),
    )
    raise RuntimeError(
        f"فشل استدعاء {provider.name}/{role_config.model}: {last_error}"
    ) from last_error


def usage_summary() -> dict[str, int]:
    """ملخص الاستهلاك المتراكم في العملية الحالية."""
    return {
        "calls": _call_count,
        "input_tokens": _total_input_tokens,
        "output_tokens": _total_output_tokens,
        "total_tokens": _total_input_tokens + _total_output_tokens,
    }


def _reset_usage_for_tests() -> None:
    """إعادة الحالة للاختبارات فقط، وليست جزءاً من الواجهة العامة."""
    global _call_count, _total_input_tokens, _total_output_tokens
    _call_count = 0
    _total_input_tokens = 0
    _total_output_tokens = 0
