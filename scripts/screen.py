"""Jalanin screener -> simpan focus_list -> tampilin hasilnya."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from trade.db import get_connection, init_db, replace_focus_list   # noqa: E402
from trade.screener import ScreenParams, screen                    # noqa: E402


def fmt_price(v, market):
    if v is None:
        return "-"
    return f"${v:,.2f}" if market == "US" else f"Rp{v:,.0f}"


def fmt_turnover(v, market):
    if v is None:
        return "-"
    return f"${v/1e6:,.1f}jt" if market == "US" else f"Rp{v/1e9:,.1f}M"


def main():
    conn = get_connection()
    init_db(conn)

    p = ScreenParams()
    passed = screen(conn, p)
    n = replace_focus_list(conn, passed)

    us = [x for x in passed if x["market"] == "US"]
    idx = [x for x in passed if x["market"] == "IDX"]
    universe = conn.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]
    with_px = conn.execute("SELECT COUNT(DISTINCT ticker) FROM prices").fetchone()[0]

    print("=" * 66)
    print(" SCREENER — hasil saringan likuiditas")
    print("=" * 66)
    print(f"  Universe          : {universe}")
    print(f"  Punya data harga  : {with_px}")
    print(f"  ✅ LOLOS focus list: {n}   (US {len(us)}, IDX {len(idx)})")
    print(f"\n  Kriteria:")
    print(f"    US : harga ≥ ${p.us_min_price:.0f}  &  turnover ≥ ${p.us_min_turnover/1e6:.0f}jt/hari")
    print(f"    IDX: harga ≥ Rp{p.idx_min_price:.0f} &  turnover ≥ Rp{p.idx_min_turnover/1e9:.0f}M/hari  (skip papan {p.idx_skip_boards[0]})")
    print(f"    (rata2 {p.lookback} hari terakhir, minimal {p.min_ndays} hari data)")

    for label, lst in [("US 🇺🇸", us), ("IDX 🇮🇩", idx)]:
        if not lst:
            continue
        print(f"\n  ── TOP 15 {label} (paling likuid) ──")
        for x in lst[:15]:
            print(f"    {x['ticker']:11s} {fmt_price(x['last_close'], x['market']):>11} "
                  f"{fmt_turnover(x['avg_turnover'], x['market']):>11}  {(x['name'] or '')[:32]}")

    print("\n💾 focus_list tersimpan → ini yang bakal ditarik berita + sentimen (Fase 1).")


if __name__ == "__main__":
    main()
