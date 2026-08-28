"""Orkestrator HARIAN — jalanin seluruh pipeline sekali gas, keluarin brief.

Urutan: refresh harga → tarik berita+disclosure → skor sentimen → sinyal → paper trading.
(Fundamental TIDAK tiap hari — berubah pelan; jalanin fetch_fundamentals.py mingguan.)

Jalanin:  python scripts/daily.py
Cocok dijadwalin tiap pagi (Windows Task Scheduler).
"""
import pathlib
import subprocess
import sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

STEPS = [
    ("Refresh harga (1 bulan terakhir)", "backfill_prices.py",
     ["--focus", "--refresh", "--period", "1mo"]),
    ("Tarik berita + disclosure IDX", "fetch_news_focus.py", []),
    ("Skor sentimen", "score_news.py", []),
    ("Generate sinyal (pagar fundamental)", "generate_signals.py", ["--top", "10"]),
    ("Paper trading update", "paper_run.py", []),
]


def run(script, args):
    r = subprocess.run([PY, str(ROOT / "scripts" / script), *args], check=False)
    return r.returncode


def main():
    t0 = datetime.now()
    print("#" * 70)
    print(f"#  BRIEF HARIAN — {t0:%Y-%m-%d %H:%M}")
    print("#" * 70)

    for i, (label, script, args) in enumerate(STEPS, 1):
        print(f"\n\n{'='*70}\n[{i}/{len(STEPS)}] {label}\n{'='*70}", flush=True)
        code = run(script, args)
        if code != 0:
            print(f"⚠️  langkah '{label}' exit code {code} (lanjut).", flush=True)

    dt = (datetime.now() - t0).total_seconds() / 60
    print(f"\n\n{'#'*70}\n#  SELESAI dalam {dt:.1f} menit. "
          f"Cek sinyal & posisi paper di atas / data/*.csv\n{'#'*70}")


if __name__ == "__main__":
    main()
