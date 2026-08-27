"""Jalanin backtest point-in-time di seluruh focus list + banding vs beli acak.

Contoh:
  python scripts/backtest.py --limit 100     # tes cepat 100 saham
  python scripts/backtest.py                  # full focus list
  python scripts/backtest.py --market IDX     # IDX aja
"""
import argparse
import csv
import pathlib
import sys
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import numpy as np      # noqa: E402
import pandas as pd     # noqa: E402

from trade.backtest import BTParams, backtest_ticker, summarize   # noqa: E402
from trade.config import DATA_DIR                                 # noqa: E402
from trade.db import get_connection, init_db                      # noqa: E402
from trade.signals import SignalParams                            # noqa: E402


def _ord(iso_date):
    try:
        return date.fromisoformat(iso_date[:10]).toordinal()
    except (ValueError, TypeError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["US", "IDX"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--max-hold", type=int, default=20)
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)
    sp, bt = SignalParams(), BTParams(max_hold=args.max_hold)

    q = "SELECT ticker, market FROM focus_list"
    params = []
    if args.market:
        q += " WHERE market = ?"
        params.append(args.market)
    market_of = {r["ticker"]: r["market"] for r in conn.execute(q, params)}
    tickers = list(market_of)
    if args.limit:
        tickers = tickers[:args.limit]
    tset = set(tickers)

    # berita per ticker (published + sent_score), buat sentimen point-in-time
    news_by = {}
    for r in conn.execute(
        "SELECT ticker, published, sent_score FROM news "
        "WHERE sent_score IS NOT NULL AND published IS NOT NULL"):
        if r["ticker"] not in tset:
            continue
        o = _ord(r["published"])
        if o is not None:
            news_by.setdefault(r["ticker"], ([], []))
            news_by[r["ticker"]][0].append(o)
            news_by[r["ticker"]][1].append(r["sent_score"])

    # harga
    df = pd.read_sql_query(
        "SELECT p.ticker, p.date, p.high, p.low, p.close FROM prices p "
        "JOIN focus_list f ON f.ticker = p.ticker ORDER BY p.ticker, p.date", conn)

    print(f"🔬 Backtest {len(tickers)} saham (max hold {bt.max_hold} hari, anti-lookahead)...\n",
          flush=True)

    all_trades = []
    base_by = {"US": [], "IDX": []}
    for ticker, g in df.groupby("ticker", sort=False):
        if ticker not in tset:
            continue
        mk = market_of[ticker]
        dates = g["date"].tolist()
        dord = [_ord(d) for d in dates]
        highs = pd.to_numeric(g["high"], errors="coerce").to_numpy()
        lows = pd.to_numeric(g["low"], errors="coerce").to_numpy()
        closes = pd.to_numeric(g["close"], errors="coerce").to_numpy()
        n = len(closes)
        if n < bt.min_history + 2:
            continue

        # baseline acak per-pasar: return H-hari ke depan dari semua bar tradeable
        H = bt.max_hold
        if n > bt.min_history + H:
            a = closes[bt.min_history:n - H]
            b = closes[bt.min_history + H:n]
            base_by.setdefault(mk, []).extend((b / a - 1.0).tolist())

        no = news_by.get(ticker, ([], []))
        trades = backtest_ticker(dord, highs, lows, closes, no[0], no[1], sp, bt)
        for t in trades:
            t["ticker"] = ticker
            t["market"] = mk
            t["entry_date"] = dates[t["entry_i"]]
            t["exit_date"] = dates[t["exit_i"]]
        all_trades.extend(trades)

    _report(all_trades, base_by, bt)
    _write_csv(all_trades)


def _pct(x):
    return f"{x*100:+.2f}%"


def _report(trades, base_by, bt):
    s = summarize(trades)
    print("=" * 70)
    print(" HASIL BACKTEST")
    print("=" * 70)
    if not s.get("n"):
        print("  Gak ada trade kebentuk.")
        return

    all_base = base_by.get("US", []) + base_by.get("IDX", [])
    base = float(np.mean(all_base)) if all_base else 0.0
    print(f"  Jumlah trade      : {s['n']}")
    print(f"  Win rate          : {s['win_rate']*100:.1f}%")
    print(f"  Rata2 return/trade : {_pct(s['avg_ret'])}   <- ini yang dibandingin")
    print(f"  Median return     : {_pct(s['median_ret'])}")
    print(f"  Rata2 menang      : {_pct(s['avg_win'])}")
    print(f"  Rata2 kalah       : {_pct(s['avg_loss'])}")
    pf = s["profit_factor"]
    print(f"  Profit factor     : {pf:.2f}   (>1 = untung; >1.5 bagus)")
    print(f"  Rata2 nahan       : {s['avg_bars']:.1f} hari bursa")

    print(f"\n  📊 PEMBANDING (beli ACAK, tahan {bt.max_hold} hari): {_pct(base)}")
    edge = s["avg_ret"] - base
    verdict = "ADA EDGE ✅" if edge > 0 else "GAK ADA EDGE ❌"
    print(f"      Selisih (edge)  : {_pct(edge)}   -> {verdict}")

    # rincian keluar
    outc = {}
    for t in trades:
        outc[t["outcome"]] = outc.get(t["outcome"], 0) + 1
    print("\n  Cara keluar:")
    for k in ("TARGET", "STOP", "TIME", "EOD"):
        if k in outc:
            print(f"    {k:7}: {outc[k]:5}  ({outc[k]/s['n']*100:.0f}%)")

    # per pasar: strategi vs acak (edge yang adil, sesama pasar)
    print("\n  Per pasar (strategi vs beli acak):")
    for mk in ("US", "IDX"):
        sub = [t for t in trades if t["market"] == mk]
        if not sub:
            continue
        ss = summarize(sub)
        bmk = float(np.mean(base_by[mk])) if base_by.get(mk) else 0.0
        e = ss["avg_ret"] - bmk
        v = "✅" if e > 0 else "❌"
        print(f"    {mk:3}: {ss['n']:5} trade, win {ss['win_rate']*100:.1f}%, "
              f"avg {_pct(ss['avg_ret'])} vs acak {_pct(bmk)} -> edge {_pct(e)} {v}")


def _write_csv(trades):
    if not trades:
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "backtest_trades.csv"
    cols = ["ticker", "market", "entry_date", "exit_date", "entry", "exit",
            "ret", "bars", "outcome", "n_news"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for t in trades:
            w.writerow(t)
    print(f"\n  💾 {len(trades)} trade ditulis ke {path}")


if __name__ == "__main__":
    main()
