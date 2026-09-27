"""Tarik / update harga harian saham IDX (yfinance) ke DB.

Aman: batch + jeda + RESUMABLE (mati di tengah? jalanin lagi -> lanjut, gak ngulang).

  python scripts/backfill_prices.py --focus --refresh --period 1mo   # update harian (dipakai daily.py)
  python scripts/backfill_prices.py --refresh --period 1mo           # update SEMUA saham (sebelum screen.py)
  python scripts/backfill_prices.py --limit 40                        # tes kecil
"""
import _bootstrap  # noqa: F401  (path repo + UTF-8)

import argparse
import logging
import time

from trade.db import get_connection, init_db, upsert_prices
from trade.prices import fetch_prices_batch

# Bungkam log "No data found / delisted" dari yfinance (bakal banyak kalau narik semua saham)
logging.getLogger("yfinance").setLevel(logging.CRITICAL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", default="6mo", help="rentang histori (1mo, 6mo, 1y, 2y, ...)")
    ap.add_argument("--batch", type=int, default=120, help="saham per batch")
    ap.add_argument("--sleep", type=float, default=1.0, help="jeda antar batch (detik)")
    ap.add_argument("--limit", type=int, help="ambil N saham pertama (buat tes)")
    ap.add_argument("--refresh", action="store_true",
                    help="tarik ulang semua (update). Tanpa ini: skip yang udah ada datanya.")
    ap.add_argument("--focus", action="store_true", help="cuma saham di focus_list (bukan semua saham)")
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)

    table = "focus_list" if args.focus else "instruments"
    all_tickers = [r[0] for r in conn.execute(f"SELECT ticker FROM {table} ORDER BY ticker")]
    have = set() if args.refresh else {r[0] for r in conn.execute("SELECT DISTINCT ticker FROM prices")}
    todo = [t for t in all_tickers if t not in have][:args.limit]

    total = len(todo)
    mode = ", mode REFRESH" if args.refresh else ""
    print(f"Target: {total} saham (dari {len(all_tickers)} total{mode}). "
          f"Batch {args.batch}, jeda {args.sleep}s, periode {args.period}.\n", flush=True)
    if total == 0:
        print("Semua target udah ada datanya. Pakai --refresh buat update.", flush=True)
        return

    nbatch = (total + args.batch - 1) // args.batch
    t_start = time.time()
    ok = fail = 0

    for i in range(0, total, args.batch):
        batch = todo[i:i + args.batch]
        bno = i // args.batch + 1
        try:
            data = fetch_prices_batch(batch, period=args.period)
        except Exception as e:
            fail += len(batch)
            print(f"  batch {bno}/{nbatch}: ERROR {type(e).__name__}: {e}", flush=True)
            time.sleep(args.sleep)
            continue

        b_rows = b_ok = 0
        for tk in batch:
            rows = data.get(tk) or []
            if rows:
                b_rows += upsert_prices(conn, tk, rows)
                b_ok += 1
                ok += 1
            else:
                fail += 1

        elapsed = time.time() - t_start
        done = min(i + args.batch, total)
        rate = done / elapsed if elapsed else 0
        eta = (total - done) / rate if rate else 0
        print(f"  batch {bno:>3}/{nbatch}  [{done:>5}/{total}]  "
              f"+{b_ok} saham, +{b_rows} baris  | ETA {eta/60:4.1f} mnt", flush=True)
        time.sleep(args.sleep)

    dt = time.time() - t_start
    grand = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    print(f"\nSelesai {dt/60:.1f} menit. Sukses {ok}, gagal/kosong {fail}. "
          f"Total baris harga di DB: {grand}", flush=True)


if __name__ == "__main__":
    main()
