"""المهمة: استخراج مفاتيح API واختبار استدعاء بسيط لكل نموذج."""
from models import ask, MODELS, spent

ok = {}
for key in MODELS:
    try:
        reply = ask(key, "Reply with exactly: OK")
        ok[key] = "OK" in reply
        print(f"✅ {key}: {reply.strip()[:40]}")
    except Exception as e:
        ok[key] = False
        print(f"❌ {key}: {e}")

print(f"\nالنتيجة: {sum(ok.values())}/{len(ok)} شغالين | التكلفة: ${spent():.5f}")
