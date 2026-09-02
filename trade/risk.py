"""Manajemen RISIKO — sizing (berapa lot) + trailing stop (di mana keluar).

Dua hal ini paling nentuin cuan jangka panjang, tapi paling sering kelupaan
(orang sibuk di entry). Melengkapi metode: entry (~20%) + RISK & EXIT (~80%).

SIZING (risk-based): risiko tetap % modal per trade. lot ditentuin dari jarak
entry->stop, bukan nebak. Kalah = rugi ~sama & terkontrol; menang = ikut ukuran.

EXIT (trailing): backtest -> trailing JAUH > fixed target (avg winner 20% vs 14%,
max 425% vs 189%). Target = checkpoint pertama, TAPI biarin lari: geser stop naik
= max(stop_awal, high_tertinggi_sejak_entry - mult*ATR). Motong di target = buang edge.
"""
from __future__ import annotations

from .indicators import atr as _atr

LOT = 100          # 1 lot IDX = 100 lembar
TRAIL_MULT = 3.0   # trailing = high tertinggi - 3*ATR (samain sama backtest)


def position_size(capital: float, entry: float, stop: float,
                  risk_pct: float = 0.01, lot: int = LOT) -> dict:
    """Ukuran posisi biar risiko (entry->stop) ≈ risk_pct * modal.
    Buat modal KECIL: kalau hitungan risiko = 0 lot TAPI 1 lot masih kebeli, kasih 1 lot
    (risiko dikit di atas target — itu minimum, nggak bisa beli separo lot).
    Return {lot, shares, modal, risk_rp, risk_pct_real, note}."""
    if not (entry and stop and entry > stop > 0):
        return {"lot": 0, "shares": 0, "modal": 0.0, "risk_rp": 0.0,
                "risk_pct_real": 0.0, "note": "stop harus di bawah entry (>0)"}
    per_share = entry - stop
    afford = int(capital // (entry * lot))                   # max lot yang kebeli modal
    lots = int((capital * risk_pct) / (per_share * lot))     # ideal by risiko
    note = ""
    if lots == 0 and afford >= 1:
        lots, note = 1, "1 lot = risiko sedikit di ATAS target (modal kecil, ini minimum)"
    lots = min(lots, afford)                                  # jangan lebih dari modal
    if lots == 0:
        note = "modal kurang buat 1 lot (kemahalan)"
    shares = lots * lot
    return {"lot": lots, "shares": shares, "modal": shares * entry,
            "risk_rp": shares * per_share,
            "risk_pct_real": (shares * per_share / capital) if capital else 0.0,
            "note": note}


def trailing_stop_level(conn, ticker: str, entry_date: str, init_stop,
                        mult: float = TRAIL_MULT, atr_n: int = 14) -> dict:
    """Stop TRAILING sekarang buat posisi terbuka:
    max(stop_awal, high_tertinggi_sejak_entry - mult*ATR).
    Return {trail, atr, hh, naik(bool)}; fallback ke init_stop kalau data kurang."""
    rows = conn.execute(
        "SELECT date, high, low, close FROM prices WHERE ticker=? ORDER BY date",
        (ticker,)).fetchall()
    if len(rows) < atr_n + 2:
        return {"trail": init_stop, "atr": None, "hh": None, "naik": False}
    highs = [r[1] for r in rows]
    lows = [r[2] for r in rows]
    closes = [r[3] for r in rows]
    a = _atr(highs, lows, closes, atr_n)
    hh = max((r[1] for r in rows if r[0][:10] >= entry_date[:10] and r[1] is not None),
             default=None)
    if a is None or hh is None:
        return {"trail": init_stop, "atr": a, "hh": hh, "naik": False}
    base = init_stop if init_stop else 0.0
    trail = max(base, hh - mult * a)
    return {"trail": round(trail, 2), "atr": a, "hh": hh,
            "naik": trail > (init_stop or 0)}
