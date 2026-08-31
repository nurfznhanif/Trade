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


# yfinance sering ngasih rasio NGACO buat saham IDX (PBV 686.000, PER 159.000, DER 9.400).
# Rentang "wajar" ini buat nyaring data sampah biar pagar fundamental nggak salah blok
# saham bagus (dulu 46/197 saham keblok gara-gara PBV ngaco).
_SANE = {
    "pbv":    (-20.0, 60.0),      # PBV wajar; di luar ini = data ngaco -> None
    "per":    (-1000.0, 1000.0),  # PER wajar; 159.000 = ngaco
    "der":    (0.0, 1500.0),      # debtToEquity (%); >1500 = ngaco
    "roe":    (-10.0, 10.0),      # ROE fraksi
    "margin": (-10.0, 10.0),      # margin fraksi
}


def _plausible(v, lo: float, hi: float):
    """Balikin v (float) kalau di rentang wajar, else None (buang data ngaco)."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if lo <= v <= hi else None


def sanitize(f: dict) -> dict:
    """Bersihin rasio yfinance yang ngaco -> None, + normalisasi satuan div_yield.

    yfinance ngasih dividendYield dalam PERSEN (mis. 3.33 = 3,33%), padahal roe/margin
    diperlakukan sebagai FRAKSI. Di sini div_yield dibagi 100 biar konsisten (0.0333)
    dan tampil bener (dikali 100 lagi) di dashboard/brief. Terima nilai MENTAH dari DB.
    """
    g = dict(f)
    for k, (lo, hi) in _SANE.items():
        if k in g:
            g[k] = _plausible(g.get(k), lo, hi)
    try:
        dy = float(f.get("div_yield"))
        g["div_yield"] = dy / 100.0 if dy > 1.0 else dy      # persen -> fraksi
    except (TypeError, ValueError):
        g["div_yield"] = None
    return g


def red_flags(f: dict) -> list[str]:
    """Bendera merah fundamental (list kosong = sehat). Pakai nilai yang sudah disanitize
    biar data ngaco yfinance nggak bikin salah blok saham bagus."""
    f = sanitize(f)
    flags = []
    margin, roe, der, pbv = f.get("margin"), f.get("roe"), f.get("der"), f.get("pbv")

    if margin is not None and margin < 0:
        flags.append("rugi (margin negatif)")
    elif roe is not None and roe < -0.05:
        flags.append("ROE negatif")

    if der is not None and der > 300:                 # >300% (3x) ekuitas = utang ekstrem
        flags.append(f"utang ekstrem (DER {der:.0f})")

    if pbv is not None and pbv < 0:                   # ekuitas NEGATIF = beneran rapuh
        flags.append("ekuitas negatif (PBV<0)")

    return flags


def is_healthy(f: dict) -> bool:
    return not red_flags(f)
