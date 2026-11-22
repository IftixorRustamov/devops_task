"""Testlar servis paketlarini topishi uchun sys.path’ni sozlaydi (har bir test faylida import qilinadi)."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
for folder in ("common", "order", "courier", "tracking"):
    path = str(ROOT / "services" / folder)
    if path not in sys.path:
        sys.path.insert(0, path)
