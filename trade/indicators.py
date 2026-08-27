"""Indikator teknikal sederhana (MA, RSI, ATR) di atas numpy.

Semua fungsi terima array harga (numpy) & balikin nilai TERAKHIR (skalar) atau None
kalau datanya kurang. Sengaja simpel & transparan biar gampang diaudit.
"""
from __future__ import annotations

import math

import numpy as np


def _clean(v):
    if v is None:
        return None
    f = float(v)
    return None if math.isnan(f) else round(f, 4)


def sma(closes, n: int):
    """Simple moving average n-hari terakhir."""
    if closes is None or len(closes) < n:
        return None
    return _clean(np.mean(closes[-n:]))


def rsi(closes, n: int = 14):
    """RSI (versi rata2 sederhana). 0-100. >70 overbought, <30 oversold."""
    if closes is None or len(closes) < n + 1:
        return None
    diff = np.diff(closes[-(n + 1):])
    gains = diff[diff > 0].sum()
    losses = -diff[diff < 0].sum()
    if losses == 0:
        return 100.0 if gains > 0 else 50.0
    rs = gains / losses
    return _clean(100 - 100 / (1 + rs))


def atr(highs, lows, closes, n: int = 14):
    """Average True Range n-hari — buat ukur volatilitas (dipakai set stop-loss)."""
    if closes is None or len(closes) < n + 1:
        return None
    trs = []
    for i in range(len(closes) - n, len(closes)):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        if any(x is None or (isinstance(x, float) and math.isnan(x)) for x in (h, l, pc)):
            continue
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if not trs:
        return None
    return _clean(np.mean(trs))
