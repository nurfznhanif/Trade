"""Diimport PALING ATAS tiap script di folder ini:
  - biar `import trade` jalan walau script dijalanin dari folder mana pun (`python scripts/xxx.py`)
  - output UTF-8 (console Windows default-nya cp1252, bikin karakter kayak '—' / '→' error)
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:   # stdout udah diganti objek lain (mis. saat dites)
    pass
