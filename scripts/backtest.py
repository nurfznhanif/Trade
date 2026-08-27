"""Jalanin backtest point-in-time di seluruh focus list + banding vs beli acak.

Indikator diprecompute vectorized (rolling) -> cepat walau histori bertahun-tahun.

Contoh:
  python scripts/backtest.py                                # trailing stop, semua
  python scripts/backtest.py --exit-mode fixed              # versi target 2:1 (lama)
  python scripts/backtest.py --market IDX --limit 200
"""
import argparse
import csv
import pathlib
import sys
import time
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import numpy as np      # noqa: E402
import pandas as pd     # noqa: E402

from trade.backtest import BTParams, backtest_ticker, summarize   # noqa: E402
from trade.backtest import net_return                             # noqa: E402
from trade.config import DATA_DIR                                 # noqa: E402
from trade.db import get_connection, init_db                      # noqa: E402
from trade.signals import SignalParams                            # noqa: E402

BASE_H = 20   # horizon pembanding "beli-tahan" (hari bursa), dipatok biar stabil


def _ord(iso_date):
    try:
        return date.fromisoformat(iso_date[:10]).toordinal()
    except (ValueError, TypeError):
        return None


def _indicators(close_s, high_s, low_s):
    ma20 = close_s.rolling(20).mean().to_numpy()
    ma50 = close_s.rolling(50).mean().to_numpy()
    delta = close_s.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rsi_a = (100 - 100 / (1 + gain / loss)).to_numpy()
    prev = close_s.shift(1)
    tr = pd.concat([high_s - low_s, (high_s - prev).abs(), (low_s - prev).abs()],
                   axis=1).max(axis=1)
    atr_a = tr.rolling(14).mean().to_numpy()
    return ma20, ma50, rsi_a, atr_a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["US", "IDX"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--exit-mode", choices=["trailing", "fixed"], default="trailing")
    ap.add_argument("--max-hold", type=int, default=40)
    ap.add_argument("--no-costs", action="store_true", help="matiin biaya transaksi (liat gross)")
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)
    sp = SignalParams()
    bt = BTParams(exit_mode=args.exit_mode, max_hold=args.max_hold,
                  apply_costs=not args.no_costs)
    t0 = time.time()

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
    print(f"[{time.time()-t0:.1f}s] focus {len(tickers)} saham; baca berita...", flush=True)

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

    print(f"[{time.time()-t0:.1f}s] berita beres; baca harga...", flush=True)
    df = pd.read_sql_query(
        "SELECT p.ticker, p.date, p.high, p.low, p.close FROM prices p "
        "JOIN focus_list f ON f.ticker = p.ticker ORDER BY p.ticker, p.date", conn)
    df = df[df["ticker"].isin(tset)]
    ctxt = (f"biaya ON (beli {bt.fee_buy*100:.2f}%+jual {bt.fee_sell*100:.2f}%"
            f"+slip {bt.slippage*100:.2f}%/sisi)") if bt.apply_costs else "biaya OFF (gross)"
    print(f"[{time.time()-t0:.1f}s] harga {len(df)} baris | exit={bt.exit_mode} "
          f"max hold {bt.max_hold}hr | {ctxt} | mulai hitung...\n", flush=True)

    all_trades = []
    base_by = {"US": [], "IDX": []}
    processed = 0
    for ticker, g in df.groupby("ticker", sort=False):
        mk = market_of[ticker]
        dates = g["date"].tolist()
        dord = [_ord(d) for d in dates]
        close_s = pd.to_numeric(g["close"], errors="coerce")
        high_s = pd.to_numeric(g["high"], errors="coerce")
        low_s = pd.to_numeric(g["low"], errors="coerce")
        closes, highs, lows = close_s.to_numpy(), high_s.to_numpy(), low_s.to_numpy()
        n = len(closes)
        if n < bt.min_history + 2:
            continue

        if n > bt.min_history + BASE_H:      # baseline acak (horizon tetap BASE_H)
            a = closes[bt.min_history:n - BASE_H]
            b = closes[bt.min_history + BASE_H:n]
            gross = b / a - 1.0
            if bt.apply_costs:               # baseline juga kena biaya (adil)
                cb, cs = bt.fee_buy + bt.slippage, bt.fee_sell + bt.slippage
                gross = (1.0 + gross) * (1.0 - cs) / (1.0 + cb) - 1.0
            base_by.setdefault(mk, []).extend(gross.tolist())

        ma20, ma50, rsi_a, atr_a = _indicators(close_s, high_s, low_s)
        no = news_by.get(ticker, ([], []))
        trades = backtest_ticker(dord, highs, lows, closes, ma20, ma50, rsi_a, atr_a,
                                 no[0], no[1], sp, bt)
        for t in trades:
            t["ticker"] = ticker
            t["market"] = mk
            t["entry_date"] = dates[t["entry_i"]]
            t["exit_date"] = dates[t["exit_i"]]
        all_trades.extend(trades)
        processed += 1
        if processed % 1000 == 0:
            print(f"[{time.time()-t0:.1f}s] {processed} saham diproses...", flush=True)

    print(f"[{time.time()-t0:.1f}s] hitung beres, {len(all_trades)} trade.\n", flush=True)
    _report(all_trades, base_by)
    _write_csv(all_trades, bt.exit_mode)


