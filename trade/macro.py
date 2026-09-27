"""Lapisan MAKRO — indikator pasar & global + REGIME IHSG (overlay market-timing).

Data via yfinance (indeks/kurs/komoditas/global) -> tabel `macro`. Regime IHSG
(^JKSE vs MA50/MA200) = risk-on / netral / risk-off: sinyal apakah lagi enak buat
long agresif atau mesti hati-hati. Buat sistem LONG-ONLY, ini penting — jangan
lawan arus pasar (gap #5: filter regime yang tadinya nggak ada).

CATATAN BACKTEST (5thn, regime saat entry): dipakai sbg OVERLAY / dial UKURAN,
BUKAN gate keras. Entry pas risk-off masih rata2 +2,86% (vs +3,56% risk-on) —
skip total malah MOTONG profit (total ret 14.293% -> 10.232%). Jadi risk-off =
selektif + ukuran kecil, bukan stop.

Kolom tiap indikator di MACRO (urutan = urutan tampil di app):
  baik  : arah yang BAGUS buat saham IDX. +1 = naik itu bagus; -1 = naik itu jelek
          (mis. USD/IDR naik = rupiah lemah = arus asing keluar = jelek).
  unit  : tampilan di app — "Rp" (depan), "%" (belakang), "" (indeks).
  per   : satuan komoditas; to_rp = faktor harga dolar -> Rupiah (dikali kurs USD/IDR hari itu).
"""
from __future__ import annotations

TROY_OZ_GR = 31.1035   # 1 troy ounce = 31,1035 gram

MACRO = {
    "GC=F":     {"label": "Emas",    "baik": +1, "unit": "Rp", "per": "gr", "to_rp": 1 / TROY_OZ_GR},
    "IDR=X":    {"label": "USD/IDR", "baik": -1, "unit": "Rp"},   # naik = rupiah lemah
    "^JKSE":    {"label": "IHSG",    "baik": +1, "unit": ""},
    "CL=F":     {"label": "Minyak",  "baik": +1, "unit": "Rp", "per": "barel", "to_rp": 1.0},
    "DX-Y.NYB": {"label": "DXY",     "baik": -1, "unit": ""},     # dolar kuat = dana keluar EM
    "^TNX":     {"label": "US 10Y",  "baik": -1, "unit": "%"},    # yield naik = tekan EM
    "^VIX":     {"label": "VIX",     "baik": -1, "unit": ""},     # takut = risk-off
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
    """Gambaran makro buat brief: regime IHSG + tren sebulan tiap indikator."""
    out = {"regime": ihsg_regime(load_series(conn, "^JKSE")), "indikator": []}
    asof = conn.execute("SELECT MAX(date) FROM macro").fetchone()
    out["asof"] = asof[0] if asof else None
    for tk, meta in MACRO.items():
        s = load_series(conn, tk)
        out["indikator"].append({"ticker": tk, "label": meta["label"], **indicator(s, meta["baik"])})
    return out


def latest(conn) -> list[dict]:
    """Angka terakhir tiap indikator + % perubahan harian (strip Makro di app).
    Emas & minyak dalam RUPIAH pakai kurs hari itu, jadi perubahannya ikut gerak kurs juga."""
    last2 = {tk: conn.execute("SELECT date, close FROM macro WHERE ticker=? ORDER BY date DESC LIMIT 2",
                              (tk,)).fetchall() for tk in MACRO}
    fx = last2["IDR=X"]
    fx_last = fx[0]["close"] if fx else None
    fx_prev = fx[1]["close"] if len(fx) > 1 else fx_last
    out = []
    for tk, m in MACRO.items():
        rows = last2[tk]
        if not rows:
            continue
        last = rows[0]["close"]
        prev = rows[1]["close"] if len(rows) > 1 else last
        if "to_rp" in m:
            if not fx_last:
                continue
            last, prev = last * fx_last * m["to_rp"], prev * (fx_prev or fx_last) * m["to_rp"]
        chg = round((last / prev - 1) * 100, 2) if prev else 0.0
        out.append({"ticker": tk, "label": m["label"], "unit": m["unit"], "per": m.get("per"),
                    "last": last, "chg": chg, "date": rows[0]["date"]})
    return out
