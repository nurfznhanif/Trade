"""Tarik berita buat NEWS TIER (IDX semua + US top N paling likuid), dari focus_list.

Throttled biar gak diblok Google News. Resumable-ish: berita dobel otomatis di-skip.

Contoh:
  python scripts/fetch_news_focus.py                 # IDX semua + US top 250
  python scripts/fetch_news_focus.py --us-top 150    # US top 150 aja
  python scripts/fetch_news_focus.py --limit 20      # tes 20 saham pertama
"""
import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from trade.db import (backfill_title_keys, get_connection,        # noqa: E402
                      init_db, insert_news)
from trade.news import (build_news_query, fetch_idx_disclosures,  # noqa: E402
                        fetch_news)


def tier(conn, us_top: int):
    idx = conn.execute(
        "SELECT f.ticker, i.name, f.market FROM focus_list f "
        "JOIN instruments i ON i.ticker = f.ticker "
        "WHERE f.market='IDX' ORDER BY f.avg_turnover DESC"
    ).fetchall()
    us = conn.execute(
        "SELECT f.ticker, i.name, f.market FROM focus_list f "
        "JOIN instruments i ON i.ticker = f.ticker "
        "WHERE f.market='US' ORDER BY f.avg_turnover DESC LIMIT ?", (us_top,)
    ).fetchall()
    return list(idx) + list(us)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--us-top", type=int, default=250)
    ap.add_argument("--news-per", type=int, default=15, help="berita per saham")
    ap.add_argument("--sleep", type=float, default=0.6, help="jeda antar saham (detik)")
    ap.add_argument("--disc-per", type=int, default=10, help="disclosure IDX per saham")
    ap.add_argument("--limit", type=int, help="ambil N saham pertama (buat tes)")
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)
    bf = backfill_title_keys(conn)
    if bf:
        print(f"(isi title_key {bf} berita lama buat dedup)\n", flush=True)

    rows = tier(conn, args.us_top)
    if args.limit:
        rows = rows[:args.limit]
    total = len(rows)
    print(f"📰 Tarik berita buat {total} saham (news tier). Jeda {args.sleep}s/saham.\n", flush=True)

    t0 = time.time()
    new_total = fail = 0
    for i, r in enumerate(rows, 1):
        query, lang = build_news_query(r["ticker"], r["name"], r["market"])
        try:
            items = fetch_news(query, lang=lang, limit=args.news_per)
            new_total += insert_news(conn, r["ticker"], items)
        except Exception as e:
            fail += 1
            if fail <= 5:
                print(f"   ✗ {r['ticker']} news: {type(e).__name__}", flush=True)

        if r["market"] == "IDX":                      # + disclosure resmi IDX
            try:
                disc = fetch_idx_disclosures(r["ticker"].replace(".JK", ""), limit=args.disc_per)
                new_total += insert_news(conn, r["ticker"], disc)
            except Exception as e:
                fail += 1
                if fail <= 5:
                    print(f"   ✗ {r['ticker']} disc: {type(e).__name__}", flush=True)

        if i % 25 == 0 or i == total:
            elapsed = time.time() - t0
            eta = (total - i) / (i / elapsed) if elapsed else 0
            print(f"   [{i:>4}/{total}]  +{new_total} berita baru  | ETA {eta/60:4.1f} mnt", flush=True)
        time.sleep(args.sleep)

    grand = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]
    print(f"\n✅ Selesai {(time.time()-t0)/60:.1f} mnt. Berita baru {new_total}, gagal {fail}. "
          f"Total berita di DB: {grand}", flush=True)


if __name__ == "__main__":
    main()
