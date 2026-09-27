"""Alat RISET: backtest point-in-time mesin sinyal di seluruh focus_list + banding vs beli acak.

Buat nguji perubahan aturan sinyal/exit SEBELUM dipakai (gak ikut daily.py).

  python scripts/backtest.py                        # trailing stop, semua saham focus
  python scripts/backtest.py --exit-mode fixed      # target 2:1 (versi lama, pembanding)
  python scripts/backtest.py --limit 200 --no-costs
"""
import _bootstrap  # noqa: F401  (path repo + UTF-8)

import argparse
import csv
import time

import numpy as np
import pandas as pd

from trade.backtest import (BTParams, backtest_ticker, day_ord, indicator_arrays, load_focus_prices,
                            load_news_sentiment, net_return, summarize)
from trade.config import DATA_DIR
from trade.db import get_connection, init_db
from trade.signals import SignalParams

BASE_H = 20   # horizon pembanding "beli acak lalu tahan" (hari bursa), dipatok biar stabil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="ambil N saham pertama (buat tes)")
    ap.add_argument("--exit-mode", choices=["trailing", "fixed"], default="trailing")
    ap.add_argument("--max-hold", type=int, default=40)
    ap.add_argument("--no-costs", action="store_true", help="matiin biaya transaksi (liat gross)")
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)
    sp = SignalParams()
    bt = BTParams(exit_mode=args.exit_mode, max_hold=args.max_hold, apply_costs=not args.no_costs)
    t0 = time.time()

    tickers = [r["ticker"] for r in conn.execute("SELECT ticker FROM focus_list ORDER BY rank")][:args.limit]
    print(f"[{time.time()-t0:.1f}s] focus {len(tickers)} saham; baca berita + harga...", flush=True)
    news_by = load_news_sentiment(conn, tickers)
    df = load_focus_prices(conn, tickers)
    ctxt = (f"biaya ON (beli {bt.fee_buy*100:.2f}%+jual {bt.fee_sell*100:.2f}%"
            f"+slip {bt.slippage*100:.2f}%/sisi)") if bt.apply_costs else "biaya OFF (gross)"
    print(f"[{time.time()-t0:.1f}s] harga {len(df)} baris | exit={bt.exit_mode} "
          f"max hold {bt.max_hold}hr | {ctxt} | mulai hitung...\n", flush=True)

    all_trades, base = [], []
    for ticker, g in df.groupby("ticker", sort=False):
        dates = g["date"].tolist()
        dord = [day_ord(d) for d in dates]
        close_s = pd.to_numeric(g["close"], errors="coerce")
        high_s = pd.to_numeric(g["high"], errors="coerce")
        low_s = pd.to_numeric(g["low"], errors="coerce")
        closes, highs, lows = close_s.to_numpy(), high_s.to_numpy(), low_s.to_numpy()
        n = len(closes)
        if n < bt.min_history + 2:
            continue

        if n > bt.min_history + BASE_H:      # pembanding: beli di hari mana aja, tahan BASE_H hari
            gross = closes[bt.min_history + BASE_H:n] / closes[bt.min_history:n - BASE_H] - 1.0
            base.extend(net_return(gross, bt).tolist())   # kena biaya juga biar adil

        ma20, ma50, rsi_a, atr_a = indicator_arrays(close_s, high_s, low_s)
        n_ord, n_sent = news_by.get(ticker, ([], []))
        for t in backtest_ticker(dord, highs, lows, closes, ma20, ma50, rsi_a, atr_a, n_ord, n_sent, sp, bt):
            all_trades.append({**t, "ticker": ticker, "entry_date": dates[t["entry_i"]],
                               "exit_date": dates[t["exit_i"]]})

    print(f"[{time.time()-t0:.1f}s] hitung beres, {len(all_trades)} trade.\n", flush=True)
    _report(all_trades, base)
    _write_csv(all_trades, bt.exit_mode)


def _pct(x):
    return f"{x*100:+.2f}%"


def _report(trades, base_rets):
    s = summarize(trades)
    print("=" * 70)
    print(" HASIL BACKTEST")
    print("=" * 70)
    if not s.get("n"):
        print("  Gak ada trade kebentuk.")
        return

    base = float(np.mean(base_rets)) if base_rets else 0.0
    print(f"  Jumlah trade       : {s['n']}")
    print(f"  Win rate           : {s['win_rate']*100:.1f}%")
    print(f"  Rata2 return/trade : {_pct(s['avg_ret'])}   <- dibandingin ke bawah")
    print(f"  Median return      : {_pct(s['median_ret'])}")
    print(f"  Rata2 menang/kalah : {_pct(s['avg_win'])} / {_pct(s['avg_loss'])}")
    print(f"  Profit factor      : {s['profit_factor']:.2f}   (>1 untung; >1.5 bagus)")
    print(f"  Rata2 nahan        : {s['avg_bars']:.1f} hari bursa")

    edge = s["avg_ret"] - base
    print(f"\n  PEMBANDING (beli ACAK, tahan {BASE_H} hari): {_pct(base)}")
    print(f"      Edge            : {_pct(edge)}   -> {'ADA EDGE' if edge > 0 else 'GAK ADA EDGE'}")

    outc = {}
    for t in trades:
        outc[t["outcome"]] = outc.get(t["outcome"], 0) + 1
    print("\n  Cara keluar:", "  ".join(
        f"{k} {outc[k]}({outc[k]/s['n']*100:.0f}%)" for k in
        ("TARGET", "STOP", "TRAIL", "TIME", "EOD") if k in outc))


def _write_csv(trades, tag):
    if not trades:
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"backtest_trades_{tag}.csv"
    cols = ["ticker", "market", "entry_date", "exit_date", "entry", "exit",
            "ret", "bars", "outcome", "n_news"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows({**t, "market": "IDX"} for t in trades)
    print(f"\n  {len(trades)} trade -> {path}")


if __name__ == "__main__":
    main()
