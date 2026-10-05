"""إعدادات المزودين والنماذج، وكلها قابلة للتعديل من متغيرات البيئة."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    api_base: str
    api_key_env: str


@dataclass(frozen=True)
class RoleConfig:
    provider: str
    model: str


PROVIDERS = {
    "openrouter": ProviderConfig(
        name="openrouter",
        api_base=os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"),
        api_key_env="OPENROUTER_API_KEY",
    ),
    "hf": ProviderConfig(
        name="hf",
        api_base=os.getenv("HF_API_BASE", "https://router.huggingface.co/v1"),
        api_key_env="HF_TOKEN",
    ),
}

ROLES = {
    "claude": RoleConfig("openrouter", os.getenv("CLAUDE_MODEL", "anthropic/claude-sonnet-4.5")),
    "gpt": RoleConfig("openrouter", os.getenv("GPT_MODEL", "openai/gpt-5")),
    "gemini": RoleConfig("openrouter", os.getenv("GEMINI_MODEL", "google/gemini-2.5-pro")),
    "qwen": RoleConfig("hf", os.getenv("QWEN_MODEL", "Qwen/Qwen3-Coder-480B-A35B-Instruct")),
}

MAX_CALLS_PER_RUN = int(os.getenv("MAX_CALLS_PER_RUN", "30"))
MODEL_TIMEOUT_SECONDS = float(os.getenv("MODEL_TIMEOUT_SECONDS", "60"))
MODEL_MAX_RETRIES = int(os.getenv("MODEL_MAX_RETRIES", "2"))
CALL_LOG_PATH = os.getenv("CALL_LOG_PATH", "logs/calls.jsonl")
