"""Konteyner kirish nuqtasi: `CRYSTAL_SERVICE` dagi servis modulini ishga tushiradi.

Bitta Dockerfile barcha servislar uchun ishlatiladi; obraz qaysi servis ekanini
build argumenti `SERVICE` belgilaydi (masalan `order` -> `order_service`).
"""

import os
import runpy
import sys

ALLOWED = {"order", "courier", "tracking"}


def main():
    service = os.environ.get("CRYSTAL_SERVICE", "")
    if service not in ALLOWED:
        sys.exit(f"CRYSTAL_SERVICE noto‘g‘ri: {service!r} (kutilgan: {', '.join(sorted(ALLOWED))})")
    runpy.run_module(f"{service}_service", run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
