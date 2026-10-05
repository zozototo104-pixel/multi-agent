"""اختبار اتصال حقيقي اختياري للمزودين الأربعة."""

import sys

import config
from models import ask, usage_summary


def main() -> int:
    passed = 0
    for role in ("claude", "gpt", "gemini", "qwen"):
        role_config = config.ROLES[role]
        provider = config.PROVIDERS[role_config.provider]
        try:
            result = ask(role, "Reply with exactly: OK")
            if "OK" in result.upper():
                passed += 1
                print(f"✅ {role}: {provider.name} / {role_config.model} — OK")
            else:
                preview = result.replace("\n", " ")[:200]
                print(
                    f"❌ {role}: {provider.name} / {role_config.model} — "
                    f"رد غير متوقع: {preview}"
                )
        except Exception as exc:
            preview = str(exc).replace("\n", " ")[:200]
            print(f"❌ {role}: {provider.name} / {role_config.model} — {preview}")

    summary = usage_summary()
    print(f"\nالنتيجة: {passed}/4")
    print(
        "ملخص التوكنز: "
        f"input={summary['input_tokens']}, "
        f"output={summary['output_tokens']}, "
        f"total={summary['total_tokens']}"
    )
    return 0 if passed == 4 else 1


if __name__ == "__main__":
    sys.exit(main())
