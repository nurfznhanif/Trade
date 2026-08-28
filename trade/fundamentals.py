"""Fundamental perusahaan (rasio kunci via yfinance) + penilaian 'sehat/rapuh'.

Dipakai sebagai PAGAR (trash filter) buat swing: buang saham yang jelas-jelas
bahaya (rugi / ekuitas rapuh / utang ekstrem), BUKAN screen value ketat —
biar pemenang momentum yang kebetulan mahal (PER tinggi) gak ikut kebuang.

Catatan jujur: ini rasio SEKARANG (yfinance gak kasih arsip point-in-time),
jadi filter ini dipakai buat sinyal LIVE, bukan di-backtest.
"""
from __future__ import annotations

import yfinance as yf

_FIELDS = {
    "per": "trailingPE", "pbv": "priceToBook", "roe": "returnOnEquity",
    "der": "debtToEquity", "div_yield": "dividendYield",
    "margin": "profitMargins", "market_cap": "marketCap",
}


def fetch_fundamentals(ticker: str) -> dict:
    """Ambil rasio fundamental satu saham. Field yang kosong -> None."""
    info = yf.Ticker(ticker).info
    out = {"ticker": ticker}
    for key, field in _FIELDS.items():
        v = info.get(field)
        out[key] = float(v) if isinstance(v, (int, float)) else None
    return out


def red_flags(f: dict) -> list[str]:
    """Bendera merah fundamental. List kosong = aman/sehat."""
    flags = []
    margin, roe, der, pbv = f.get("margin"), f.get("roe"), f.get("der"), f.get("pbv")

    if margin is not None and margin < 0:
        flags.append("rugi (margin negatif)")
    elif roe is not None and roe < -0.05:
        flags.append("ROE negatif")

    if der is not None and der > 300:                 # >300% ekuitas = utang ekstrem
        flags.append(f"utang ekstrem (DER {der:.0f})")

    if pbv is not None and (pbv < 0 or pbv > 100):    # negatif/aneh = ekuitas rapuh
        flags.append("PBV aneh (ekuitas rapuh?)")

    return flags


def is_healthy(f: dict) -> bool:
    return not red_flags(f)
