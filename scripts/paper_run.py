"""Paper trading forward-test: 2 portfolio (FULL vs TECH) + A/B sentimen.

Mulai dari 'inception' (dikunci sekali di DB), simulasi maju ke tanggal terakhir.
Jalanin lagi tiap hari -> otomatis maju ikut data baru.
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

import pandas as pd     # noqa: E402

from trade.backtest import BTParams, backtest_ticker, net_return   # noqa: E402
from trade.config import DATA_DIR                              # noqa: E402
from trade.db import get_connection, get_or_init_paper_state, init_db   # noqa: E402
from trade.paper import PaperParams, simulate_portfolio        # noqa: E402
from trade.signals import SignalParams                         # noqa: E402


def _ord(d):
    try:
        return date.fromisoformat(d[:10]).toordinal()
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
    ap.add_argument("--since-days", type=int, default=120,
                    help="(saat init) mulai paper trading N hari bursa lalu")
    ap.add_argument("--capital", type=float, default=100_000_000)
    ap.add_argument("--max-pos", type=int, default=10)
    args = ap.parse_args()

    conn = get_connection()
    init_db(conn)
    sp, bt = SignalParams(), BTParams()             # trailing + biaya (default)
    pp = PaperParams(start_capital=args.capital, max_positions=args.max_pos)

    tset = {r["ticker"] for r in conn.execute("SELECT ticker FROM focus_list")}
    if not tset:
        print("focus_list kosong — jalanin screen.py dulu.")
        return

    news_by = {}
    for r in conn.execute("SELECT ticker, published, sent_score FROM news "
                          "WHERE sent_score IS NOT NULL AND published IS NOT NULL"):
        if r["ticker"] not in tset:
            continue
        o = _ord(r["published"])
        if o is not None:
            news_by.setdefault(r["ticker"], ([], []))
            news_by[r["ticker"]][0].append(o)
            news_by[r["ticker"]][1].append(r["sent_score"])

    df = pd.read_sql_query(
        "SELECT p.ticker, p.date, p.high, p.low, p.close FROM prices p "
        "JOIN focus_list f ON f.ticker = p.ticker ORDER BY p.ticker, p.date", conn)
    df = df[df["ticker"].isin(tset)]

    all_dates = sorted(df["date"].unique())
    latest = all_dates[-1]
    default_incept = all_dates[max(0, len(all_dates) - 1 - args.since_days)]
    st = get_or_init_paper_state(conn, default_incept, args.capital)
    inception = st["inception_date"]
    inception_ord = _ord(inception)

    print(f"📈 PAPER TRADING — inception {inception[:10]} → {latest[:10]}")
    print(f"   Modal {_rp(pp.start_capital)} | max {pp.max_positions} posisi | trailing + biaya\n",
          flush=True)

    cand = {"full": [], "tech": []}
    bench = []                                 # buy-and-hold semua saham (equal weight)
    for ticker, g in df.groupby("ticker", sort=False):
        dates = g["date"].tolist()
        dord = [_ord(d) for d in dates]
        close_s = pd.to_numeric(g["close"], errors="coerce")
        high_s = pd.to_numeric(g["high"], errors="coerce")
        low_s = pd.to_numeric(g["low"], errors="coerce")
        closes, highs, lows = close_s.to_numpy(), high_s.to_numpy(), low_s.to_numpy()
        if len(closes) < bt.min_history + 2:
            continue

        ii = next((k for k, o in enumerate(dord) if o is not None and o >= inception_ord), None)
        if ii is not None and closes[ii] > 0:
            bench.append(net_return(closes[-1] / closes[ii] - 1.0, bt))

        ma20, ma50, rsi_a, atr_a = _indicators(close_s, high_s, low_s)
        no = news_by.get(ticker, ([], []))

        for label, news in [("full", no), ("tech", ([], []))]:
            for t in backtest_ticker(dord, highs, lows, closes, ma20, ma50, rsi_a, atr_a,
                                     news[0], news[1], sp, bt):
                eo = dord[t["entry_i"]]
                if eo is None or eo < inception_ord:      # cuma trade setelah inception
                    continue
                t = {**t, "ticker": ticker, "entry_ord": eo, "exit_ord": dord[t["exit_i"]],
                     "entry_date": dates[t["entry_i"]], "exit_date": dates[t["exit_i"]]}
                cand[label].append(t)

    res = {k: simulate_portfolio(v, pp) for k, v in cand.items()}
    bench_ret = sum(bench) / len(bench) if bench else 0.0
    _report(res, bench_ret)
    _write_open(res["full"])


def _rp(x):
    return f"Rp{x:,.0f}"


def _pct(x):
    return f"{x*100:+.2f}%"


def _report(res, bench_ret):
    print("=" * 66)
    print(" HASIL PAPER TRADING")
    print("=" * 66)
    for label, name in [("full", "FULL (teknikal + sentimen)"), ("tech", "TECH (teknikal doang)")]:
        r = res[label]
        print(f"\n  ▶ {name}")
        print(f"     Equity   : {_rp(r['equity'])}  ({_pct(r['ret_pct'])})")
        print(f"     Realized : {_rp(r['realized'])}    Open(unrealized): {_rp(r['unreal'])}")
        print(f"     Trade    : {r['n_taken']} diambil "
              f"({r['n_closed']} closed win {r['win_rate']*100:.0f}%, {r['n_open']} open)")

    print(f"\n  📊 PEMBANDING (beli SEMUA saham focus, tahan dari inception): {_pct(bench_ret)}")
    a_full = res["full"]["ret_pct"] - bench_ret
    a_tech = res["tech"]["ret_pct"] - bench_ret
    print(f"      ALPHA FULL: {_pct(a_full)}  |  ALPHA TECH: {_pct(a_tech)}  "
          f"→ {'ada alpha ✅' if max(a_full, a_tech) > 0 else 'belum ada alpha (cuma ikut pasar) ❌'}")

    diff = res["full"]["ret_pct"] - res["tech"]["ret_pct"]
    verd = ("sentimen NAMBAH nilai ✅" if diff > 0
            else "sentimen belum nambah / malah ngurangin ❌" if diff < 0 else "netral")
    print(f"\n  🔬 A/B SENTIMEN: FULL − TECH = {_pct(diff)} → {verd}")
    print("     (berita historis masih tipis → ini indikasi awal, makin valid seiring waktu)")

    op = sorted(res["full"]["open_positions"], key=lambda t: t["ret"], reverse=True)
    if op:
        print(f"\n  📌 POSISI TERBUKA sekarang (FULL, {len(op)}):")
        for t in op[:12]:
            print(f"     {t['ticker']:10s} masuk {t['entry_date'][:10]} @ {t['entry']:.0f} "
                  f" → now {_pct(t['ret'])}")


def _write_open(r):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "paper_open_positions.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "entry_date", "entry", "current_ret", "outcome"])
        for t in r["open_positions"]:
            w.writerow([t["ticker"], t["entry_date"][:10], t["entry"], round(t["ret"], 4), t["outcome"]])
    print(f"\n  💾 posisi terbuka → {path}")


if __name__ == "__main__":
    main()
