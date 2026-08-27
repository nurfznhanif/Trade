"""Backtest event-driven, long-only, POINT-IN-TIME (anti lookahead bias).

Indikator (MA/RSI/ATR) DIPRECOMPUTE vectorized di runner (rolling window = cuma
pakai data s/d hari itu, jadi tetap anti-lookahead) lalu dioper ke sini sebagai
array. Di sini tinggal jalan per hari -> cepat walau histori bertahun-tahun.

Exit:
  - "trailing": stop awal = entry - stop_mult*ATR, lalu NAIK ngikutin harga
    tertinggi (highest_high - trail_mult*ATR). Biarin pemenang lari.
  - "fixed"   : stop tetap + target reward_risk:1 (versi lama, buat pembanding).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .signals import SignalParams, decide


@dataclass
class BTParams:
    exit_mode: str = "trailing"   # "trailing" atau "fixed"
    max_hold: int = 40            # batas nahan (hari bursa) — backstop
    stop_mult: float = 2.0        # stop awal = entry - stop_mult*ATR
    trail_mult: float = 3.0       # trailing = highest_high - trail_mult*ATR
    reward_risk: float = 2.0      # (mode fixed) target = entry + rr*risiko
    min_history: int = 50
    sent_window_days: int = 14
    # biaya transaksi (IDX): dipotong dari tiap trade
    apply_costs: bool = True
    fee_buy: float = 0.0015       # 0.15% beli
    fee_sell: float = 0.0025      # 0.25% jual (fee + pajak)
    slippage: float = 0.0010      # 0.10% per sisi (spread/impact)


def _nn(x):
    if x is None:
        return None
    x = float(x)
    return None if math.isnan(x) else x


def net_return(gross, bt):
    """Return bersih setelah biaya: bayar lebih pas beli, terima kurang pas jual."""
    if not bt.apply_costs:
        return gross
    cb = bt.fee_buy + bt.slippage
    cs = bt.fee_sell + bt.slippage
    return (1.0 + gross) * (1.0 - cs) / (1.0 + cb) - 1.0


def _sentiment_at(day_ord, news_ord, news_sent, window):
    if not news_ord:
        return 0.0, 0
    lo = day_ord - window
    vals = [s for o, s in zip(news_ord, news_sent) if lo < o <= day_ord]
    if not vals:
        return 0.0, 0
    return float(sum(vals) / len(vals)), len(vals)


def _sim_fixed(highs, lows, closes, i, stop, target, bt):
    for k in range(i + 1, min(i + 1 + bt.max_hold, len(closes))):
        if lows[k] <= stop:
            return k, stop, "STOP"
        if highs[k] >= target:
            return k, target, "TARGET"
    k = min(i + bt.max_hold, len(closes) - 1)
    return k, closes[k], ("TIME" if k == i + bt.max_hold else "EOD")


def _sim_trailing(highs, lows, closes, i, stop, atr_e, bt):
    hh = highs[i]
    end = min(i + bt.max_hold, len(closes) - 1)
    for k in range(i + 1, end + 1):
        if lows[k] <= stop:                       # cek stop (dari data s/d k-1)
            return k, stop, "TRAIL"
        if highs[k] > hh:
            hh = highs[k]
        stop = max(stop, hh - bt.trail_mult * atr_e)   # trailing NAIK aja
    return end, closes[end], ("TIME" if end == i + bt.max_hold else "EOD")


def backtest_ticker(dates_ord, highs, lows, closes, ma20, ma50, rsi_a, atr_a,
                    news_ord, news_sent, sp: SignalParams, bt: BTParams):
    """Return list of trade dict. Indikator dioper sbg array (aligned dgn closes)."""
    trades = []
    n = len(closes)
    i = bt.min_history
    while i < n:
        sent, n_news = _sentiment_at(dates_ord[i], news_ord, news_sent, bt.sent_window_days)
        atr_e = _nn(atr_a[i])
        feat = {
            "close": float(closes[i]),
            "ma20": _nn(ma20[i]), "ma50": _nn(ma50[i]),
            "rsi": _nn(rsi_a[i]), "atr": atr_e,
            "sent": sent, "n_news": n_news,
        }
        d = decide(feat, sp)

        if d["action"] == "BUY" and atr_e:
            entry = float(closes[i])
            init_stop = entry - bt.stop_mult * atr_e
            if not (0 < init_stop < entry):
                i += 1
                continue
            if bt.exit_mode == "trailing":
                ei, epx, out = _sim_trailing(highs, lows, closes, i, init_stop, atr_e, bt)
            else:
                target = entry + bt.reward_risk * (entry - init_stop)
                ei, epx, out = _sim_fixed(highs, lows, closes, i, init_stop, target, bt)

            gross = float(epx) / entry - 1.0
            trades.append({
                "entry_i": i, "exit_i": ei, "entry": entry, "exit": float(epx),
                "gross": gross, "ret": net_return(gross, bt), "bars": ei - i,
                "outcome": out, "n_news": n_news,
            })
            i = ei + 1
        else:
            i += 1
    return trades


def summarize(trades):
    if not trades:
        return {"n": 0}
    rets = np.array([t["ret"] for t in trades])
    wins = rets[rets > 0]
    losses = rets[rets <= 0]
    gw, gl = wins.sum(), -losses.sum()
    return {
        "n": len(trades),
        "win_rate": len(wins) / len(rets),
        "avg_ret": rets.mean(),
        "median_ret": float(np.median(rets)),
        "avg_win": wins.mean() if len(wins) else 0.0,
        "avg_loss": losses.mean() if len(losses) else 0.0,
        "profit_factor": (gw / gl) if gl > 0 else float("inf"),
        "avg_bars": np.mean([t["bars"] for t in trades]),
        "expectancy": rets.mean(),
    }
