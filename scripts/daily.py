"""Pipeline data HARIAN — jalanin semua langkah berurutan, hasil akhirnya data/brief_latest.md.

Urutan: harga -> makro -> berita -> skor sentimen -> sinyal -> paper trading -> brief.
Langkah yang gagal gak ngehentiin langkah berikutnya. Tiap langkah = script terpisah
(bisa dijalanin sendiri kalau perlu).

Server jalanin ini tiap Senin-Jumat 05:00 WIB (systemd trade-daily, lanjut auto_analisa.py) —
JANGAN pindah/rename file ini.

  python scripts/daily.py
"""
import _bootstrap  # noqa: F401  (path repo + UTF-8)

import pathlib
import subprocess
import sys
from datetime import datetime

HERE = pathlib.Path(__file__).resolve().parent

STEPS = [
    ("Refresh harga (1 bulan terakhir)", "backfill_prices.py", ["--focus", "--refresh", "--period", "1mo"]),
    ("Tarik data makro (regime IHSG + kurs/komoditas)", "fetch_macro.py", []),
    ("Tarik berita (Google News RSS)", "fetch_news.py", []),
    ("Skor sentimen", "score_news.py", []),
    ("Generate sinyal (pagar fundamental)", "generate_signals.py", ["--top", "10"]),
    ("Paper trading update", "paper_run.py", []),
    ("Tulis brief harian (bahan analisa LLM)", "brief.py", ["--quiet"]),
]


def main():
    t0 = datetime.now()
    print("#" * 70)
    print(f"#  PIPELINE HARIAN — {t0:%Y-%m-%d %H:%M}")
    print("#" * 70)

    for i, (label, script, args) in enumerate(STEPS, 1):
        print(f"\n\n{'=' * 70}\n[{i}/{len(STEPS)}] {label}\n{'=' * 70}", flush=True)
        code = subprocess.run([sys.executable, str(HERE / script), *args], check=False).returncode
        if code != 0:
            print(f"[!] langkah '{label}' gagal (exit code {code}), lanjut ke berikutnya.", flush=True)

    dt = (datetime.now() - t0).total_seconds() / 60
    print(f"\n\n{'#' * 70}\n#  SELESAI dalam {dt:.1f} menit.\n{'#' * 70}")


if __name__ == "__main__":
    main()
