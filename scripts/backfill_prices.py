"""Backfill / update harga buat SEMUA saham di universe.

Aman: batch + jeda + RESUMABLE (kalau mati di tengah, jalanin lagi -> lanjut, gak ngulang).

Contoh:
  python scripts/backfill_prices.py --limit 40           # tes kecil dulu
  python scripts/backfill_prices.py --market IDX         # IDX aja (~962)
  python scripts/backfill_prices.py                       # backfill penuh (~7900, lama)
  python scripts/backfill_prices.py --refresh --period 5d # update harian semua saham
"""
import argparse
import logging
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Bungkam log "No data found / delisted" dari yfinance (bakal banyak di universe segede ini)
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

from trade.db import get_connection, init_db, upsert_prices   # noqa: E402
from trade.prices import fetch_prices_batch                    # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", default="6mo", help="rentang histori (6mo, 1y, 2y, ...)")
    ap.add_argument("--batch", type=int, default=120, help="saham per batch")
    ap.add_argument("--sleep", type=float, default=1.0, help="jeda antar batch (detik)")
    ap.add_argument("--market", choices=["US", "IDX"], help="batasi ke satu pasar")
    ap.add_argument("--limit", type=int, help="ambil N saham pertama (buat tes)")
    ap.add_argument("--refresh", action="store_true",
                    help="fetch ulang semua (update). Tanpa ini: skip yang udah ada data.")
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)

    q = "SELECT ticker FROM instruments"
    params: list = []
    if args.market:
        q += " WHERE market = ?"
        params.append(args.market)
    q += " ORDER BY ticker"
    all_tickers = [r[0] for r in conn.execute(q, params)]

    have = set()
    if not args.refresh:
        have = {r[0] for r in conn.execute("SELECT DISTINCT ticker FROM prices")}
    todo = [t for t in all_tickers if t not in have]
    if args.limit:
        todo = todo[:args.limit]

    total = len(todo)
    mode = ", mode REFRESH" if args.refresh else ""
    print(f"🎯 Target: {total} saham (dari {len(all_tickers)} total{mode}). "
          f"Batch {args.batch}, jeda {args.sleep}s, periode {args.period}.\n", flush=True)
    if total == 0:
        print("Semua target udah ada datanya. Pakai --refresh buat update.", flush=True)
        return

    nbatch = (total + args.batch - 1) // args.batch
    t_start = time.time()
    ok = fail = rows_total = 0

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
        rows_total += b_rows

        elapsed = time.time() - t_start
        done = min(i + args.batch, total)
        rate = done / elapsed if elapsed else 0
        eta = (total - done) / rate if rate else 0
        print(f"  batch {bno:>3}/{nbatch}  [{done:>5}/{total}]  "
              f"+{b_ok} saham, +{b_rows} baris  | ETA {eta/60:4.1f} mnt", flush=True)
        time.sleep(args.sleep)

    dt = time.time() - t_start
    grand = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    print(f"\n✅ Selesai {dt/60:.1f} menit. Sukses {ok}, gagal/kosong {fail}. "
          f"Total baris harga di DB: {grand}", flush=True)


if __name__ == "__main__":
    main()
