"""Tarik rasio fundamental buat semua saham di focus_list -> simpan ke DB."""
import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from trade.db import get_connection, init_db, upsert_fundamentals_bulk   # noqa: E402
from trade.fundamentals import fetch_fundamentals, red_flags             # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="ambil N saham pertama (buat tes)")
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)
    tickers = [r["ticker"] for r in
               conn.execute("SELECT ticker FROM focus_list ORDER BY ticker")]
    if args.limit:
        tickers = tickers[:args.limit]

    print(f"💎 Tarik fundamental {len(tickers)} saham...\n", flush=True)
    t0 = time.time()
    batch, ok, flagged = [], 0, 0
    for i, tk in enumerate(tickers, 1):
        try:
            f = fetch_fundamentals(tk)
            batch.append(f)
            ok += 1
            if red_flags(f):
                flagged += 1
        except Exception:
            pass
        if i % 25 == 0 or i == len(tickers):
            upsert_fundamentals_bulk(conn, batch)
            batch = []
            eta = (len(tickers) - i) / (i / (time.time() - t0)) if time.time() > t0 else 0
            print(f"   [{i:>3}/{len(tickers)}] ok {ok}, bendera-merah {flagged}  | ETA {eta/60:.1f} mnt",
                  flush=True)

    print(f"\n✅ Selesai {(time.time()-t0)/60:.1f} mnt. {ok} saham, {flagged} kena bendera merah.")


if __name__ == "__main__":
    main()
