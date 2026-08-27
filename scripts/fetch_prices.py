"""Tarik harga historis buat semua saham di watchlist -> simpan ke DB."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from trade.config import load_watchlist          # noqa: E402
from trade.db import get_connection, init_db, upsert_prices  # noqa: E402
from trade.prices import fetch_prices             # noqa: E402


def main(period: str = "6mo"):
    conn = get_connection()
    init_db(conn)
    wl = load_watchlist()

    print(f"📈 Tarik harga ({period}) buat {len(wl)} saham...\n")
    for ins in wl:
        try:
            rows = fetch_prices(ins.ticker, period=period)
            n = upsert_prices(conn, ins.ticker, rows)
            last = rows[-1] if rows else None
            info = f"terakhir {last[0]} close={last[4]}" if last else "(kosong)"
            print(f"   ✓ {ins.ticker:10s} {n:4d} baris  {info}")
        except Exception as e:
            print(f"   ✗ {ins.ticker:10s} GAGAL: {e}")

    print("\nSelesai.")


if __name__ == "__main__":
    main()
