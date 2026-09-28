"""Pipeline data HARIAN — jalanin semua langkah berurutan, hasil akhirnya data/brief_latest.md.

Urutan: cadangan jurnal -> harga -> makro -> berita -> sentimen -> fundamental (tiap Senin) -> sinyal
-> paper trading -> brief. Langkah yang gagal gak ngehentiin langkah berikutnya. Tiap langkah = script
terpisah (bisa dijalanin sendiri kalau perlu).

Server jalanin ini tiap Senin-Jumat 05:00 WIB (systemd trade-daily, lanjut auto_analisa.py) —
JANGAN pindah/rename file ini.

  python scripts/daily.py
"""
import _bootstrap  # noqa: F401  (path repo + UTF-8)

import pathlib
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from trade.db import get_connection

HERE = pathlib.Path(__file__).resolve().parent
WIB = timezone(timedelta(hours=7))


def fundamentals_due() -> bool:
    """Fundamental berubah pelan (laporan keuangan per kuartal): perbarui tiap Senin, atau kapan pun
    datanya udah lebih dari 7 hari (mis. Senin libur / gagal)."""
    if datetime.now(WIB).weekday() == 0:
        return True
    last = get_connection().execute("SELECT MAX(updated) FROM fundamentals").fetchone()[0]
    return not last or datetime.fromisoformat(last) < datetime.now(timezone.utc) - timedelta(days=7)


# (label, script, argumen, syarat jalan — None = selalu)
STEPS = [
    ("Cadangan jurnal (simpan 30 hari)", "backup_jurnal.py", [], None),
    ("Refresh harga (1 bulan terakhir)", "backfill_prices.py", ["--focus", "--refresh", "--period", "1mo"], None),
    ("Tarik data makro (regime IHSG + kurs/komoditas)", "fetch_macro.py", [], None),
    ("Tarik berita (Google News RSS)", "fetch_news.py", [], None),
    ("Skor sentimen", "score_news.py", [], None),
    ("Fundamental (tiap Senin)", "fetch_fundamentals.py", [], fundamentals_due),
    ("Generate sinyal (pagar fundamental)", "generate_signals.py", ["--top", "10"], None),
    ("Paper trading update", "paper_run.py", [], None),
    ("Tulis brief harian (bahan analisa LLM)", "brief.py", ["--quiet"], None),
]


def main():
    t0 = datetime.now()
    print("#" * 70)
    print(f"#  PIPELINE HARIAN — {t0:%Y-%m-%d %H:%M}")
    print("#" * 70)

    for i, (label, script, args, when) in enumerate(STEPS, 1):
        print(f"\n\n{'=' * 70}\n[{i}/{len(STEPS)}] {label}\n{'=' * 70}", flush=True)
        if when is not None and not when():
            print("(dilewati: belum waktunya)", flush=True)
            continue
        code = subprocess.run([sys.executable, str(HERE / script), *args], check=False).returncode
        if code != 0:
            print(f"[!] langkah '{label}' gagal (exit code {code}), lanjut ke berikutnya.", flush=True)

    dt = (datetime.now() - t0).total_seconds() / 60
    print(f"\n\n{'#' * 70}\n#  SELESAI dalam {dt:.1f} menit.\n{'#' * 70}")


if __name__ == "__main__":
    main()
