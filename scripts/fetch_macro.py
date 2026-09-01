"""Tarik data MAKRO (indeks/kurs/komoditas/global) -> tabel `macro` + ringkas regime IHSG.

Jalanin:  python scripts/fetch_macro.py
Ikut di daily.py (makro gerak tiap hari, sama kayak harga).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import warnings  # noqa: E402

warnings.filterwarnings("ignore")

from trade.db import get_connection, init_db, upsert_macro   # noqa: E402
from trade.macro import MACRO, fetch_series, snapshot          # noqa: E402


def main():
    conn = get_connection()
    init_db(conn)
    print("🌐 Tarik data makro (yfinance)...\n", flush=True)

    ok = fail = 0
    for tk, meta in MACRO.items():
        try:
            rows = fetch_series(tk)
            n = upsert_macro(conn, tk, rows)
            ok += 1
            print(f"   ✓ {meta['label']:8s} ({tk})  +{n} bar", flush=True)
        except Exception as e:
            fail += 1
            print(f"   ✗ {meta['label']:8s} ({tk})  {type(e).__name__}", flush=True)

    snap = snapshot(conn)
    r = snap["regime"]
    icon = {"risk-on": "🟢", "netral": "🟡", "risk-off": "🔴"}.get(r["regime"], "⚪")
    print(f"\n{'='*60}")
    print(f"  {icon} REGIME IHSG: {r['regime'].upper()}")
    print(f"     {r['note']}")
    if r["level"]:
        ma200 = f"{r['ma200']:.0f}" if r["ma200"] else "—"
        print(f"     IHSG {r['level']:.0f}  |  MA50 {r['ma50']:.0f}  |  MA200 {ma200}")
    print(f"{'='*60}")
    print("  Indikator (arah = efek buat saham IDX):")
    for i in snap["indikator"]:
        if i["ticker"] == "^JKSE":
            continue
        chg = f"{i['chg1mo']*100:+.1f}%" if i.get("chg1mo") is not None else "—"
        tag = {"bagus": "👍", "jelek": "👎"}.get(i.get("arah"), "")
        print(f"     {i['label']:8s} {i['level']:>11.2f}   1bln {chg:>7}  {tag}")
    print(f"\n  (asof {snap.get('asof')}) — dipakai /analisa & dashboard sebagai overlay makro.")


if __name__ == "__main__":
    main()
