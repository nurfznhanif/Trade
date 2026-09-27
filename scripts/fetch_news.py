"""Tarik berita Google News buat semua saham di focus_list (langkah daily.py).

Dijeda biar gak diblok Google. Berita dobel (link / judul sama dari media lain) otomatis di-skip.

  python scripts/fetch_news.py
  python scripts/fetch_news.py --limit 20      # tes 20 saham pertama
"""
import _bootstrap  # noqa: F401  (path repo + UTF-8)

import argparse
import time

from trade.db import get_connection, init_db, insert_news
from trade.news import build_news_query, fetch_news


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--news-per", type=int, default=15, help="berita per saham")
    ap.add_argument("--sleep", type=float, default=0.6, help="jeda antar saham (detik)")
    ap.add_argument("--limit", type=int, help="ambil N saham pertama (buat tes)")
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)
    rows = conn.execute(
        "SELECT f.ticker, i.name FROM focus_list f JOIN instruments i ON i.ticker = f.ticker "
        "ORDER BY f.avg_turnover DESC").fetchall()[:args.limit]
    total = len(rows)
    print(f"Tarik berita buat {total} saham. Jeda {args.sleep}s/saham.\n", flush=True)

    t0 = time.time()
    new_total = fail = 0
    for i, r in enumerate(rows, 1):
        try:
            items = fetch_news(build_news_query(r["ticker"], r["name"]), limit=args.news_per)
            new_total += insert_news(conn, r["ticker"], items)
        except Exception as e:
            fail += 1
            if fail <= 5:
                print(f"   GAGAL {r['ticker']}: {type(e).__name__}", flush=True)

        if i % 25 == 0 or i == total:
            elapsed = time.time() - t0
            eta = (total - i) / (i / elapsed) if elapsed else 0
            print(f"   [{i:>4}/{total}]  +{new_total} berita baru  | ETA {eta/60:4.1f} mnt", flush=True)
        time.sleep(args.sleep)

    grand = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]
    print(f"\nSelesai {(time.time()-t0)/60:.1f} mnt. Berita baru {new_total}, gagal {fail}. "
          f"Total berita di DB: {grand}", flush=True)


if __name__ == "__main__":
    main()
