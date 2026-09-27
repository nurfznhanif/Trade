"""Tarik data MAKRO (IHSG, kurs, komoditas, global) -> tabel `macro`, lalu cetak regime IHSG.

  python scripts/fetch_macro.py      (langkah daily.py)
"""
import _bootstrap  # noqa: F401  (path repo + UTF-8)

import warnings

from trade.db import get_connection, init_db, upsert_macro
from trade.macro import MACRO, fetch_series, snapshot

warnings.filterwarnings("ignore")


def main():
    conn = get_connection()
    init_db(conn)
    print("Tarik data makro (yfinance)...\n", flush=True)

    for tk, meta in MACRO.items():
        try:
            n = upsert_macro(conn, tk, fetch_series(tk))
            print(f"   OK    {meta['label']:8s} ({tk})  +{n} bar", flush=True)
        except Exception as e:
            print(f"   GAGAL {meta['label']:8s} ({tk})  {type(e).__name__}", flush=True)

    snap = snapshot(conn)
    r = snap["regime"]
    print(f"\n{'=' * 60}")
    print(f"  REGIME IHSG: {r['regime'].upper()}")
    print(f"     {r['note']}")
    if r["level"]:
        ma200 = f"{r['ma200']:.0f}" if r["ma200"] else "—"
        print(f"     IHSG {r['level']:.0f}  |  MA50 {r['ma50']:.0f}  |  MA200 {ma200}")
    print(f"{'=' * 60}")
    print("  Indikator (arah = efek buat saham IDX):")
    for i in snap["indikator"]:
        if i["ticker"] == "^JKSE" or i["level"] is None:
            continue
        chg = f"{i['chg1mo']*100:+.1f}%" if i.get("chg1mo") is not None else "—"
        print(f"     {i['label']:8s} {i['level']:>11.2f}   1bln {chg:>7}  {i.get('arah') or ''}")
    print(f"\n  (data per {snap.get('asof')})")


if __name__ == "__main__":
    main()
