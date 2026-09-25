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


def allocate(capital: float, calls: list[dict], risk_pct: float = 0.02, max_pct: float = 0.25,
             max_pos: int = 6, min_pct: float = 0.05, fee: float = 0.0015, lot: int = LOT) -> dict:
    """SLICING MODAL: bagi modal ke saham BELI dari analisa. Murni hitungan (BUKAN LLM).

    Tiap saham: ukuran by risiko (entry->stop ≈ risk_pct modal; spekulatif setengahnya),
    maks max_pct modal per saham (berlaku juga buat 1 lot), porsi < min_pct dibuang (remah),
    total gak lebih dari modal (fee beli ikut dihitung). Sisa = kas.
    Urutan jatah: konviksi tinggi dulu -> non-spekulatif -> R:R terbesar. Modal kecil: kalau
    hitungan risiko 0 lot tapi 1 lot masih muat, tetap 1 lot (minimum IDX)."""
    rank = {"tinggi": 0, "sedang-tinggi": 0.5, "sedang": 1, "rendah": 2}
    cands = []
    for c in calls:
        act = c.get("action") or ""
        e, s, t = c.get("entry"), c.get("stop"), c.get("target")
        if not act.startswith("BELI") or not e or not s or not (e > s > 0):
            continue
        spek = "spekulatif" in act.lower()
        rr = (t - e) / (e - s) if t and t > e else 0.0
        cands.append((rank.get(str(c.get("conviction") or "").strip().lower(), 3), spek, -rr, c))
    cands.sort(key=lambda x: x[:3])

    cash, picks, skipped = float(capital), [], []
    for _, spek, neg_rr, c in cands:
        e, s = float(c["entry"]), float(c["stop"])
        per_lot = e * lot * (1 + fee)
        if len(picks) >= max_pos:
            skipped.append({"ticker": c["ticker"], "why": f"udah {max_pos} saham"})
            continue
        r = risk_pct / 2 if spek else risk_pct
        lots = min(int(capital * r // ((e - s) * lot)), int(capital * max_pct // per_lot))
        note = ""
        if per_lot > capital * max_pct:
            skipped.append({"ticker": c["ticker"], "why": f"1 lot > {max_pct:.0%} modal"})
            continue
        if lots == 0 and per_lot <= cash:
            lots, note = 1, "minimal 1 lot"
        lots = min(lots, int(cash // per_lot))
        if lots <= 0:
            skipped.append({"ticker": c["ticker"], "why": "modal sisa gak cukup"})
            continue
        if lots * per_lot < capital * min_pct:
            skipped.append({"ticker": c["ticker"], "why": f"porsi < {min_pct:.0%} modal"})
            continue
        cost = lots * per_lot
        cash -= cost
        picks.append({"ticker": c["ticker"], "action": c.get("action"), "conviction": c.get("conviction"),
                      "lot": lots, "entry": e, "stop": s, "target": c.get("target"),
                      "value": round(cost), "pct": cost / capital,
                      "risk_rp": round(lots * lot * (e - s)), "rr": round(-neg_rr, 2), "note": note})
    risk_total = sum(p["risk_rp"] for p in picks)
    return {"modal": capital, "used": round(capital - cash), "cash": round(cash),
            "risk_rp": risk_total, "risk_pct": risk_total / capital if capital else 0.0,
            "picks": picks, "skipped": skipped,
            "rules": {"risk_pct": risk_pct, "max_pct": max_pct, "max_pos": max_pos, "min_pct": min_pct}}


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
