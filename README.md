# Multi-Model Coding Agent

وكيل برمجي متعدد النماذج. المرحلة الثانية تضيف MVP بنموذج واحد: يخطط مشروع Python، يكتب ملفاته، يشغّل الاختبارات داخل Docker معزول، ثم يصلح الأخطاء من مخرجات التشغيل الحقيقية حتى النجاح أو بلوغ خمس محاولات.

## الإعداد

الأسرار تبقى في GitHub Codespaces Secrets فقط:

- `OPENROUTER_API_KEY`
- `HF_TOKEN`

إعدادات المرحلة الثانية الافتراضية:

```text
PLANNER_ROLE=claude
CODER_ROLE=claude
MAX_CALLS_PER_RUN=40
```

يمكن تغيير الدورين إلى أي دور موجود في `config.ROLES` بدون تعديل بنية الوكيل.

## التشغيل

```bash
pytest -q
docker --version
python run.py "اعمل CLI آلة حاسبة بـ Python تدعم + - * / مع اختبارات pytest"
cat workspace/*/agent_report.json | head -50
```

كل مشروع مولّد يُكتب تحت `workspace/<project_name>/` فقط، والمجلد مستبعد من Git.

## دورة العمل

1. `planner.py` يحول الطلب إلى خطة JSON محققة الحقول.
2. `coder.py` يولد ملفات المشروع بصيغة JSON.
3. `workspace.py` يرفض المسارات المطلقة و`..` وأي خروج من مجلد المشروع، ويطبق حد 200KB للملف و50 ملفاً للمشروع.
4. `sandbox.py` يثبت dependencies داخل `python:3.12-slim` مع الشبكة، ثم يشغل الاختبارات في حاوية جديدة بدون شبكة وبحدود 512MB RAM وCPU واحد و256 process.
5. عند الفشل، `fix_code()` يستقبل الخطة والملفات وآخر 4000 حرف من stdout/stderr وexit code، ثم يعيد الملفات المعدلة فقط.
6. `loop.py` يكرر التشغيل والإصلاح بحد أقصى خمس محاولات ويحفظ `agent_report.json`.

لا يوجد fallback لتشغيل الكود المولد على الجهاز مباشرة إذا كان Docker غائباً.

## أخطاء متوقعة

| المشكلة | التصرف |
|---|---|
| Docker permission denied | تأكد أن Codespace يسمح بالوصول إلى Docker daemon ثم أعد تشغيل البيئة إذا لزم |
| JSON غير صالح من النموذج | النظام يحاول استخراج JSON من النص/code fence ثم يطلب تصحيح JSON مرة واحدة فقط |
| timeout | تثبيت الحزم يتوقف بعد 180 ثانية، والاختبار بعد 120 ثانية ويظهر ذلك في التقرير |
| تجاوز حد الاستدعاءات | `models.ask()` يوقف الطلبات عند `MAX_CALLS_PER_RUN`؛ القيمة المقترحة للمرحلة الثانية 40 |
| النموذج يحذف/يضعف الاختبارات | system prompt يمنع ذلك، ومرحلة لاحقة يمكن أن تضيف reviewer مستقل للتحقق البنيوي |

## فحص الأسرار

```bash
git grep -n "sk-\|hf_" || echo "✅ لا توجد أنماط مفاتيح معروفة في الملفات المتتبعة"
```

## أوامر التسليم

```bash
pytest -q
docker --version
python run.py "اعمل CLI آلة حاسبة بـ Python تدعم + - * / مع اختبارات pytest"
cat workspace/*/agent_report.json | head -50
git add . && git commit -m "Phase 2: single-model plan-code-run-fix loop" && git push -u origin phase-2
```
