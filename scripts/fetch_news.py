"""Tarik berita buat semua saham di watchlist -> simpan ke DB."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from trade.config import load_watchlist          # noqa: E402
from trade.db import get_connection, init_db, insert_news  # noqa: E402
from trade.news import fetch_news                 # noqa: E402


def main(limit: int = 20):
    conn = get_connection()
    init_db(conn)
    wl = load_watchlist()

    print(f"📰 Tarik berita buat {len(wl)} saham...\n")
    for ins in wl:
        try:
            items = fetch_news(ins.news_query, lang=ins.news_lang, limit=limit)
            new = insert_news(conn, ins.ticker, items)
            print(f"   ✓ {ins.ticker:10s} {len(items):2d} ketemu, {new:2d} baru")
            for it in items[:2]:
                print(f"       - {(it['title'] or '')[:72]}")
        except Exception as e:
            print(f"   ✗ {ins.ticker:10s} GAGAL: {e}")

    print("\nSelesai.")


if __name__ == "__main__":
    main()
