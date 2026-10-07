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
from .ticks import round_tick

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


def is_risk_off(analysis: dict) -> bool:
    """Pasar lagi RISK-OFF menurut analisa (field regime; analisa lama belum punya -> tebak dari teks makro)."""
    regime = (analysis.get("regime") or "").upper()
    return regime == "RISK-OFF" or (not regime and "RISK-OFF" in (analysis.get("macro") or "").upper())


def allocate(capital: float, calls: list[dict], risk_pct: float = 0.02, max_pct: float = 0.25,
             min_pct: float = 0.05, fee: float = 0.0015, lot: int = LOT,
             cash: float | None = None, held: list[str] | tuple = (), lot1_risk: float = 0.02) -> dict:
    """SLICING MODAL: bagi uang ke saham BELI dari analisa. Murni hitungan (BUKAN LLM).

    capital = modal TOTAL (kas + nilai saham yang udah dipegang) -> dasar ukuran: rugi di Stop ≈ risk_pct
    modal (spekulatif setengahnya), maks max_pct modal per saham — kecuali 1 lot aja udah lewat max_pct:
    tetap boleh 1 lot asal rugi di Stop <= lot1_risk modal (modal kecil gak kehilangan saham bagus yang
    harganya tinggi). Porsi < min_pct dibuang (remah). cash = uang yang beneran bisa dibelanjain (default = capital); fee beli ikut dihitung.
    held = saham yang udah dipegang: dilewati. Jumlah saham gak dibatasi — yang membatasi cuma kas.
    Urutan jatah: konviksi tinggi dulu -> non-spekulatif -> R:R terbesar. Modal kecil: kalau hitungan
    risiko 0 lot tapi 1 lot masih muat, tetap 1 lot (minimum IDX)."""
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

    start = float(capital if cash is None else cash)
    left, picks, skipped = start, [], []
    for _, spek, _, c in cands:
        e, s = float(c["entry"]), float(c["stop"])
        per_lot = e * lot * (1 + fee)
        if c["ticker"] in held:
            skipped.append({"ticker": c["ticker"], "why": "udah dipegang"})
            continue
        r = risk_pct / 2 if spek else risk_pct
        lots = min(int(capital * r // ((e - s) * lot)), int(capital * max_pct // per_lot))
        if per_lot > capital * max_pct:
            if (e - s) * lot > capital * lot1_risk:
                skipped.append({"ticker": c["ticker"],
                                "why": f"1 lot kemahalan (kalau kena Stop rugi lebih dari {lot1_risk:.0%} modal)"})
                continue
            lots = 1                                     # 1 lot lewat max_pct, tapi ruginya di Stop masih kecil
        if lots == 0 and per_lot <= left:
            lots = 1                                     # modal kecil: minimal 1 lot
        lots = min(lots, int(left // per_lot))
        if lots <= 0:
            skipped.append({"ticker": c["ticker"], "why": "kas gak cukup"})
            continue
        if lots * per_lot < capital * min_pct:
            skipped.append({"ticker": c["ticker"], "why": f"porsinya kekecilan (kurang dari {min_pct:.0%} modal)"})
            continue
        cost = lots * per_lot
        left -= cost
        t = c.get("target")
        picks.append({"ticker": c["ticker"], "lot": lots, "entry": e, "stop": s, "target": t,
                      "value": round(cost), "pct": cost / capital,
                      "risk_rp": round(lots * lot * (e - s)),                            # rugi kalau kena stop
                      "reward_rp": round(lots * lot * (t - e)) if t and t > e else 0})   # untung kalau sampai target
    risk_total = sum(p["risk_rp"] for p in picks)
    reward_total = sum(p["reward_rp"] for p in picks)
    return {"modal": capital, "kas_awal": round(start), "used": round(start - left), "cash": round(left),
            "risk_rp": risk_total, "risk_pct": risk_total / capital if capital else 0.0,
            "reward_rp": reward_total, "reward_pct": reward_total / capital if capital else 0.0,
            "picks": picks, "skipped": skipped,
            "rules": {"risk_pct": risk_pct, "max_pct": max_pct, "min_pct": min_pct, "lot1_risk": lot1_risk}}


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
    trail = round_tick(max(base, hh - mult * a))   # harga sah di broker (fraksi BEI)
    return {"trail": trail, "atr": a, "hh": hh,
            "naik": trail > (init_stop or 0)}
