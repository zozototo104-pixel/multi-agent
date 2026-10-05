"""طبقة موحدة لاستدعاء Claude و GPT و Gemini عبر LiteLLM."""
import os
from dotenv import load_dotenv
from litellm import completion, completion_cost

load_dotenv()

# عدّل أسماء النماذج حسب المتاح في حسابك
MODELS = {
    "claude": "anthropic/claude-sonnet-4-5",
    "gpt": "openai/gpt-4o",
    "gemini": "gemini/gemini-2.5-pro",
}

MAX_COST = float(os.getenv("MAX_COST_PER_RUN", "0.50"))
_spent = 0.0


def ask(model_key: str, prompt: str, system: str = "") -> str:
    """يرسل طلب لنموذج معين ويرجع النص، مع تتبع التكلفة."""
    global _spent
    if _spent >= MAX_COST:
        raise RuntimeError(f"تجاوزت حد الصرف: ${_spent:.4f}")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = completion(model=MODELS[model_key], messages=messages)
    try:
        cost = completion_cost(completion_response=resp)
    except Exception:
        cost = 0.0
    _spent += cost
    print(f"[{model_key}] cost=${cost:.5f} total=${_spent:.5f}")
    return resp.choices[0].message.content


def spent() -> float:
    return _spent