def _pct(x):
    return f"{x*100:+.2f}%"


def _report(trades, base_by):
    s = summarize(trades)
    print("=" * 70)
    print(" HASIL BACKTEST")
    print("=" * 70)
    if not s.get("n"):
        print("  Gak ada trade kebentuk.")
        return

    all_base = base_by.get("US", []) + base_by.get("IDX", [])
    base = float(np.mean(all_base)) if all_base else 0.0
    print(f"  Jumlah trade       : {s['n']}")
    print(f"  Win rate           : {s['win_rate']*100:.1f}%")
    print(f"  Rata2 return/trade : {_pct(s['avg_ret'])}   <- dibandingin ke bawah")
    print(f"  Median return      : {_pct(s['median_ret'])}")
    print(f"  Rata2 menang/kalah : {_pct(s['avg_win'])} / {_pct(s['avg_loss'])}")
    pf = s["profit_factor"]
    print(f"  Profit factor      : {pf:.2f}   (>1 untung; >1.5 bagus)")
    print(f"  Rata2 nahan        : {s['avg_bars']:.1f} hari bursa")

    print(f"\n  📊 PEMBANDING (beli ACAK, tahan {BASE_H} hari): {_pct(base)}")
    edge = s["avg_ret"] - base
    print(f"      Edge total      : {_pct(edge)}   -> "
          f"{'ADA EDGE ✅' if edge > 0 else 'GAK ADA EDGE ❌'}")

    outc = {}
    for t in trades:
        outc[t["outcome"]] = outc.get(t["outcome"], 0) + 1
    print("\n  Cara keluar:", "  ".join(
        f"{k} {outc[k]}({outc[k]/s['n']*100:.0f}%)" for k in
        ("TARGET", "STOP", "TRAIL", "TIME", "EOD") if k in outc))

    print("\n  Per pasar (strategi vs beli acak):")
    for mk in ("US", "IDX"):
        sub = [t for t in trades if t["market"] == mk]
        if not sub:
            continue
        ss = summarize(sub)
        bmk = float(np.mean(base_by[mk])) if base_by.get(mk) else 0.0
        e = ss["avg_ret"] - bmk
        print(f"    {mk:3}: {ss['n']:5} trade, win {ss['win_rate']*100:.1f}%, "
              f"avg {_pct(ss['avg_ret'])} vs acak {_pct(bmk)} -> edge {_pct(e)} "
              f"{'✅' if e > 0 else '❌'}")


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
        w.writerows(trades)
    print(f"\n  💾 {len(trades)} trade -> {path}")


if __name__ == "__main__":
    main()
