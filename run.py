"""واجهة CLI للمرحلة الثانية."""

from __future__ import annotations

import argparse
import sys

from agent.loop import build


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-Model Coding Agent — Phase 2")
    parser.add_argument("request", help="وصف المشروع المطلوب بلغة طبيعية")
    parser.add_argument("--max-attempts", type=int, default=5, help="الحد الأقصى لمحاولات التشغيل (1-5)")
    args = parser.parse_args()

    try:
        report = build(args.request, max_attempts=args.max_attempts)
    except Exception as exc:
        print(f"❌ فشل الوكيل: {exc}", file=sys.stderr)
        return 1
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
