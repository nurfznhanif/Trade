"""Hitung sinyal BUY/HOLD/SELL buat semua saham focus_list -> tabel `signals` (langkah daily.py).

Gabung teknikal (MA20/MA50/RSI/ATR dari harga) + sentimen (rata-rata berita N hari) + pagar
fundamental (perusahaan rapuh gak boleh BUY).
"""
import _bootstrap  # noqa: F401  (path repo + UTF-8)

import argparse
import json
from datetime import datetime, timedelta, timezone

import pandas as pd

from trade.db import get_connection, init_db, replace_signals
from trade.fundamentals import red_flags
from trade.indicators import atr, rsi, sma
from trade.signals import SignalParams, decide


def _rp(v):
    return "-" if v is None else f"Rp{v:,.0f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sent-days", type=int, default=14, help="jendela sentimen berita (hari)")
    ap.add_argument("--top", type=int, default=15, help="jumlah kandidat BUY yang dicetak")
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)

    market_of = {r["ticker"]: r["market"] for r in conn.execute("SELECT ticker, market FROM focus_list")}
    if not market_of:
        print("focus_list kosong — jalanin scripts/screen.py dulu.")
        return

    since = (datetime.now(timezone.utc) - timedelta(days=args.sent_days)).isoformat(timespec="seconds")
    sent_map = {r["ticker"]: (r["avg_sent"], r["n"]) for r in conn.execute(
        "SELECT ticker, AVG(sent_score) AS avg_sent, COUNT(*) AS n FROM news "
        "WHERE sent_score IS NOT NULL AND (published IS NULL OR published >= ?) "
        "GROUP BY ticker", (since,))}
    fund_flags = {r["ticker"]: red_flags(dict(r)) for r in conn.execute(
        "SELECT ticker, per, pbv, roe, der, div_yield, margin, market_cap FROM fundamentals")}
    df = pd.read_sql_query(
        "SELECT p.ticker, p.date, p.high, p.low, p.close FROM prices p "
        "JOIN focus_list f ON f.ticker = p.ticker ORDER BY p.ticker, p.date", conn)

    print(f"Hitung sinyal buat {len(market_of)} saham focus list...\n", flush=True)

    out = []
    blocked = 0
    p = SignalParams()
    for ticker, g in df.groupby("ticker", sort=False):
        closes = pd.to_numeric(g["close"], errors="coerce").to_numpy()
        highs = pd.to_numeric(g["high"], errors="coerce").to_numpy()
        lows = pd.to_numeric(g["low"], errors="coerce").to_numpy()
        if len(closes) < 50:
            continue

        s_avg, s_n = sent_map.get(ticker, (0.0, 0))
        flags = fund_flags.get(ticker)
        feat = {
            "close": float(closes[-1]),
            "ma20": sma(closes, 20), "ma50": sma(closes, 50),
            "rsi": rsi(closes, 14), "atr": atr(highs, lows, closes, 14),
            "sent": s_avg or 0.0, "n_news": s_n or 0, "fund_flags": flags,
        }
        d = decide(feat, p)
        if flags and d["score"] >= p.buy_th:
            blocked += 1
        out.append({
            "ticker": ticker, "market": market_of.get(ticker), "asof": g["date"].iloc[-1],
            "action": d["action"], "score": d["score"], "close": feat["close"],
            "ma20": feat["ma20"], "ma50": feat["ma50"], "rsi": feat["rsi"],
            "sent": round(feat["sent"], 3), "n_news": feat["n_news"],
            "stop": d["stop"], "target": d["target"], "reasons": json.dumps(d["reasons"]),
        })

    n = replace_signals(conn, out)
    counts = {a: sum(s["action"] == a for s in out) for a in ("BUY", "HOLD", "SELL")}

    print("=" * 70)
    print(f" SINYAL — {n} saham dihitung")
    print("=" * 70)
    print(f"   BUY {counts['BUY']}   HOLD {counts['HOLD']}   SELL {counts['SELL']}")
    print(f"   {blocked} calon BUY DIBLOK pagar fundamental (perusahaan rapuh)")

    buys = sorted((s for s in out if s["action"] == "BUY"), key=lambda x: x["score"], reverse=True)
    print(f"\n  -- TOP {args.top} KANDIDAT BUY (skor tertinggi) --")
    print(f"  {'ticker':10} {'harga':>11} {'skor':>5} {'RSI':>4} {'sent':>6}  stop -> target")
    for s in buys[:args.top]:
        stt = f"{_rp(s['stop'])} -> {_rp(s['target'])}" if s["stop"] else "-"
        print(f"  {s['ticker']:10} {_rp(s['close']):>11} "
              f"{s['score']:>5} {s['rsi'] or 0:>4.0f} {s['sent']:>+6.2f}  {stt}")
        print(f"       alasan: {' · '.join(json.loads(s['reasons']))}")


if __name__ == "__main__":
    main()
