"""Diagnostik: ukur waktu tiap panggilan network satu-satu (biar ketahuan yang lambat)."""
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from trade.news import fetch_news       # noqa: E402
from trade.prices import fetch_prices   # noqa: E402


def timed(label, fn):
    t0 = time.time()
    try:
        res = fn()
        print(f"[{time.time() - t0:6.1f}s] {label}: OK -> {res}", flush=True)
    except Exception as e:
        print(f"[{time.time() - t0:6.1f}s] {label}: ERROR {type(e).__name__}: {e}", flush=True)


print("Mulai diagnostik...", flush=True)
timed("price AAPL   ", lambda: f"{len(fetch_prices('AAPL', period='1mo'))} baris")
timed("price BBCA.JK", lambda: f"{len(fetch_prices('BBCA.JK', period='1mo'))} baris")
timed("news  AAPL/en", lambda: f"{len(fetch_news('Apple AAPL stock', lang='en', limit=5))} berita")
timed("news  BBCA/id", lambda: f"{len(fetch_news('saham BBCA', lang='id', limit=5))} berita")
print("Selesai diagnostik.", flush=True)
