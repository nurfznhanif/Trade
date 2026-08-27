"""Tarik harga historis via yfinance.

Jalan buat US (ticker biasa: AAPL) maupun IDX (pakai suffix .JK: BBCA.JK).
"""
from __future__ import annotations

import yfinance as yf


def fetch_prices(ticker: str, period: str = "6mo", interval: str = "1d") -> list[tuple]:
    """Ambil OHLCV. Return list of (date, open, high, low, close, volume)."""
    t = yf.Ticker(ticker)
    df = t.history(period=period, interval=interval, auto_adjust=False)

    rows: list[tuple] = []
    for idx, row in df.iterrows():
        rows.append((
            idx.date().isoformat(),
            _f(row.get("Open")),
            _f(row.get("High")),
            _f(row.get("Low")),
            _f(row.get("Close")),
            _i(row.get("Volume")),
        ))
    return rows


def fetch_prices_batch(tickers, period: str = "6mo", interval: str = "1d") -> dict[str, list[tuple]]:
    """Tarik banyak ticker sekaligus (batch download yfinance).

    Return dict {ticker: [(date, open, high, low, close, volume), ...]}.
    Ticker yang gagal/kosong -> list kosong (bukan error), biar backfill jalan terus.
    """
    tickers = list(tickers)
    if not tickers:
        return {}

    df = yf.download(tickers, period=period, interval=interval,
                     group_by="ticker", auto_adjust=False,
                     threads=True, progress=False)

    single = len(tickers) == 1
    result: dict[str, list[tuple]] = {}
    for tk in tickers:
        try:
            sub = df if single else df[tk]
        except (KeyError, TypeError):
            result[tk] = []
            continue

        rows: list[tuple] = []
        if sub is not None and not sub.empty:
            for idx, row in sub.iterrows():
                close = _f(row.get("Close"))
                if close is None:       # hari kosong / delisted -> skip
                    continue
                rows.append((
                    idx.date().isoformat(),
                    _f(row.get("Open")), _f(row.get("High")),
                    _f(row.get("Low")), close, _i(row.get("Volume")),
                ))
        result[tk] = rows
    return result


def _f(v):
    """Ke float, aman dari None/NaN."""
    try:
        if v is None:
            return None
        f = float(v)
        return None if f != f else round(f, 6)   # f != f -> NaN
    except (TypeError, ValueError):
        return None


def _i(v):
    """Ke int, aman dari None/NaN."""
    try:
        if v is None:
            return None
        f = float(v)
        return None if f != f else int(f)
    except (TypeError, ValueError):
        return None
