"""END-TO-END Fase 0: tarik harga + berita buat semua saham, lalu ringkas.

Jalanin:  python scripts/run_all.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from trade.config import DB_PATH, load_watchlist   # noqa: E402
from trade.db import (                              # noqa: E402
    get_connection, init_db, insert_news, upsert_instrument, upsert_prices,
)
from trade.news import fetch_news                   # noqa: E402
from trade.prices import fetch_prices               # noqa: E402


def main():
    conn = get_connection()
    init_db(conn)
    wl = load_watchlist()

    print("=" * 60)
    print(" FASE 0 — Tarik data harga + berita")
    print("=" * 60)

    for ins in wl:
        upsert_instrument(conn, ins.ticker, ins.name, ins.market)

    print("\n📈 HARGA")
    for ins in wl:
        try:
            rows = fetch_prices(ins.ticker, period="6mo")
            n = upsert_prices(conn, ins.ticker, rows)
            last = rows[-1] if rows else None
            info = f"terakhir {last[0]} close={last[4]}" if last else "(kosong)"
            print(f"   ✓ {ins.ticker:10s} {n:4d} baris  {info}")
        except Exception as e:
            print(f"   ✗ {ins.ticker:10s} GAGAL: {e}")

    print("\n📰 BERITA")
    for ins in wl:
        try:
            items = fetch_news(ins.news_query, lang=ins.news_lang, limit=20)
            new = insert_news(conn, ins.ticker, items)
            print(f"   ✓ {ins.ticker:10s} {len(items):2d} ketemu, {new:2d} baru disimpan")
        except Exception as e:
            print(f"   ✗ {ins.ticker:10s} GAGAL: {e}")

    # Ringkasan dari DB
    total_prices = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    total_news = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]

    print("\n" + "=" * 60)
    print(" RINGKASAN DATABASE")
    print("=" * 60)
    print(f"   Total baris harga : {total_prices}")
    print(f"   Total berita      : {total_news}")
    print(f"   Lokasi DB         : {DB_PATH}")
    print("\nSelesai. 🚀")


if __name__ == "__main__":
    main()
