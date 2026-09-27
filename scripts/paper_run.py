"""Paper trading (duit bohongan) maju ke depan: 2 portfolio FULL (teknikal+sentimen) vs TECH
(teknikal doang) + pembanding beli-semua. Langkah daily.py.

Mulai dari 'inception' (dikunci sekali di DB), disimulasi sampai data terakhir — jalanin tiap hari,
otomatis maju. Posisi yang masih kebuka ditulis ke data/paper_open_positions.csv (dibaca brief.py).
"""
import _bootstrap  # noqa: F401  (path repo + UTF-8)

import argparse
import csv

import pandas as pd

from trade.backtest import (BTParams, backtest_ticker, day_ord, indicator_arrays, load_focus_prices,
                            load_news_sentiment, net_return)
from trade.config import DATA_DIR
from trade.db import get_connection, get_or_init_paper_state, init_db
from trade.paper import PaperParams, simulate_portfolio
from trade.signals import SignalParams


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since-days", type=int, default=120,
                    help="(pas pertama kali) mulai paper trading N hari bursa lalu")
    ap.add_argument("--capital", type=float, default=100_000_000)
    ap.add_argument("--max-pos", type=int, default=10)
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)
    sp, bt = SignalParams(), BTParams()             # trailing + biaya (default)
    pp = PaperParams(start_capital=args.capital, max_positions=args.max_pos)

    tickers = [r["ticker"] for r in conn.execute("SELECT ticker FROM focus_list")]
    if not tickers:
        print("focus_list kosong — jalanin scripts/screen.py dulu.")
        return
    news_by = load_news_sentiment(conn, tickers)
    df = load_focus_prices(conn, tickers)

    all_dates = sorted(df["date"].unique())
    latest = all_dates[-1]
    default_incept = all_dates[max(0, len(all_dates) - 1 - args.since_days)]
    inception = get_or_init_paper_state(conn, default_incept, args.capital)["inception_date"]
    inception_ord = day_ord(inception)

    print(f"PAPER TRADING — inception {inception[:10]} -> {latest[:10]}")
    print(f"   Modal {_rp(pp.start_capital)} | max {pp.max_positions} posisi | trailing + biaya\n", flush=True)

    cand = {"full": [], "tech": []}
    bench = []                                 # beli-tahan semua saham (equal weight)
    for ticker, g in df.groupby("ticker", sort=False):
        dates = g["date"].tolist()
        dord = [day_ord(d) for d in dates]
        close_s = pd.to_numeric(g["close"], errors="coerce")
        high_s = pd.to_numeric(g["high"], errors="coerce")
        low_s = pd.to_numeric(g["low"], errors="coerce")
        closes, highs, lows = close_s.to_numpy(), high_s.to_numpy(), low_s.to_numpy()
        if len(closes) < bt.min_history + 2:
            continue

        ii = next((k for k, o in enumerate(dord) if o is not None and o >= inception_ord), None)
        if ii is not None and closes[ii] > 0:
            bench.append(net_return(closes[-1] / closes[ii] - 1.0, bt))

        ma20, ma50, rsi_a, atr_a = indicator_arrays(close_s, high_s, low_s)
        news = news_by.get(ticker, ([], []))
        for label, (n_ord, n_sent) in (("full", news), ("tech", ([], []))):
            for t in backtest_ticker(dord, highs, lows, closes, ma20, ma50, rsi_a, atr_a,
                                     n_ord, n_sent, sp, bt):
                eo = dord[t["entry_i"]]
                if eo is None or eo < inception_ord:      # cuma trade setelah inception
                    continue
                cand[label].append({**t, "ticker": ticker, "entry_ord": eo, "exit_ord": dord[t["exit_i"]],
                                    "entry_date": dates[t["entry_i"]], "exit_date": dates[t["exit_i"]]})

    res = {k: simulate_portfolio(v, pp) for k, v in cand.items()}
    _report(res, sum(bench) / len(bench) if bench else 0.0)
    _write_open(res["full"])


def _rp(x):
    return f"Rp{x:,.0f}"


def _pct(x):
    return f"{x*100:+.2f}%"


def _report(res, bench_ret):
    print("=" * 66)
    print(" HASIL PAPER TRADING")
    print("=" * 66)
    for label, name in (("full", "FULL (teknikal + sentimen)"), ("tech", "TECH (teknikal doang)")):
        r = res[label]
        print(f"\n  > {name}")
        print(f"     Equity   : {_rp(r['equity'])}  ({_pct(r['ret_pct'])})")
        print(f"     Realized : {_rp(r['realized'])}    Open(unrealized): {_rp(r['unreal'])}")
        print(f"     Trade    : {r['n_taken']} diambil "
              f"({r['n_closed']} closed win {r['win_rate']*100:.0f}%, {r['n_open']} open)")

    print(f"\n  PEMBANDING (beli SEMUA saham focus, tahan dari inception): {_pct(bench_ret)}")
    a_full = res["full"]["ret_pct"] - bench_ret
    a_tech = res["tech"]["ret_pct"] - bench_ret
    print(f"      ALPHA FULL: {_pct(a_full)}  |  ALPHA TECH: {_pct(a_tech)}  -> "
          f"{'ada alpha' if max(a_full, a_tech) > 0 else 'belum ada alpha (cuma ikut pasar)'}")

    diff = res["full"]["ret_pct"] - res["tech"]["ret_pct"]
    verd = ("sentimen NAMBAH nilai" if diff > 0
            else "sentimen belum nambah / malah ngurangin" if diff < 0 else "netral")
    print(f"\n  A/B SENTIMEN: FULL - TECH = {_pct(diff)} -> {verd}")
    print("     (berita historis masih tipis -> ini indikasi awal, makin valid seiring waktu)")

    op = sorted(res["full"]["open_positions"], key=lambda t: t["ret"], reverse=True)
    if op:
        print(f"\n  POSISI TERBUKA sekarang (FULL, {len(op)}):")
        for t in op[:12]:
            print(f"     {t['ticker']:10s} masuk {t['entry_date'][:10]} @ {t['entry']:.0f}  -> now {_pct(t['ret'])}")


def _write_open(r):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "paper_open_positions.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "entry_date", "entry", "current_ret", "outcome"])
        for t in r["open_positions"]:
            w.writerow([t["ticker"], t["entry_date"][:10], t["entry"], round(t["ret"], 4), t["outcome"]])
    print(f"\n  posisi terbuka -> {path}")


if __name__ == "__main__":
    main()
