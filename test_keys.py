from models import ask, MODELS

ok = 0
for key, name in MODELS.items():
    try:
        r = ask(key, "Reply with exactly: OK")
        ok += "OK" in r
        print(f"✅ {key} ({name}): {r.strip()[:40]}")
    except Exception as e:
        print(f"❌ {key} ({name}): {str(e)[:200]}")
print(f"\nالنتيجة: {ok}/{len(MODELS)}")
