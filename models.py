"""طبقة موحدة: مفتاح واحد من مزود خارجي (متوافق مع OpenAI) يشغّل Claude و GPT و Gemini."""
import os
from dotenv import load_dotenv
from litellm import completion

load_dotenv()

API_KEY = os.getenv("PROVIDER_API_KEY")
BASE_URL = os.getenv("PROVIDER_BASE_URL")  # مثال: https://openrouter.ai/api/v1

# أسماء النماذج كما يكتبها المزود عندك (من صفحة Models في موقعه)
MODELS = {
    "claude": os.getenv("MODEL_CLAUDE", "anthropic/claude-sonnet-4.5"),
    "gpt": os.getenv("MODEL_GPT", "openai/gpt-4o"),
    "gemini": os.getenv("MODEL_GEMINI", "google/gemini-2.5-pro"),
}

MAX_CALLS = int(os.getenv("MAX_CALLS_PER_RUN", "30"))
_calls = 0


def ask(model_key: str, prompt: str, system: str = "") -> str:
    global _calls
    if not API_KEY or not BASE_URL:
        raise RuntimeError("ناقص PROVIDER_API_KEY أو PROVIDER_BASE_URL في الـ Secrets")
    if _calls >= MAX_CALLS:
        raise RuntimeError(f"وصلت الحد الأقصى للاستدعاءات ({MAX_CALLS})")
    _calls += 1
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    resp = completion(
        model="openai/" + MODELS[model_key],  # openai/ = بروتوكول متوافق مع OpenAI
        api_base=BASE_URL,
        api_key=API_KEY,
        messages=messages,
    )
    u = resp.usage
    print(f"[{model_key}] tokens in={u.prompt_tokens} out={u.completion_tokens}")
    return resp.choices[0].message.content
