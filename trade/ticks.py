"""Fraksi harga BEI: harga saham cuma boleh kelipatan tertentu, tergantung level harganya.
Broker (Stockbit dll) nolak order di harga yang bukan kelipatan — mis. Stop 2.991 buat saham Rp2.000-an
(kelipatannya Rp10). Level dari LLM (Entry/Target/Stop) dibulatkan ke harga sah terdekat.
"""
from __future__ import annotations

# (harga mulai, kelipatan) — aturan fraksi harga BEI. Batas-batasnya sendiri (200/500/2.000/5.000) juga
# kelipatan fraksi di atasnya, jadi pembulatan yang nyebrang batas tetap jatuh di harga sah.
_TICKS = [(5000, 25), (2000, 10), (500, 5), (200, 2), (0, 1)]


def tick_size(price: float) -> int:
    return next(t for floor, t in _TICKS if price >= floor)


def round_tick(price: float) -> int:
    """Bulatkan ke harga sah terdekat: 2.991 -> 2.990, 3.707 -> 3.710, 5.612 -> 5.600, 998 -> 1.000."""
    t = tick_size(price)
    return int(round(price / t) * t)


def round_levels(analysis: dict) -> dict:
    """Entry/Target/Stop tiap saran dibulatkan ke fraksi sah (ngubah dict-nya langsung, aman diulang)."""
    for c in analysis.get("calls", []):
        for k in ("entry", "target", "stop"):
            v = c.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
                c[k] = round_tick(v)
    return analysis
