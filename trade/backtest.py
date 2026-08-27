"""Backtest event-driven, long-only, POINT-IN-TIME (anti lookahead bias).

Aturan main di tiap hari t (cuma pakai data s/d t):
  - Hitung sinyal (teknikal + sentimen dari berita yang PUBLISH s/d t).
  - Kalau BUY & lagi tidak punya posisi -> MASUK di close[t]; pasang stop & target.
  - Hari-hari berikut dicek berurutan:
        low <= stop   -> keluar di stop   (STOP)
        high >= target-> keluar di target (TARGET)
        nahan > max_hold -> keluar di close (TIME)
    (kalau satu hari kena dua-duanya, anggap STOP dulu — konservatif)
  - Gak overlap di ticker yang sama.

CATATAN JUJUR: berita kita baru dikumpulin belakangan, jadi buat tanggal lama
n_news biasanya 0 -> di masa lampau sinyal praktis TEKNIKAL doang. Bagian sentimen
baru bener-bener keuji lewat paper trading ke depan (atau arsip berita historis).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .indicators import atr, rsi, sma
from .signals import SignalParams, decide


@dataclass
class BTParams:
    max_hold: int = 20        # hari bursa maksimal nahan posisi (swing)
    min_history: int = 50     # butuh >=50 bar buat MA50
    sent_window_days: int = 14


def _sentiment_at(day_ord, news_ord, news_sent, window):
    """Rata2 sentimen berita yang publish di (day-window, day]. Anti lookahead."""
    if not news_ord:
        return 0.0, 0
    lo = day_ord - window
    vals = [s for o, s in zip(news_ord, news_sent) if lo < o <= day_ord]
    if not vals:
        return 0.0, 0
    return float(sum(vals) / len(vals)), len(vals)


def backtest_ticker(dates_ord, highs, lows, closes, news_ord, news_sent,
                    sp: SignalParams, bt: BTParams):
    """Return list of trade dict buat satu ticker."""
    trades = []
    n = len(closes)
    i = bt.min_history
    while i < n:
        c = closes[:i + 1]
        sent, n_news = _sentiment_at(dates_ord[i], news_ord, news_sent, bt.sent_window_days)
        feat = {
            "close": float(closes[i]),
            "ma20": sma(c, 20), "ma50": sma(c, 50),
            "rsi": rsi(c, 14), "atr": atr(highs[:i + 1], lows[:i + 1], c, 14),
            "sent": sent, "n_news": n_news,
        }
        d = decide(feat, sp)

        if d["action"] == "BUY" and d["stop"]:
            entry, stop, target = closes[i], d["stop"], d["target"]
            exit_i = exit_px = outcome = None
            for k in range(i + 1, min(i + 1 + bt.max_hold, n)):
                if lows[k] <= stop:
                    exit_i, exit_px, outcome = k, stop, "STOP"
                    break
                if highs[k] >= target:
                    exit_i, exit_px, outcome = k, target, "TARGET"
                    break
            if exit_i is None:                      # kena batas waktu / mentok data
                k = min(i + bt.max_hold, n - 1)
                outcome = "TIME" if k == i + bt.max_hold else "EOD"
                exit_i, exit_px = k, closes[k]

            trades.append({
                "entry_i": i, "exit_i": exit_i, "entry": float(entry),
                "exit": float(exit_px), "ret": float(exit_px) / float(entry) - 1.0,
                "bars": exit_i - i, "outcome": outcome, "n_news": n_news,
            })
            i = exit_i + 1                          # gak overlap
        else:
            i += 1
    return trades


def summarize(trades):
    """Metrik agregat dari list trade."""
    if not trades:
        return {"n": 0}
    rets = np.array([t["ret"] for t in trades])
    wins = rets[rets > 0]
    losses = rets[rets <= 0]
    gross_win = wins.sum()
    gross_loss = -losses.sum()
    return {
        "n": len(trades),
        "win_rate": len(wins) / len(rets),
        "avg_ret": rets.mean(),
        "median_ret": float(np.median(rets)),
        "avg_win": wins.mean() if len(wins) else 0.0,
        "avg_loss": losses.mean() if len(losses) else 0.0,
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else float("inf"),
        "avg_bars": np.mean([t["bars"] for t in trades]),
        "expectancy": rets.mean(),
    }
