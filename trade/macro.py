"""Lapisan MAKRO — indikator pasar & global + REGIME IHSG (overlay market-timing).

Data via yfinance (indeks/kurs/komoditas/global) -> tabel `macro`. Regime IHSG
(^JKSE vs MA50/MA200) = risk-on / netral / risk-off: sinyal apakah lagi enak buat
long agresif atau mesti hati-hati. Buat sistem LONG-ONLY, ini penting — jangan
lawan arus pasar (gap #5: filter regime yang tadinya nggak ada).

`baik`: arah yang BAGUS buat saham IDX. +1 = naik itu bagus; -1 = naik itu jelek
(mis. USD/IDR naik = rupiah lemah = arus asing keluar = jelek).
"""
from __future__ import annotations

MACRO = {
    "^JKSE":    {"label": "IHSG",    "grup": "domestik",  "baik": +1},
    "IDR=X":    {"label": "USD/IDR", "grup": "domestik",  "baik": -1},  # naik = rupiah lemah
    "GC=F":     {"label": "Emas",    "grup": "komoditas", "baik": +1},  # tailwind ARCI/HRTA
    "CL=F":     {"label": "Minyak",  "grup": "komoditas", "baik": +1},  # proxy energi/komoditas
    "DX-Y.NYB": {"label": "DXY",     "grup": "global",    "baik": -1},  # dolar kuat = keluar EM
    "^TNX":     {"label": "US 10Y",  "grup": "global",    "baik": -1},  # yield naik = tekan EM
    "^VIX":     {"label": "VIX",     "grup": "global",    "baik": -1},  # takut = risk-off
}


def fetch_series(ticker: str, period: str = "2y") -> list[tuple]:
    """Ambil seri close harian 1 ticker makro. Return list (date_iso, close)."""
    import yfinance as yf
    h = yf.Ticker(ticker).history(period=period)
    out = []
    if "Close" not in h:
        return out
    for ts, c in h["Close"].items():
        c = float(c)
        if c == c:                       # buang NaN
            out.append((ts.date().isoformat(), c))
    return out


def _sma(vals, n):
    return sum(vals[-n:]) / n if len(vals) >= n else None


def ihsg_regime(closes: list) -> dict:
    """closes IHSG (urut lama->baru) -> {regime, note, level, ma50, ma200}."""
    if len(closes) < 50:
        return {"regime": "—", "note": "data IHSG kurang", "level": None,
                "ma50": None, "ma200": None}
    last, ma50, ma200 = closes[-1], _sma(closes, 50), _sma(closes, 200)
    if ma200 is None:                                    # < 200 bar: MA50 aja
        on = last > ma50
        return {"regime": "risk-on" if on else "risk-off", "level": last,
                "ma50": ma50, "ma200": None,
                "note": f"IHSG {'di atas' if on else 'di bawah'} MA50"}
    if last > ma200 and ma50 > ma200:
        regime, note = "risk-on", "IHSG di atas MA200 & MA50>MA200 (uptrend) — boleh long"
    elif last < ma200:
        regime, note = "risk-off", "IHSG di BAWAH MA200 (downtrend) — rem long baru"
    else:
        regime, note = "netral", "IHSG dekat MA200 — selektif, kurangi ukuran"
    return {"regime": regime, "note": note, "level": last, "ma50": ma50, "ma200": ma200}


def indicator(closes: list, baik: int = 1) -> dict:
    """1 indikator: level + %1bulan (~21 bar) + arah (bagus/jelek buat IDX)."""
    if not closes:
        return {"level": None, "chg1mo": None, "arah": None}
    last = closes[-1]
    chg = (last / closes[-22] - 1.0) if len(closes) >= 22 else None
    arah = None
    if chg is not None:
        good = (chg > 0) if baik > 0 else (chg < 0)
        arah = "bagus" if good else "jelek"
    return {"level": last, "chg1mo": chg, "arah": arah}


def load_series(conn, ticker: str) -> list:
    return [r[0] for r in conn.execute(
        "SELECT close FROM macro WHERE ticker=? ORDER BY date", (ticker,))]


def snapshot(conn) -> dict:
    """Gambaran makro lengkap buat dashboard/brief: regime IHSG + semua indikator."""
    out = {"regime": ihsg_regime(load_series(conn, "^JKSE")), "indikator": []}
    asof = conn.execute("SELECT MAX(date) FROM macro").fetchone()
    out["asof"] = asof[0] if asof else None
    for tk, meta in MACRO.items():
        s = load_series(conn, tk)
        out["indikator"].append({"ticker": tk, **meta, **indicator(s, meta["baik"])})
    return out
