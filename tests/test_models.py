"""اختبارات models.py بدون أي اتصال حقيقي بالإنترنت."""

from types import SimpleNamespace

import pytest

import config
import models


@pytest.fixture(autouse=True)
def reset_state(monkeypatch, tmp_path):
    models._reset_usage_for_tests()
    monkeypatch.setattr(config, "CALL_LOG_PATH", str(tmp_path / "calls.jsonl"))
    monkeypatch.setattr(config, "MAX_CALLS_PER_RUN", 30)
    monkeypatch.setattr(config, "MODEL_MAX_RETRIES", 2)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setenv("HF_TOKEN", "test-hf-key")


def fake_response(text="OK", prompt_tokens=5, completion_tokens=1):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        ),
    )


def test_successful_call(monkeypatch):
    completion = lambda **kwargs: fake_response("OK", 7, 2)
    monkeypatch.setattr(models.litellm, "completion", completion)

    assert models.ask("gpt", "hello") == "OK"
    assert models.usage_summary() == {
        "calls": 1,
        "input_tokens": 7,
        "output_tokens": 2,
        "total_tokens": 9,
    }


def test_missing_provider_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        models.ask("claude", "hello")


def test_call_limit(monkeypatch):
    monkeypatch.setattr(config, "MAX_CALLS_PER_RUN", 1)
    monkeypatch.setattr(models.litellm, "completion", lambda **kwargs: fake_response())

    assert models.ask("gpt", "first") == "OK"
    with pytest.raises(RuntimeError, match="الحد الأقصى"):
        models.ask("gpt", "second")


def test_retry_after_temporary_error(monkeypatch):
    attempts = {"count": 0}

    class TemporaryError(Exception):
        status_code = 429

    def completion(**kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise TemporaryError("rate limited")
        return fake_response()

    monkeypatch.setattr(models.litellm, "completion", completion)
    monkeypatch.setattr(models.time, "sleep", lambda seconds: None)

    assert models.ask("gpt", "retry") == "OK"
    assert attempts["count"] == 2
    assert models.usage_summary()["calls"] == 1


def test_log_is_written(monkeypatch, tmp_path):
    log_path = tmp_path / "nested" / "calls.jsonl"
    monkeypatch.setattr(config, "CALL_LOG_PATH", str(log_path))
    monkeypatch.setattr(models.litellm, "completion", lambda **kwargs: fake_response())

    models.ask("qwen", "log me")

    content = log_path.read_text(encoding="utf-8")
    assert '"role": "qwen"' in content
    assert '"provider": "hf"' in content
    assert '"success": true' in content
    assert '"input_tokens": 5' in content
