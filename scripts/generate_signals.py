"""Hitung sinyal BUY/HOLD/SELL buat seluruh focus list -> simpan + tampilkan.

Gabung: teknikal (MA20/MA50/RSI/ATR dari harga) + sentimen (rata2 berita 14 hari).
"""
import argparse
import json
import pathlib
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pandas as pd   # noqa: E402

from trade.db import get_connection, init_db, replace_signals   # noqa: E402
from trade.indicators import atr, rsi, sma                       # noqa: E402
from trade.signals import SignalParams, decide                   # noqa: E402


def _flag(m):
    return "🇮🇩" if m == "IDX" else "🇺🇸"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sent-days", type=int, default=14)
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)

    market_of = {r["ticker"]: r["market"] for r in
                 conn.execute("SELECT ticker, market FROM focus_list")}
    if not market_of:
        print("focus_list kosong — jalanin scripts/screen.py dulu.")
        return

    # sentimen agregat per saham (14 hari terakhir)
    since = (datetime.now(timezone.utc) - timedelta(days=args.sent_days)).isoformat(timespec="seconds")
    sent_map = {r["ticker"]: (r["avg_sent"], r["n"]) for r in conn.execute(
        "SELECT ticker, AVG(sent_score) AS avg_sent, COUNT(*) AS n FROM news "
        "WHERE sent_score IS NOT NULL AND (published IS NULL OR published >= ?) "
        "GROUP BY ticker", (since,))}

    # harga seluruh focus list sekaligus
    df = pd.read_sql_query(
        "SELECT p.ticker, p.date, p.high, p.low, p.close FROM prices p "
        "JOIN focus_list f ON f.ticker = p.ticker ORDER BY p.ticker, p.date", conn)

    print(f"⚙️  Hitung sinyal buat {len(market_of)} saham focus list...\n", flush=True)

    out = []
    p = SignalParams()
    for ticker, g in df.groupby("ticker", sort=False):
        closes = pd.to_numeric(g["close"], errors="coerce").to_numpy()
        highs = pd.to_numeric(g["high"], errors="coerce").to_numpy()
        lows = pd.to_numeric(g["low"], errors="coerce").to_numpy()
        if len(closes) < 50:
            continue

        s_avg, s_n = sent_map.get(ticker, (0.0, 0))
        feat = {
            "close": float(closes[-1]),
            "ma20": sma(closes, 20), "ma50": sma(closes, 50),
            "rsi": rsi(closes, 14), "atr": atr(highs, lows, closes, 14),
            "sent": s_avg or 0.0, "n_news": s_n or 0,
        }
        d = decide(feat, p)
        out.append({
            "ticker": ticker, "market": market_of.get(ticker), "asof": g["date"].iloc[-1],
            "action": d["action"], "score": d["score"], "close": feat["close"],
            "ma20": feat["ma20"], "ma50": feat["ma50"], "rsi": feat["rsi"],
            "sent": round(feat["sent"], 3), "n_news": feat["n_news"],
            "stop": d["stop"], "target": d["target"], "reasons": json.dumps(d["reasons"]),
        })

    n = replace_signals(conn, out)

    counts = {"BUY": 0, "HOLD": 0, "SELL": 0}
    for s in out:
        counts[s["action"]] += 1

    print("=" * 70)
    print(f" SINYAL — {n} saham dihitung")
    print("=" * 70)
    print(f"   🟢 BUY {counts['BUY']}   ⚪ HOLD {counts['HOLD']}   🔴 SELL {counts['SELL']}")

    def fmt(v, market):
        if v is None:
            return "-"
        return f"{v:,.2f}" if market == "US" else f"{v:,.0f}"

    buys = sorted([s for s in out if s["action"] == "BUY"],
                  key=lambda x: x["score"], reverse=True)
    print(f"\n  ── TOP {args.top} KANDIDAT BUY (skor tertinggi) ──")
    print(f"  {'':3}{'ticker':10} {'harga':>11} {'skor':>5} {'RSI':>4} {'sent':>6}  stop → target")
    for s in buys[:args.top]:
        cur = "$" if s["market"] == "US" else "Rp"
        px = f"{cur}{fmt(s['close'], s['market'])}"
        stt = (f"{cur}{fmt(s['stop'], s['market'])} → {cur}{fmt(s['target'], s['market'])}"
               if s["stop"] else "-")
        print(f"  {_flag(s['market'])} {s['ticker']:10} {px:>11} "
              f"{s['score']:>5} {s['rsi'] or 0:>4.0f} {s['sent']:>+6.2f}  {stt}")
        print(f"       → {' · '.join(json.loads(s['reasons']))}")


if __name__ == "__main__":
    main()
