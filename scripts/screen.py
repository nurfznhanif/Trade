"""Screener likuiditas -> focus_list (saham yang dipantau tiap hari). Jalanin sesekali (mis. bulanan),
SETELAH harga semua saham di-update: `python scripts/backfill_prices.py --refresh --period 1mo`."""
import _bootstrap  # noqa: F401  (path repo + UTF-8)

from trade.db import get_connection, init_db, replace_focus_list
from trade.screener import ScreenParams, screen


def main():
    conn = get_connection()
    init_db(conn)

    p = ScreenParams()
    passed = screen(conn, p)
    n = replace_focus_list(conn, passed)

    universe = conn.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]
    with_px = conn.execute("SELECT COUNT(DISTINCT ticker) FROM prices").fetchone()[0]

    print("=" * 66)
    print(" SCREENER — hasil saringan likuiditas")
    print("=" * 66)
    print(f"  Universe          : {universe}")
    print(f"  Punya data harga  : {with_px}")
    print(f"  LOLOS focus list  : {n}")
    print("\n  Kriteria:")
    print(f"    harga >= Rp{p.min_price:.0f} & turnover >= Rp{p.min_turnover/1e9:.0f}M/hari "
          f"(skip papan {', '.join(p.skip_boards)})")
    print(f"    (rata2 {p.lookback} hari terakhir, minimal {p.min_ndays} hari data)")

    print("\n  -- TOP 15 (paling likuid) --")
    for x in passed[:15]:
        px, turn = f"Rp{x['last_close']:,.0f}", f"Rp{x['avg_turnover'] / 1e9:,.1f}M"
        print(f"    {x['ticker']:11s} {px:>11} {turn:>11}  {(x['name'] or '')[:32]}")

    print("\nfocus_list tersimpan -> saham ini yang ditarik berita + sinyalnya tiap hari.")


if __name__ == "__main__":
    main()
